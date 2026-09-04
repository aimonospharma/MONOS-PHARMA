"""Төвлөрсөн тохиргоо. Бүх зам, тогтмол утга энд байрлана."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

# Файлыг app server дотор хадгална (тусдаа cloud storage ашиглахгүй).
# Deploy дээр File Mount / volume холбосон бол MP_STORAGE_DIR, MP_DATA_DIR env-ээр
# гадагш нь чиглүүлж болно — тэгвэл дахин deploy хийхэд өгөгдөл устахгүй.
STORAGE_DIR = Path(os.environ.get("MP_STORAGE_DIR") or BASE_DIR / "storage").resolve()
DATA_DIR = Path(os.environ.get("MP_DATA_DIR") or BASE_DIR / "data").resolve()
UPLOAD_DIR = STORAGE_DIR / "uploads"
THUMB_DIR = STORAGE_DIR / "thumbs"
DB_PATH = DATA_DIR / "app.db"

for _d in (STORAGE_DIR, UPLOAD_DIR, THUMB_DIR, DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

APP_NAME = "MP team"
APP_TAGLINE = "Видео контент түгээх, хэмжих платформ"
COMPANY_DOMAIN = "monos.mn"

def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------- аюулгүй байдал
# DEMO_MODE=1 үед л mock login, demo Microsoft account, seed өгөгдөл ажиллана.
# Production дээр ЗААВАЛ 0 байх ёстой (default нь 0 — аюулгүй тал руугаа).
DEMO_MODE = _flag("DEMO_MODE", "0")

DEFAULT_SECRET = "monos-video-platform-dev-secret-change-me"
SECRET_KEY = os.environ.get("SECRET_KEY") or DEFAULT_SECRET
SESSION_COOKIE = "mp_session"
SESSION_HTTPS_ONLY = _flag("SESSION_HTTPS_ONLY", "0")

# Нууц үг нь хэрэглэгчийн мэйлийн ID хэсэг (name@monos.mn -> name).
# Нэвтрэхийг зөвшөөрөх шалгуур нь админаас оруулсан ажилтны лавлах (directory).
# Эдгээр хаягаар нэвтэрсэн хүн Admin эрх авна (бусад нь DB-д байгаагаараа).
ADMIN_EMAILS = {e.strip().lower() for e in
                (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()}
# Teams карт дээрх "Үзэх" товчны бүтэн хаяг үүсгэхэд хэрэглэнэ
PUBLIC_BASE_URL = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")

# ---------------------------------------------- Microsoft Entra ID (Azure AD) SSO
# Гурвуулаа бөглөгдсөн үед SSO автоматаар идэвхжиж, нууц үгийн (сул) арга
# хаагдана — хүн бүр өөрийн Microsoft бүртгэлээрээ нэвтэрнэ.
AZURE_TENANT_ID = (os.environ.get("AZURE_TENANT_ID") or "").strip()
AZURE_CLIENT_ID = (os.environ.get("AZURE_CLIENT_ID") or "").strip()
AZURE_CLIENT_SECRET = (os.environ.get("AZURE_CLIENT_SECRET") or "").strip()
SSO_ENABLED = bool(AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET)
SSO_CALLBACK_PATH = "/auth/microsoft/callback"

# Зөвхөн эдгээр домэйны хаягтай хүн нэвтэрнэ (tenant-аас гадуурх зочин хаягаас сэргийлнэ)
ALLOWED_EMAIL_DOMAINS = {
    d.strip().lower().lstrip("@")
    for d in (os.environ.get("ALLOWED_EMAIL_DOMAINS") or COMPANY_DOMAIN).split(",")
    if d.strip()
}


# SSO залгагдмагц нууц үгийн (сул) арга автоматаар хаагдана
PASSWORD_LOGIN_ENABLED = bool(DEMO_MODE or not SSO_ENABLED)


def sso_redirect_uri() -> str:
    """Azure App registration дээр бүртгүүлэх Redirect URI."""
    return f"{PUBLIC_BASE_URL}{SSO_CALLBACK_PATH}" if PUBLIC_BASE_URL else ""


def check_production_config() -> list[str]:
    """Production дээр эгзэгтэй тохиргоо дутуу бол алдааны жагсаалт буцаана."""
    problems = []
    if DEMO_MODE:
        return problems
    if SECRET_KEY == DEFAULT_SECRET:
        problems.append(
            "SECRET_KEY тохируулаагүй байна. Кодод бичсэн default утга нь GitHub дээр ил "
            "тул сесс cookie хуурамчаар үүсгэх боломжтой. Environment дээр "
            "SECRET_KEY=<санамсаргүй 64 тэмдэгт> нэмнэ үү."
        )
    if SSO_ENABLED and not PUBLIC_BASE_URL:
        problems.append(
            "SSO асаалттай атлаа PUBLIC_BASE_URL тохируулаагүй байна. Redirect URI "
            "үүсгэх боломжгүй тул нэвтрэлт ажиллахгүй."
        )
    if not ADMIN_EMAILS:
        problems.append(
            "ADMIN_EMAILS тохируулаагүй байна. Admin эрхтэй хүн байхгүй болно. "
            "ADMIN_EMAILS=ner@monos.mn гэж нэмнэ үү."
        )
    return problems

# Контентын үндсэн 2 хэсэг
SECTION_BONUS = "bonus"
SECTION_OTHER = "other"
SECTIONS = {
    SECTION_BONUS: "Жор баригч танд зориулсан бонус идэвхтэй бүтээгдэхүүн",
    SECTION_OTHER: "Бусад контент",
}
SECTION_SHORT = {
    SECTION_BONUS: "Бонус контент",
    SECTION_OTHER: "Бусад контент",
}

ROLE_ADMIN = "admin"
ROLE_VIEWER = "viewer"
ROLE_LABELS = {
    ROLE_ADMIN: "Admin / Marketing Manager",
    ROLE_VIEWER: "Viewer (Жор баригч / Эмийн мэргэжилтэн)",
}

ALLOWED_VIDEO = {".mp4", ".webm", ".mov", ".m4v", ".ogg"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
ALLOWED_DOC = {".pdf"}
ALLOWED_EXT = ALLOWED_VIDEO | ALLOWED_IMAGE | ALLOWED_DOC
# Урд талын proxy (Traefik/nginx)-ийн client_max_body_size-тай ижил байлгана.
# Тэндхийнээс их байвал хэрэглэгч 413 алдаа хараад шалтгааныг нь ойлгохгүй.
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "512"))

# Идэвхийн tier (нийт үзэлтээр)
TIERS = [
    (50, "Gold", "#f5c518"),
    (25, "Silver", "#c9d4e3"),
    (10, "Bronze", "#d08a52"),
    (0, "Starter", "#6b7ba8"),
]


def tier_for(view_count: int):
    for threshold, name, color in TIERS:
        if view_count >= threshold:
            return {"name": name, "color": color, "threshold": threshold}
    return {"name": "Starter", "color": "#6b7ba8", "threshold": 0}
