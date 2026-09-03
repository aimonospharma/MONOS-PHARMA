"""Өгөгдөл унших/бичих функцууд. Route-ууд зөвхөн энэ давхаргаар дамжина."""
from datetime import datetime, timedelta

from .database import db, query, query_one, execute, now
from .config import ROLE_ADMIN, ROLE_VIEWER

CONTENT_SELECT = """
SELECT c.*, p.name AS product_name, p.color AS product_color, p.code AS product_code,
       u.name AS author_name,
       (SELECT COUNT(*) FROM views v WHERE v.content_id = c.id) AS views_total,
       (SELECT COUNT(DISTINCT v.user_id) FROM views v WHERE v.content_id = c.id) AS viewers_unique,
       (SELECT COUNT(*) FROM comments cm WHERE cm.content_id = c.id) AS comments_total,
       (SELECT COUNT(*) FROM distributions d WHERE d.content_id = c.id AND d.status='sent') AS sent_count,
       (SELECT COUNT(*) FROM distributions d WHERE d.content_id = c.id AND d.status='scheduled') AS scheduled_count
FROM contents c
LEFT JOIN products p ON p.id = c.product_id
LEFT JOIN users u ON u.id = c.created_by
"""


# ----------------------------- Users ------------------------------------
def get_user(user_id: int):
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def get_user_by_email(email: str):
    return query_one("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),))


def list_users():
    return query(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM views v WHERE v.user_id = u.id) AS views_total,
                  (SELECT COUNT(*) FROM comments c WHERE c.user_id = u.id) AS comments_total,
                  (SELECT MAX(v.viewed_at) FROM views v WHERE v.user_id = u.id) AS last_view
           FROM users u ORDER BY views_total DESC, u.name"""
    )


def create_user(email: str, name: str, role: str = ROLE_VIEWER, position: str = None,
                branch: str = None, department: str = None, source: str = "mock"):
    hue = abs(hash(email.lower())) % 360
    uid = execute(
        "INSERT INTO users(email,name,role,position,branch,department,avatar_hue,source,created_at,last_login)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (email.strip(), name.strip(), role, position, branch, department, hue, source, now(), now()),
    )
    return get_user(uid)


def touch_login(user_id: int):
    execute("UPDATE users SET last_login = ? WHERE id = ?", (now(), user_id))


def update_user_role(user_id: int, role: str):
    execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def sync_from_microsoft(user_id: int, position: str | None, branch: str | None,
                        department: str | None, phone: str | None, name: str | None):
    """Graph-аас ирсэн утгуудаар профайлыг шинэчилнэ.

    Microsoft талд хоосон байгаа талбарыг дарж бичихгүй (COALESCE) — тэнд
    бөглөөгүй байхад аппад гараар оруулсан мэдээллийг устгах ёсгүй.
    """
    execute(
        """UPDATE users
              SET position   = COALESCE(?, position),
                  branch     = COALESCE(?, branch),
                  department = COALESCE(?, department),
                  phone      = COALESCE(?, phone),
                  name       = COALESCE(?, name),
                  source     = 'microsoft'
            WHERE id = ?""",
        (position, branch, department, phone, name, user_id),
    )


def update_profile(user_id: int, position: str, branch: str, department: str, phone: str):
    execute(
        "UPDATE users SET position=?, branch=?, department=?, phone=? WHERE id=?",
        (position, branch, department, phone, user_id),
    )


# ----------------------------- Products ---------------------------------
PALETTE = ["#00e0a4", "#38bdf8", "#a855f7", "#f97316", "#ec4899",
           "#22d3ee", "#ef4444", "#facc15", "#84cc16", "#7c5cff"]


def list_products():
    return query(
        """SELECT p.*, (SELECT COUNT(*) FROM contents c WHERE c.product_id = p.id) AS content_count,
                  (SELECT COUNT(*) FROM views v JOIN contents c ON c.id = v.content_id
                    WHERE c.product_id = p.id) AS views_total
           FROM products p ORDER BY p.name"""
    )


def add_product(name: str, code: str = None, line: str = None) -> int | None:
    name = (name or "").strip()
    if not name:
        return None
    existing = query_one("SELECT id FROM products WHERE name = ? COLLATE NOCASE", (name,))
    if existing:
        return None
    color = PALETTE[abs(hash(name.lower())) % len(PALETTE)]
    return execute(
        "INSERT INTO products(name,code,line,color,created_at) VALUES(?,?,?,?,?)",
        (name, (code or "").strip() or None, (line or "").strip() or None, color, now()),
    )


def get_product(pid: int):
    return query_one("SELECT * FROM products WHERE id = ?", (pid,))


def update_product(pid: int, name: str, code: str = None, line: str = None,
                   color: str = None) -> bool:
    """Бүтээгдэхүүний мэдээлэл засах. Нэр давхардвал False буцаана."""
    name = (name or "").strip()
    if not name:
        return False
    clash = query_one(
        "SELECT id FROM products WHERE name = ? COLLATE NOCASE AND id <> ?", (name, pid)
    )
    if clash:
        return False
    current = get_product(pid)
    if not current:
        return False
    execute(
        "UPDATE products SET name = ?, code = ?, line = ?, color = ? WHERE id = ?",
        (name, (code or "").strip() or None, (line or "").strip() or None,
         (color or "").strip() or current["color"], pid),
    )
    return True


def delete_product(pid: int):
    execute("DELETE FROM products WHERE id = ?", (pid,))


# ----------------------------- Channels ---------------------------------
def list_channels(active_only: bool = False):
    sql = """SELECT ch.*,
                 (SELECT COUNT(*) FROM distributions d WHERE d.channel_id = ch.id AND d.status='sent') AS sent_count,
                 (SELECT COUNT(*) FROM views v WHERE v.channel_id = ch.id) AS views_total
             FROM channels ch"""
    if active_only:
        sql += " WHERE ch.is_active = 1"
    return query(sql + " ORDER BY ch.name")


def add_channel(name: str, team_name: str, link: str, webhook: str = None, members: int = 0) -> int:
    return execute(
        "INSERT INTO channels(name,team_name,link,webhook_url,members,is_active,created_at)"
        " VALUES(?,?,?,?,?,1,?)",
        (name.strip(), (team_name or "").strip() or None, link.strip(),
         (webhook or "").strip() or None, members or 0, now()),
    )


def toggle_channel(cid: int):
    execute("UPDATE channels SET is_active = 1 - is_active WHERE id = ?", (cid,))


def delete_channel(cid: int):
    execute("DELETE FROM channels WHERE id = ?", (cid,))


# ----------------------------- Contents ---------------------------------
def list_contents(section: str = None, product_id: int = None, kind: str = None,
                  status: str = None, search: str = None, channel_id: int = None,
                  date_from: str = None, date_to: str = None, limit: int = None):
    sql = CONTENT_SELECT + " WHERE 1=1"
    params: list = []
    if section:
        sql += " AND c.section = ?"
        params.append(section)
    if product_id:
        sql += " AND c.product_id = ?"
        params.append(product_id)
    if kind:
        sql += " AND c.kind = ?"
        params.append(kind)
    if status:
        sql += " AND c.status = ?"
        params.append(status)
    if search:
        sql += " AND (c.title LIKE ? OR c.description LIKE ? OR p.name LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    if channel_id:
        sql += " AND EXISTS (SELECT 1 FROM distributions d WHERE d.content_id = c.id AND d.channel_id = ?)"
        params.append(channel_id)
    if date_from:
        sql += " AND date(c.created_at) >= date(?)"
        params.append(date_from)
    if date_to:
        sql += " AND date(c.created_at) <= date(?)"
        params.append(date_to)
    sql += " ORDER BY c.created_at DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return query(sql, tuple(params))


def get_content(cid: int):
    return query_one(CONTENT_SELECT + " WHERE c.id = ?", (cid,))


def create_content(**kw) -> int:
    return execute(
        """INSERT INTO contents(title,description,section,kind,product_id,file_name,file_path,mime,
               size_bytes,thumb_path,duration_sec,publish_date,status,created_by,created_at)
           VALUES(:title,:description,:section,:kind,:product_id,:file_name,:file_path,:mime,
               :size_bytes,:thumb_path,:duration_sec,:publish_date,:status,:created_by,:created_at)""",
        {**kw, "created_at": now()},
    )


def update_content(cid: int, **kw):
    fields = ", ".join(f"{k} = :{k}" for k in kw)
    execute(f"UPDATE contents SET {fields} WHERE id = :id", {**kw, "id": cid})


def delete_content(cid: int):
    execute("DELETE FROM contents WHERE id = ?", (cid,))


def set_tags(cid: int, tags: list[str]):
    with db() as conn:
        conn.execute("DELETE FROM content_tags WHERE content_id = ?", (cid,))
        conn.executemany(
            "INSERT OR IGNORE INTO content_tags(content_id, tag) VALUES(?,?)",
            [(cid, t.strip()) for t in tags if t.strip()],
        )


def get_tags(cid: int) -> list[str]:
    return [r["tag"] for r in query("SELECT tag FROM content_tags WHERE content_id = ? ORDER BY tag", (cid,))]


# --------------------------- Distribution -------------------------------
def create_distributions(content_id: int, channel_ids: list[int], message: str,
                         scheduled_at: str | None, user_id: int) -> list[int]:
    """Түгээлтийн мөрүүдийг үүсгэнэ. Товлосон бол `scheduled`, эсэхгүй бол `pending`.

    `sent` статус нь зөвхөн Teams руу БОДИТООР илгээгдсэний дараа тавигдана
    (main.py дахь илгээх алхам).
    """
    ids = []
    with db() as conn:
        for ch in channel_ids:
            cur = conn.execute(
                "INSERT INTO distributions(content_id,channel_id,status,message,scheduled_at,"
                "sent_at,created_by,created_at) VALUES(?,?,?,?,?,NULL,?,?)",
                (content_id, ch, "scheduled" if scheduled_at else "pending",
                 message or None, scheduled_at or None, user_id, now()),
            )
            ids.append(cur.lastrowid)
        conn.execute("UPDATE contents SET status = 'published' WHERE id = ?", (content_id,))
    return ids


def get_distribution(dist_id: int):
    return query_one(
        """SELECT d.*, ch.name AS channel_name, ch.link AS channel_link,
                  ch.webhook_url, ch.is_active,
                  c.title AS content_title, c.description AS content_description,
                  c.section, COALESCE(p.name,'') AS product_name
           FROM distributions d
           JOIN channels ch ON ch.id = d.channel_id
           JOIN contents c ON c.id = d.content_id
           LEFT JOIN products p ON p.id = c.product_id
           WHERE d.id = ?""",
        (dist_id,),
    )


def mark_sent(dist_id: int, ok: bool, detail: str):
    """Илгээлтийн үр дүнг бүртгэнэ. Алдаа гарвал `failed` болж, шалтгаан хадгалагдана."""
    execute(
        """UPDATE distributions
              SET status = ?, sent_at = ?, error = ?,
                  attempts = attempts + 1, last_try_at = ?
            WHERE id = ?""",
        ("sent" if ok else "failed", now() if ok else None,
         None if ok else (detail or "")[:500], now(), dist_id),
    )


def due_scheduled(limit: int = 50):
    """Илгээх хугацаа нь болсон, хүлээгдэж буй түгээлтүүд."""
    return query(
        """SELECT id FROM distributions
            WHERE status = 'scheduled' AND scheduled_at IS NOT NULL
              AND datetime(scheduled_at) <= datetime('now', 'localtime')
            ORDER BY scheduled_at LIMIT ?""",
        (limit,),
    )


def list_distributions(content_id: int = None, limit: int = 50):
    sql = """SELECT d.*, ch.name AS channel_name, ch.link AS channel_link, ch.team_name,
                    ch.webhook_url, c.title AS content_title, u.name AS sender
             FROM distributions d
             JOIN channels ch ON ch.id = d.channel_id
             JOIN contents c ON c.id = d.content_id
             LEFT JOIN users u ON u.id = d.created_by"""
    params = ()
    if content_id:
        sql += " WHERE d.content_id = ?"
        params = (content_id,)
    return query(sql + f" ORDER BY d.created_at DESC LIMIT {int(limit)}", params)


# ------------------------------ Views -----------------------------------
def log_view(content_id: int, user_id: int, channel_id: int = None, device: str = None) -> int:
    return execute(
        "INSERT INTO views(content_id,user_id,channel_id,watched_sec,completed,device,viewed_at)"
        " VALUES(?,?,?,0,0,?,?)",
        (content_id, user_id, channel_id, device, now()),
    )


def update_view_progress(view_id: int, watched_sec: int, completed: bool):
    execute(
        "UPDATE views SET watched_sec = MAX(watched_sec, ?), completed = MAX(completed, ?) WHERE id = ?",
        (int(watched_sec), 1 if completed else 0, view_id),
    )


# ----------------------------- Comments ---------------------------------
def add_comment(content_id: int, user_id: int, body: str, rating: int = None) -> int:
    return execute(
        "INSERT INTO comments(content_id,user_id,body,rating,created_at) VALUES(?,?,?,?,?)",
        (content_id, user_id, body.strip(), rating, now()),
    )


def list_comments(content_id: int):
    return query(
        """SELECT cm.*, u.name AS user_name, u.position, u.branch, u.avatar_hue
           FROM comments cm JOIN users u ON u.id = cm.user_id
           WHERE cm.content_id = ? ORDER BY cm.created_at DESC""",
        (content_id,),
    )


def delete_comment(cid: int):
    execute("DELETE FROM comments WHERE id = ?", (cid,))


# ---------------------------- Analytics ---------------------------------
def _view_filter(date_from=None, date_to=None, product_id=None, channel_id=None, section=None):
    sql, params = "", []
    if date_from:
        sql += " AND date(v.viewed_at) >= date(?)"
        params.append(date_from)
    if date_to:
        sql += " AND date(v.viewed_at) <= date(?)"
        params.append(date_to)
    if product_id:
        sql += " AND c.product_id = ?"
        params.append(product_id)
    if channel_id:
        sql += " AND v.channel_id = ?"
        params.append(channel_id)
    if section:
        sql += " AND c.section = ?"
        params.append(section)
    return sql, params


def kpi_summary(**f):
    where, params = _view_filter(**f)
    row = query_one(
        f"""SELECT COUNT(*) AS views_total,
                   COUNT(DISTINCT v.user_id) AS viewers_unique,
                   COUNT(DISTINCT v.content_id) AS contents_viewed,
                   COALESCE(SUM(v.watched_sec),0) AS watch_seconds,
                   COALESCE(AVG(v.completed),0) AS completion_rate
            FROM views v JOIN contents c ON c.id = v.content_id WHERE 1=1 {where}""",
        tuple(params),
    )
    extra = query_one(
        """SELECT (SELECT COUNT(*) FROM contents) AS contents_total,
                  (SELECT COUNT(*) FROM contents WHERE status='published') AS published_total,
                  (SELECT COUNT(*) FROM users) AS viewers_total,
                  (SELECT COUNT(*) FROM comments) AS comments_total,
                  (SELECT COUNT(*) FROM distributions WHERE status='sent') AS sent_total,
                  (SELECT COUNT(*) FROM distributions WHERE status='scheduled') AS scheduled_total,
                  (SELECT COUNT(*) FROM channels WHERE is_active=1) AS channels_total"""
    )
    out = dict(row)
    out.update(dict(extra))
    reach = out["viewers_total"] or 1
    out["reach_pct"] = min(round(out["viewers_unique"] / reach * 100, 1), 100.0)
    out["completion_rate"] = round((out["completion_rate"] or 0) * 100, 1)
    out["watch_hours"] = round((out["watch_seconds"] or 0) / 3600, 1)
    return out


def views_trend(days: int = 30, **f):
    where, params = _view_filter(**f)
    rows = query(
        f"""SELECT date(v.viewed_at) AS d, COUNT(*) AS views,
                   COUNT(DISTINCT v.user_id) AS viewers
            FROM views v JOIN contents c ON c.id = v.content_id
            WHERE date(v.viewed_at) >= date('now', ?) {where}
            GROUP BY d ORDER BY d""",
        (f"-{int(days)} day", *params),
    )
    by_day = {r["d"]: r for r in rows}
    today = datetime.now().date()
    labels, views, viewers = [], [], []
    for i in range(days, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        labels.append(d)
        views.append(by_day[d]["views"] if d in by_day else 0)
        viewers.append(by_day[d]["viewers"] if d in by_day else 0)
    return {"labels": labels, "views": views, "viewers": viewers}


def views_by_product(limit: int = 10, **f):
    where, params = _view_filter(**f)
    return query(
        f"""SELECT COALESCE(p.name,'Ангилалгүй') AS name, COALESCE(p.color,'#7c5cff') AS color,
                   COUNT(*) AS views, COUNT(DISTINCT v.user_id) AS viewers
            FROM views v JOIN contents c ON c.id = v.content_id
            LEFT JOIN products p ON p.id = c.product_id
            WHERE 1=1 {where}
            GROUP BY p.id ORDER BY views DESC LIMIT {int(limit)}""",
        tuple(params),
    )


def views_by_section(**f):
    where, params = _view_filter(**f)
    return query(
        f"""SELECT c.section AS section, COUNT(*) AS views, COUNT(DISTINCT v.user_id) AS viewers
            FROM views v JOIN contents c ON c.id = v.content_id
            WHERE 1=1 {where} GROUP BY c.section""",
        tuple(params),
    )


def views_by_channel(**f):
    where, params = _view_filter(**f)
    return query(
        f"""SELECT COALESCE(ch.name,'Тодорхойгүй') AS name, COUNT(*) AS views,
                   COUNT(DISTINCT v.user_id) AS viewers
            FROM views v JOIN contents c ON c.id = v.content_id
            LEFT JOIN channels ch ON ch.id = v.channel_id
            WHERE 1=1 {where} GROUP BY ch.id ORDER BY views DESC""",
        tuple(params),
    )


def top_contents(limit: int = 8, **f):
    where, params = _view_filter(**f)
    return query(
        f"""SELECT c.id, c.title, c.section, c.kind, c.thumb_path,
                   COALESCE(p.name,'Ангилалгүй') AS product_name,
                   COALESCE(p.color,'#7c5cff') AS product_color,
                   COUNT(*) AS views, COUNT(DISTINCT v.user_id) AS viewers
            FROM views v JOIN contents c ON c.id = v.content_id
            LEFT JOIN products p ON p.id = c.product_id
            WHERE 1=1 {where}
            GROUP BY c.id ORDER BY views DESC LIMIT {int(limit)}""",
        tuple(params),
    )


def top_users(limit: int = 10, **f):
    where, params = _view_filter(**f)
    return query(
        f"""SELECT u.id, u.name, u.position, u.branch, u.avatar_hue,
                   COUNT(*) AS views, COUNT(DISTINCT v.content_id) AS contents,
                   (SELECT COUNT(*) FROM comments cm WHERE cm.user_id = u.id) AS comments_total,
                   (SELECT COALESCE(p2.name,'—') FROM views v2
                      JOIN contents c2 ON c2.id = v2.content_id
                      LEFT JOIN products p2 ON p2.id = c2.product_id
                     WHERE v2.user_id = u.id
                     GROUP BY c2.product_id ORDER BY COUNT(*) DESC LIMIT 1) AS fav_product
            FROM views v JOIN contents c ON c.id = v.content_id
            JOIN users u ON u.id = v.user_id
            WHERE 1=1 {where}
            GROUP BY u.id ORDER BY views DESC LIMIT {int(limit)}""",
        tuple(params),
    )


def user_product_matrix(limit_users: int = 8, limit_products: int = 6, **f):
    """Хэрэглэгч × бүтээгдэхүүн — аль хэрэглэгч алийг их үзсэн."""
    where, params = _view_filter(**f)
    users = top_users(limit_users, **f)
    prods = views_by_product(limit_products, **f)
    pnames = [p["name"] for p in prods]
    rows = query(
        f"""SELECT u.id AS uid, COALESCE(p.name,'Ангилалгүй') AS pname, COUNT(*) AS views
            FROM views v JOIN contents c ON c.id = v.content_id
            LEFT JOIN products p ON p.id = c.product_id
            JOIN users u ON u.id = v.user_id
            WHERE 1=1 {where} GROUP BY u.id, p.id""",
        tuple(params),
    )
    lookup = {(r["uid"], r["pname"]): r["views"] for r in rows}
    matrix = [
        {"user": u["name"], "cells": [lookup.get((u["id"], pn), 0) for pn in pnames]}
        for u in users
    ]
    return {"products": pnames, "colors": [p["color"] for p in prods], "rows": matrix}


def hourly_heat(**f):
    where, params = _view_filter(**f)
    rows = query(
        f"""SELECT CAST(strftime('%H', v.viewed_at) AS INTEGER) AS h, COUNT(*) AS views
            FROM views v JOIN contents c ON c.id = v.content_id
            WHERE 1=1 {where} GROUP BY h ORDER BY h""",
        tuple(params),
    )
    data = {r["h"]: r["views"] for r in rows}
    return {"labels": [f"{h:02d}:00" for h in range(24)], "views": [data.get(h, 0) for h in range(24)]}


# --------------------------- Profile data -------------------------------
def user_history(user_id: int, limit: int = 100):
    return query(
        """SELECT c.id, c.title, c.section, c.kind, c.thumb_path,
                  COALESCE(p.name,'Ангилалгүй') AS product_name,
                  COALESCE(p.color,'#7c5cff') AS product_color,
                  COUNT(*) AS times, MAX(v.viewed_at) AS last_seen,
                  COALESCE(SUM(v.watched_sec),0) AS watched
           FROM views v JOIN contents c ON c.id = v.content_id
           LEFT JOIN products p ON p.id = c.product_id
           WHERE v.user_id = ?
           GROUP BY c.id ORDER BY last_seen DESC LIMIT ?""",
        (user_id, limit),
    )


def user_stats(user_id: int):
    row = query_one(
        """SELECT (SELECT COUNT(*) FROM views WHERE user_id=?) AS views_total,
                  (SELECT COUNT(DISTINCT content_id) FROM views WHERE user_id=?) AS contents_total,
                  (SELECT COUNT(*) FROM comments WHERE user_id=?) AS comments_total,
                  (SELECT COALESCE(SUM(watched_sec),0) FROM views WHERE user_id=?) AS watched,
                  (SELECT COUNT(*) FROM views WHERE user_id=? AND date(viewed_at) >= date('now','-7 day')) AS week_views""",
        (user_id, user_id, user_id, user_id, user_id),
    )
    return dict(row)


def user_comments(user_id: int, limit: int = 30):
    return query(
        """SELECT cm.*, c.title AS content_title, c.id AS content_id
           FROM comments cm JOIN contents c ON c.id = cm.content_id
           WHERE cm.user_id = ? ORDER BY cm.created_at DESC LIMIT ?""",
        (user_id, limit),
    )


def user_trend(user_id: int, days: int = 30):
    rows = query(
        """SELECT date(viewed_at) AS d, COUNT(*) AS views FROM views
           WHERE user_id = ? AND date(viewed_at) >= date('now', ?)
           GROUP BY d ORDER BY d""",
        (user_id, f"-{int(days)} day"),
    )
    by_day = {r["d"]: r["views"] for r in rows}
    today = datetime.now().date()
    labels = [(today - timedelta(days=i)).isoformat() for i in range(days, -1, -1)]
    return {"labels": labels, "views": [by_day.get(d, 0) for d in labels]}


def export_rows(**f):
    where, params = _view_filter(**f)
    return query(
        f"""SELECT v.viewed_at, u.name AS user_name, u.email, u.position, u.branch,
                   c.title AS content_title, c.section, c.kind,
                   COALESCE(p.name,'') AS product, COALESCE(ch.name,'') AS channel,
                   v.watched_sec, v.completed, v.device
            FROM views v
            JOIN contents c ON c.id = v.content_id
            JOIN users u ON u.id = v.user_id
            LEFT JOIN products p ON p.id = c.product_id
            LEFT JOIN channels ch ON ch.id = v.channel_id
            WHERE 1=1 {where} ORDER BY v.viewed_at DESC""",
        tuple(params),
    )
