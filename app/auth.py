"""Нэвтрэлт.

Аюулгүй байдлын гол зарчмууд:

* Эрхийг (role) хэзээ ч формоос авдаггүй — DB-д байгаа утга нь эх сурвалж.
  Зөвхөн `ADMIN_EMAILS` жагсаалтад байгаа хаяг Admin болж bootstrap хийгдэнэ.
* `DEMO_MODE=0` (production default) үед mock login болон demo Microsoft
  account-ууд бүрэн хаагдана.
* SSO залгагдах хүртэл production дээр `LOGIN_PASSWORD` шаардана.

Production (Azure AD / Microsoft Entra ID) руу шилжихэд `MICROSOFT_SSO` блокийн
дагуу `resolve_microsoft_user()`-ийн дотор талыг л сольно — route өөрчлөгдөхгүй.
"""
import hmac

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from . import repo
from .config import (ROLE_ADMIN, ROLE_VIEWER, COMPANY_DOMAIN, DEMO_MODE,
                     LOGIN_PASSWORD, ADMIN_EMAILS)

# --- MICROSOFT_SSO (production-д бөглөх) ---------------------------------
# AZURE_TENANT_ID = "<tenant-id>"
# AZURE_CLIENT_ID = "<app-id>"
# AZURE_CLIENT_SECRET = "<secret>"
# AUTHORIZE_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize"
# TOKEN_URL     = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
# GRAPH_ME      = "https://graph.microsoft.com/v1.0/me?$select=displayName,mail,jobTitle,officeLocation,department"
# SCOPES        = "openid profile email User.Read"
# Teams tab дотор: microsoftTeams.authentication.getAuthToken() -> on-behalf-of flow.
# -------------------------------------------------------------------------

# Demo Microsoft account-ууд — ЗӨВХӨН DEMO_MODE=1 үед ашиглагдана
DEMO_MS_ACCOUNTS = [
    {"email": "admin@monos.mn", "name": "Маркетингийн менежер", "role": ROLE_ADMIN,
     "position": "Marketing Manager", "branch": "Төв оффис", "department": "Marketing"},
    {"email": "bolormaa.b@monos.mn", "name": "Б. Болормаа", "role": ROLE_VIEWER,
     "position": "Жор баригч", "branch": "Сансар салбар", "department": "Retail"},
    {"email": "tuvshin.d@monos.mn", "name": "Д. Түвшин", "role": ROLE_VIEWER,
     "position": "Эмийн мэргэжилтэн", "branch": "Төв салбар", "department": "Retail"},
]


def demo_accounts():
    """Login дэлгэц дээр demo account харуулах эсэх."""
    return DEMO_MS_ACCOUNTS if DEMO_MODE else []


def require_demo_mode():
    if not DEMO_MODE:
        raise HTTPException(404, "Энэ хаяг зөвхөн demo горимд ажиллана.")


def check_password(supplied: str) -> bool:
    """Production дээр нэвтрэхэд шаардах түр нууц үг.

    DEMO_MODE=1 үед нууц үг шаардахгүй. Тогтмол хугацааны харьцуулалт
    ашиглаж, нууц үг таамаглах довтолгооноос сэргийлнэ.
    """
    if DEMO_MODE:
        return True
    if not LOGIN_PASSWORD:
        return False          # тохируулаагүй бол хэн ч нэвтэрч чадахгүй
    return hmac.compare_digest((supplied or "").strip(), LOGIN_PASSWORD)


def current_user(request: Request):
    uid = request.session.get("uid")
    if not uid:
        return None
    user = repo.get_user(uid)
    if not user:
        request.session.clear()
        return None
    return user


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="login-required")
    return user


def require_admin(request: Request):
    user = require_user(request)
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Зөвхөн Admin эрхтэй хэрэглэгч хандах боломжтой.")
    return user


def login_session(request: Request, user):
    request.session.clear()          # сесс солигдоход хуучин утгыг үлдээхгүй
    request.session["uid"] = user["id"]
    repo.touch_login(user["id"])


def logout(request: Request):
    request.session.clear()


def _resolve_role(email: str, existing) -> str:
    """Эрхийг DB болон ADMIN_EMAILS-аас тодорхойлно. Хэрэглэгчийн оролтоос АВАХГҮЙ."""
    if email.lower() in ADMIN_EMAILS:
        return ROLE_ADMIN
    if existing is not None:
        return existing["role"]
    return ROLE_VIEWER


def sign_in(request: Request, email: str, name: str = "", position: str = None,
            branch: str = None, department: str = None, source: str = "mock"):
    """Email-ээр нэвтрэх. Эрхийг DB/ADMIN_EMAILS-аас л тодорхойлно."""
    email = (email or "").strip()
    if not email:
        raise ValueError("Мэйл хаяг шаардлагатай.")
    if "@" not in email:
        email = f"{email}@{COMPANY_DOMAIN}"

    user = repo.get_user_by_email(email)
    role = _resolve_role(email, user)
    if user is None:
        user = repo.create_user(
            email=email,
            name=(name or email.split("@")[0]).strip(),
            role=role,
            position=position or "Жор баригч",
            branch=branch or "Тодорхойгүй салбар",
            department=department or "Retail",
            source=source,
        )
    elif user["role"] != role:
        # ADMIN_EMAILS-д нэмэгдсэн/хасагдсан бол л өөрчлөгдөнө
        repo.update_user_role(user["id"], role)
        user = repo.get_user(user["id"])
    login_session(request, user)
    return user


def resolve_microsoft_user(request: Request, email: str):
    """DEMO горим: Microsoft SSO-г дуурайлгана.

    Production-д энэ функц Graph API-аас ирсэн профайлыг хүлээж авна.
    """
    require_demo_mode()
    acc = next((a for a in DEMO_MS_ACCOUNTS if a["email"] == email), DEMO_MS_ACCOUNTS[1])
    return sign_in(request, acc["email"], acc["name"], acc["position"],
                   acc["branch"], acc["department"], source="microsoft")


def redirect_login(next_url: str = "/"):
    return RedirectResponse(f"/login?next={next_url}", status_code=303)
