"""Төвлөрсөн тохиргоо. Бүх зам, тогтмол утга энд байрлана."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

# Файлыг app server дотор хадгална (тусдаа cloud storage ашиглахгүй)
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
THUMB_DIR = STORAGE_DIR / "thumbs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

for _d in (STORAGE_DIR, UPLOAD_DIR, THUMB_DIR, DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SECRET_KEY = "monos-video-platform-dev-secret-change-in-production"
SESSION_COOKIE = "mp_session"

APP_NAME = "MP team"
APP_TAGLINE = "Видео контент түгээх, хэмжих платформ"
COMPANY_DOMAIN = "monos.mn"

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
MAX_UPLOAD_MB = 512

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
