"""SQLite давхарга.

Дараагийн түвшинд PostgreSQL руу шилжихэд хялбар байхаар бүх SQL-г энэ модуль болон
`repo.py` дотор төвлөрүүлсэн. Аппликейшний код шууд sqlite3-той харьцахгүй.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
import random

from .config import DB_PATH, THUMB_DIR, ROLE_ADMIN, ROLE_VIEWER, SECTION_BONUS, SECTION_OTHER

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'viewer',
    position    TEXT,                      -- албан тушаал (Microsoft contacts-аас sync)
    branch      TEXT,                      -- салбарын нэр
    department  TEXT,
    phone       TEXT,
    avatar_hue  INTEGER NOT NULL DEFAULT 200,
    source      TEXT NOT NULL DEFAULT 'mock',   -- mock | microsoft
    created_at  TEXT NOT NULL,
    last_login  TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    code        TEXT,
    line        TEXT,                      -- бүтээгдэхүүний чиглэл / бүлэг
    color       TEXT NOT NULL DEFAULT '#00e0a4',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    team_name   TEXT,
    link        TEXT NOT NULL,             -- Teams channel холбоос (гараар оруулна)
    webhook_url TEXT,                      -- сонголт: Incoming webhook
    members     INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    description  TEXT,
    section      TEXT NOT NULL DEFAULT 'other',   -- bonus | other
    kind         TEXT NOT NULL DEFAULT 'video',   -- video | image | poster | pdf
    product_id   INTEGER REFERENCES products(id) ON DELETE SET NULL,
    file_name    TEXT,
    file_path    TEXT,
    mime         TEXT,
    size_bytes   INTEGER NOT NULL DEFAULT 0,
    thumb_path   TEXT,
    duration_sec INTEGER NOT NULL DEFAULT 0,
    publish_date TEXT,
    status       TEXT NOT NULL DEFAULT 'draft',   -- draft | published
    created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_tags (
    content_id INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (content_id, tag)
);

CREATE TABLE IF NOT EXISTS distributions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id   INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    channel_id   INTEGER NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'sent',    -- sent | scheduled | failed
    message      TEXT,
    scheduled_at TEXT,
    sent_at      TEXT,
    created_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS views (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id   INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id   INTEGER REFERENCES channels(id) ON DELETE SET NULL,
    watched_sec  INTEGER NOT NULL DEFAULT 0,
    completed    INTEGER NOT NULL DEFAULT 0,
    device       TEXT,
    viewed_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body       TEXT NOT NULL,
    rating     INTEGER,
    created_at TEXT NOT NULL
);

-- Ажилтны лавлах: админаас Excel-ээр оруулсан @monos.mn хаягуудын жагсаалт.
-- Нэвтрэхийг зөвшөөрөх шалгуур бөгөөд профайлын мэдээллийн эх сурвалж.
-- `users`-аас тусдаа: дахин импорт хийхэд хэрэглэгчийн эрх, үзэлтийн түүх хөндөгдөхгүй.
CREATE TABLE IF NOT EXISTS directory (
    email       TEXT PRIMARY KEY,
    last_name   TEXT,                      -- овог
    first_name  TEXT,                      -- нэр
    position    TEXT,                      -- албан тушаал
    branch      TEXT,                      -- салбар
    department  TEXT,
    phone       TEXT,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_directory_branch ON directory(branch);
CREATE INDEX IF NOT EXISTS idx_views_content ON views(content_id);
CREATE INDEX IF NOT EXISTS idx_views_user ON views(user_id);
CREATE INDEX IF NOT EXISTS idx_views_date ON views(viewed_at);
CREATE INDEX IF NOT EXISTS idx_contents_section ON contents(section);
CREATE INDEX IF NOT EXISTS idx_dist_content ON distributions(content_id);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql: str, params=()) -> list[sqlite3.Row]:
    with db() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params=()):
    with db() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql: str, params=()) -> int:
    with db() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


MIGRATIONS = {
    # distributions — Teams-руу бодитоор илгээх үр дүнг хадгалах талбарууд
    "distributions": [
        ("error", "TEXT"),              # амжилтгүй болсон шалтгаан
        ("attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("last_try_at", "TEXT"),
    ],
}


def migrate() -> list[str]:
    """Байгаа DB дээр дутуу баганыг нэмнэ (давтан ажиллуулахад аюулгүй)."""
    applied = []
    with db() as conn:
        for table, columns in MIGRATIONS.items():
            have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for name, ddl in columns:
                if name not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                    applied.append(f"{table}.{name}")
    return applied


def init_db(seed: bool = True) -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
    migrate()
    if seed and not query_one("SELECT 1 FROM users LIMIT 1"):
        seed_demo_data()


# --------------------------------------------------------------------------
# Demo өгөгдөл — dashboard-г хоосон биш, бодит харагдацтай эхлүүлэхэд
# --------------------------------------------------------------------------

POSTER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <radialGradient id="r" cx="0.8" cy="0.15" r="0.9">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="800" height="450" fill="url(#g)"/>
  <rect width="800" height="450" fill="url(#r)"/>
  <circle cx="672" cy="366" r="150" fill="#ffffff" opacity="0.07"/>
  <circle cx="112" cy="70" r="96" fill="#ffffff" opacity="0.06"/>
  <text x="48" y="212" font-family="Segoe UI, Helvetica, Arial" font-size="52"
        font-weight="700" fill="#ffffff">{line1}</text>
  <text x="48" y="272" font-family="Segoe UI, Helvetica, Arial" font-size="30"
        fill="#ffffff" opacity="0.82">{line2}</text>
  <text x="48" y="404" font-family="Segoe UI, Helvetica, Arial" font-size="21"
        fill="#ffffff" opacity="0.6" letter-spacing="3">MP TEAM · MONOS</text>
</svg>
"""


def _make_poster(slug: str, line1: str, line2: str, c1: str, c2: str) -> str:
    """Demo контентын cover зургийг SVG-ээр үүсгэж storage дотор хадгална."""
    path = THUMB_DIR / f"{slug}.svg"
    safe = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    path.write_text(
        POSTER_SVG.format(line1=safe(line1[:22]), line2=safe(line2[:34]), c1=c1, c2=c2),
        encoding="utf-8",
    )
    return f"thumbs/{slug}.svg"


DEMO_PRODUCTS = [
    ("Ампилин", "AMP", "Антибиотик", "#00e0a4"),
    ("Гепаклин", "GEP", "Элэг", "#38bdf8"),
    ("Иммунофорт", "IMF", "Дархлаа", "#a855f7"),
    ("Кальци-Д3", "CAD", "Витамин", "#f97316"),
    ("Ринофлю", "RNF", "Ханиад", "#ec4899"),
    ("Гастропро", "GSP", "Ходоод", "#22d3ee"),
    ("Кардиолайф", "KRL", "Зүрх судас", "#ef4444"),
    ("Витамин С-1000", "VC1", "Витамин", "#facc15"),
]

DEMO_CHANNELS = [
    ("Эмийн сан — Улаанбаатар", "Monos Pharmacy", "https://teams.microsoft.com/l/channel/19%3ademo-ub/UB", 420),
    ("Эмийн сан — Орон нутаг", "Monos Pharmacy", "https://teams.microsoft.com/l/channel/19%3ademo-oro/Oron", 310),
    ("Эмийн мэргэжилтэн", "Monos Medical", "https://teams.microsoft.com/l/channel/19%3ademo-med/Med", 180),
    ("Маркетинг зарлал", "Monos HQ", "https://teams.microsoft.com/l/channel/19%3ademo-mkt/Marketing", 95),
]

DEMO_USERS = [
    ("bolormaa.b@monos.mn", "Б. Болормаа", "Жор баригч", "Сансар салбар"),
    ("tuvshin.d@monos.mn", "Д. Түвшин", "Эмийн мэргэжилтэн", "Төв салбар"),
    ("enkhjin.g@monos.mn", "Г. Энхжин", "Жор баригч", "Зайсан салбар"),
    ("munkh.o@monos.mn", "О. Мөнх", "Салбарын менежер", "Дархан салбар"),
    ("saruul.t@monos.mn", "Т. Саруул", "Жор баригч", "Эрдэнэт салбар"),
    ("nomin.e@monos.mn", "Э. Номин", "Эмийн мэргэжилтэн", "Хан-Уул салбар"),
    ("ganzul.b@monos.mn", "Б. Ганзул", "Жор баригч", "Баянзүрх салбар"),
    ("delgermaa.s@monos.mn", "С. Дэлгэрмаа", "Жор баригч", "Сүхбаатар салбар"),
    ("erdene.j@monos.mn", "Ж. Эрдэнэ", "Эмийн мэргэжилтэн", "Налайх салбар"),
    ("oyunaa.p@monos.mn", "П. Оюунаа", "Жор баригч", "Чингэлтэй салбар"),
    ("battur.n@monos.mn", "Н. Баттөр", "Салбарын менежер", "Дорнод салбар"),
    ("altantsetseg.m@monos.mn", "М. Алтанцэцэг", "Жор баригч", "Хөвсгөл салбар"),
]

DEMO_CONTENTS = [
    # (title, section, kind, product_index, description)
    ("Ампилин — бонус урамшууллын нөхцөл", SECTION_BONUS, "video", 0,
     "2026 оны 3-р сарын бонус нөхцөл, борлуулалтын зорилт болон урамшууллын тооцооны жишээ."),
    ("Иммунофорт — жор баригчийн бонус хөтөлбөр", SECTION_BONUS, "video", 2,
     "Дархлаа дэмжих бүтээгдэхүүний улирлын идэвхжүүлэлт, шатлалт урамшуулал."),
    ("Кальци-Д3 бонус постер", SECTION_BONUS, "poster", 3,
     "Салбарт байршуулах A3 постер. Бонус оноо, хугацааг тодотгосон."),
    ("Ринофлю — намрын кампанит ажил", SECTION_BONUS, "video", 4,
     "Ханиад томуугийн улирлын идэвхтэй бүтээгдэхүүний бонус нөхцөл."),
    ("Витамин С-1000 бонус зар", SECTION_BONUS, "image", 7,
     "Teams-д тараах зориулалттай квадрат баннер."),
    ("Гепаклин — үйлчлэлийн механизм", SECTION_OTHER, "video", 1,
     "Элэг хамгаалах бүтээгдэхүүний найрлага, үйлчлэл, заалт, харшлын мэдээлэл."),
    ("Гастропро — зөвлөх борлуулалтын скрипт", SECTION_OTHER, "video", 5,
     "Жор баригчийн харилцан ярианы загвар, түгээмэл эсэргүүцэлтэй ажиллах."),
    ("Кардиолайф — эмнэлзүйн судалгааны хураангуй", SECTION_OTHER, "video", 6,
     "Олон улсын судалгааны үр дүн, харьцуулсан үзүүлэлт."),
    ("Ампилин — тун хэрэглээний зөвлөмж", SECTION_OTHER, "image", 0,
     "Насны ангилал тус бүрийн тун, хэрэглэх заавар."),
    ("Шинэ бүтээгдэхүүний танилцуулга — 2026 Q1", SECTION_OTHER, "video", None,
     "Улирлын шинэ бүтээгдэхүүнүүдийн нэгдсэн танилцуулга."),
    ("Эмийн сангийн үйлчилгээний стандарт", SECTION_OTHER, "poster", None,
     "Үйлчлүүлэгчтэй харилцах 7 алхам."),
    ("Витамин С-1000 — хадгалалт, хугацаа", SECTION_OTHER, "image", 7,
     "Агуулах болон лангууны хадгалалтын шаардлага."),
]

DEMO_COMMENTS = [
    "Маш ойлгомжтой тайлбарлалаа, баярлалаа!",
    "Бонусын тооцооны хэсгийг дахин жишээтэй тайлбарлаж өгөх үү?",
    "Салбартаа хамт олондоо үзүүллээ. Хэрэгтэй мэдээлэл байна.",
    "Постерыг хэвлэх хэмжээтэй файлаар авах боломжтой юу?",
    "Үйлчлүүлэгчид тайлбарлахад амар боллоо.",
    "Видео сайхан бэлтгэгдсэн байна, дуу чимээ бага зэрэг сул байна.",
    "Заалт, эсрэг заалтын хэсэг тодорхой байлаа.",
    "Дараагийн удаа асуулт хариултын хэсэг нэмээрэй.",
]


def seed_demo_data() -> None:
    ts = now()
    with db() as conn:
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users(email,name,role,position,branch,department,avatar_hue,source,created_at,last_login)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("admin@monos.mn", "Маркетингийн менежер", ROLE_ADMIN, "Marketing Manager",
             "Төв оффис", "Marketing", 160, "mock", ts, ts),
        )
        admin_id = cur.lastrowid

        user_ids = []
        for i, (email, name, position, branch) in enumerate(DEMO_USERS):
            cur.execute(
                "INSERT INTO users(email,name,role,position,branch,department,avatar_hue,source,created_at,last_login)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (email, name, ROLE_VIEWER, position, branch, "Retail",
                 (i * 37) % 360, "microsoft", ts, ts),
            )
            user_ids.append(cur.lastrowid)

        product_ids = []
        for name, code, line, color in DEMO_PRODUCTS:
            cur.execute(
                "INSERT INTO products(name,code,line,color,created_at) VALUES(?,?,?,?,?)",
                (name, code, line, color, ts),
            )
            product_ids.append(cur.lastrowid)

        channel_ids = []
        for name, team, link, members in DEMO_CHANNELS:
            cur.execute(
                "INSERT INTO channels(name,team_name,link,members,is_active,created_at) VALUES(?,?,?,?,1,?)",
                (name, team, link, members, ts),
            )
            channel_ids.append(cur.lastrowid)

        rng = random.Random(20260902)
        content_ids = []
        for idx, (title, section, kind, p_idx, desc) in enumerate(DEMO_CONTENTS):
            product_id = product_ids[p_idx] if p_idx is not None else None
            color = DEMO_PRODUCTS[p_idx][3] if p_idx is not None else "#7c5cff"
            thumb = _make_poster(
                f"demo-{idx + 1}",
                DEMO_PRODUCTS[p_idx][0] if p_idx is not None else "MP team",
                title,
                color,
                "#141a3a" if section == SECTION_OTHER else "#2a0f4a",
            )
            created = (datetime.now() - timedelta(days=rng.randint(2, 55))).replace(microsecond=0)
            cur.execute(
                "INSERT INTO contents(title,description,section,kind,product_id,file_name,file_path,mime,"
                "size_bytes,thumb_path,duration_sec,publish_date,status,created_by,created_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (title, desc, section, kind, product_id, None, None,
                 "video/mp4" if kind == "video" else "image/svg+xml",
                 rng.randint(2_000_000, 90_000_000), thumb,
                 rng.randint(90, 420) if kind == "video" else 0,
                 created.date().isoformat(), "published", admin_id,
                 created.isoformat(sep=" ")),
            )
            cid = cur.lastrowid
            content_ids.append((cid, created))
            for ch in rng.sample(channel_ids, rng.randint(1, 3)):
                sent = created + timedelta(hours=rng.randint(1, 20))
                cur.execute(
                    "INSERT INTO distributions(content_id,channel_id,status,message,sent_at,created_by,created_at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (cid, ch, "sent", "Шинэ контент нэмэгдлээ.", sent.isoformat(sep=" "),
                     admin_id, sent.isoformat(sep=" ")),
                )

        # Үзэлтүүд — сүүлийн 8 долоо хоногт тархсан
        for cid, created in content_ids:
            days_live = max((datetime.now() - created).days, 1)
            for uid in rng.sample(user_ids, rng.randint(4, len(user_ids))):
                for _ in range(rng.randint(1, 4)):
                    seen = created + timedelta(
                        days=rng.randint(0, days_live),
                        hours=rng.randint(8, 21),
                        minutes=rng.randint(0, 59),
                    )
                    if seen > datetime.now():
                        seen = datetime.now() - timedelta(hours=rng.randint(1, 40))
                    cur.execute(
                        "INSERT INTO views(content_id,user_id,channel_id,watched_sec,completed,device,viewed_at)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (cid, uid, rng.choice(channel_ids), rng.randint(20, 380),
                         1 if rng.random() > 0.4 else 0,
                         rng.choice(["Teams mobile", "Teams desktop", "Browser"]),
                         seen.replace(microsecond=0).isoformat(sep=" ")),
                    )
            for uid in rng.sample(user_ids, rng.randint(0, 4)):
                c_at = created + timedelta(days=rng.randint(0, days_live))
                cur.execute(
                    "INSERT INTO comments(content_id,user_id,body,rating,created_at) VALUES(?,?,?,?,?)",
                    (cid, uid, rng.choice(DEMO_COMMENTS), rng.randint(3, 5),
                     min(c_at, datetime.now()).replace(microsecond=0).isoformat(sep=" ")),
                )
