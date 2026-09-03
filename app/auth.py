"""Нэвтрэлт.

Prototype горим: email + нэрээр mock login, эсвэл "Sign in with Microsoft" товчоор
demo Microsoft account сонгож нэвтэрнэ.

Production: доорх `MICROSOFT_SSO` блок дахь тэмдэглэлийн дагуу Azure AD (Microsoft
Entra ID) OAuth2 authorization-code урсгалыг залгана. Route-ууд өөрчлөгдөхгүй — зөвхөн
`resolve_microsoft_user()` функцийн дотор Graph API-аас ирсэн профайлыг буулгана.
"""
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from . import repo
from .config import ROLE_ADMIN, ROLE_VIEWER, COMPANY_DOMAIN

# --- MICROSOFT_SSO (production-д бөглөх) ---------------------------------
# AZURE_TENANT_ID = "<tenant-id>"
# AZURE_CLIENT_ID = "<app-id>"
# AZURE_CLIENT_SECRET = "<secret>"
# AUTHORIZE_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize"
# TOKEN_URL     = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
# GRAPH_ME      = "https://graph.microsoft.com/v1.0/me?$select=displayName,mail,jobTitle,officeLocation,department
# SCOPES        = "openid profile email User.Read"
# Teams tab дотор: microsoftTeams.authentication.getAuthToken() -> on-behalf-of flow.
# -------------------------------------------------------------------------

# Demo Microsoft account-ууд ("Sign in with Microsoft" товч дарахад сонгогдоно)
DEMO_MS_ACCOUNTS = [
    {"email": "admin@monos.mn", "name": "Маркетингийн менежер", "role": ROLE_ADMIN,
     "position": "Marketing Manager", "branch": "Төв оффис", "department": "Marketing"},
    {"email": "bolormaa.b@monos.mn", "name": "Б. Болормаа", "role": ROLE_VIEWER,
     "position": "Жор баригч", "branch": "Сансар салбар", "department": "Retail"},
    {"email": "tuvshin.d@monos.mn", "name": "Д. Түвшин", "role": ROLE_VIEWER,
     "position": "Эмийн мэргэжилтэн", "branch": "Төв салбар", "department": "Retail"},
]


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
    request.session["uid"] = user["id"]
    repo.touch_login(user["id"])


def logout(request: Request):
    request.session.clear()


def sign_in_mock(request: Request, email: str, name: str, role: str = None,
                 position: str = None, branch: str = None, source: str = "mock"):
    """Email + нэрээр нэвтрэх. Байхгүй бол шинээр үүсгэнэ."""
    email = (email or "").strip()
    if not email:
        raise ValueError("Мэйл хаяг шаардлагатай.")
    if "@" not in email:
        email = f"{email}@{COMPANY_DOMAIN}"
    user = repo.get_user_by_email(email)
    if user is None:
        # @monos.mn хаягтай хүн шууд нэгдэнэ (demo горим)
        user = repo.create_user(
            email=email,
            name=(name or email.split("@")[0]).strip(),
            role=role or (ROLE_ADMIN if email.lower().startswith("admin@") else ROLE_VIEWER),
            position=position or "Жор баригч",
            branch=branch or "Тодорхойгүй салбар",
            department="Retail",
            source=source,
        )
    elif role and user["role"] != role:
        repo.update_user_role(user["id"], role)
        user = repo.get_user(user["id"])
    login_session(request, user)
    return user


def resolve_microsoft_user(request: Request, email: str):
    """Production-д энэ функц Graph API-аас ирсэн профайлыг хүлээж авна."""
    acc = next((a for a in DEMO_MS_ACCOUNTS if a["email"] == email), DEMO_MS_ACCOUNTS[1])
    return sign_in_mock(request, acc["email"], acc["name"], acc["role"],
                        acc["position"], acc["branch"], source="microsoft")


def redirect_login(next_url: str = "/"):
    return RedirectResponse(f"/login?next={next_url}", status_code=303)
