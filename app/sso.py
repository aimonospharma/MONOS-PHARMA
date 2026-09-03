"""Microsoft Entra ID (Azure AD) SSO — OAuth2 authorization code flow + PKCE.

Урсгал:

    1. Хэрэглэгч "Sign in with Microsoft" дарна      → /auth/microsoft
    2. Бид Microsoft-ийн authorize хуудас руу явуулна (state + PKCE сесст хадгална)
    3. Хэрэглэгч Microsoft дээрээ нэвтэрнэ
    4. Microsoft буцаана                              → /auth/microsoft/callback?code=...
    5. Бид code-г token болгож солино (client_secret + code_verifier)
    6. Graph /me-ээс профайл татна (нэр, албан тушаал, салбар)
    7. Сесс үүсгэнэ

Azure App registration дээр тохируулах зүйлс:
    * Redirect URI (Web):  <PUBLIC_BASE_URL>/auth/microsoft/callback
    * API permissions (delegated): openid, profile, email, User.Read
    * Certificates & secrets → client secret

Tenant-specific authority ашиглаж байгаа тул зөвхөн танай байгууллагын хүн
нэвтэрнэ. Үүн дээр нэмээд `ALLOWED_EMAIL_DOMAINS`-аар домэйн шалгана.
"""
import base64
import hashlib
import logging
import secrets
import urllib.parse

import httpx

from .config import (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
                     SSO_ENABLED, ALLOWED_EMAIL_DOMAINS, sso_redirect_uri)

log = logging.getLogger("mp.sso")

SCOPES = "openid profile email User.Read"
GRAPH_ME = ("https://graph.microsoft.com/v1.0/me"
            "?$select=displayName,mail,userPrincipalName,jobTitle,officeLocation,"
            "department,mobilePhone")
TIMEOUT = httpx.Timeout(15.0, connect=8.0)


def _authority() -> str:
    return f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0"


def new_pkce() -> tuple[str, str]:
    """(code_verifier, code_challenge) хос үүсгэнэ."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def authorize_url(state: str, challenge: str) -> str:
    """Хэрэглэгчийг явуулах Microsoft-ийн нэвтрэх хуудасны хаяг."""
    params = {
        "client_id": AZURE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": sso_redirect_uri(),
        "response_mode": "query",
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{_authority()}/authorize?" + urllib.parse.urlencode(params)


def exchange_code(code: str, verifier: str) -> tuple[str | None, str]:
    """Authorization code-г access token болгож солино. `(token, алдаа)`."""
    data = {
        "client_id": AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": sso_redirect_uri(),
        "scope": SCOPES,
        "code_verifier": verifier,
    }
    try:
        r = httpx.post(f"{_authority()}/token", data=data, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        return None, f"Microsoft-той холбогдож чадсангүй: {type(e).__name__}"
    if r.status_code != 200:
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        desc = body.get("error_description") or r.text[:200]
        log.warning("Token солилцоо амжилтгүй: %s %s", r.status_code, desc)
        return None, f"Token авахад алдаа гарлаа: {desc[:200]}"
    token = r.json().get("access_token")
    return (token, "") if token else (None, "Microsoft-оос token ирсэнгүй.")


def fetch_profile(access_token: str) -> tuple[dict | None, str]:
    """Graph /me-ээс профайл татаж, дотоод талбаруудад буулгана."""
    try:
        r = httpx.get(GRAPH_ME, headers={"Authorization": f"Bearer {access_token}"},
                      timeout=TIMEOUT)
    except httpx.HTTPError as e:
        return None, f"Graph API-тай холбогдож чадсангүй: {type(e).__name__}"
    if r.status_code != 200:
        return None, f"Graph API алдаа: HTTP {r.status_code}"

    me = r.json()
    email = (me.get("mail") or me.get("userPrincipalName") or "").strip()
    if not email:
        return None, "Microsoft бүртгэлээс мэйл хаяг олдсонгүй."

    domain = email.rsplit("@", 1)[-1].lower()
    if ALLOWED_EMAIL_DOMAINS and domain not in ALLOWED_EMAIL_DOMAINS:
        allowed = ", ".join(sorted(ALLOWED_EMAIL_DOMAINS))
        return None, (f"'{domain}' домэйн зөвшөөрөгдөөгүй байна. "
                      f"Зөвхөн {allowed} хаягаар нэвтэрнэ.")

    return {
        "email": email,
        "name": (me.get("displayName") or email.split("@")[0]).strip(),
        "position": (me.get("jobTitle") or "").strip() or None,      # албан тушаал
        "branch": (me.get("officeLocation") or "").strip() or None,  # салбар
        "department": (me.get("department") or "").strip() or None,
        "phone": (me.get("mobilePhone") or "").strip() or None,
    }, ""


def status() -> dict:
    """Тохиргооны төлөвийг UI/лог дээр харуулахад."""
    return {
        "enabled": SSO_ENABLED,
        "tenant": AZURE_TENANT_ID or "—",
        "client_id": AZURE_CLIENT_ID or "—",
        "redirect_uri": sso_redirect_uri() or "(PUBLIC_BASE_URL тохируулаагүй)",
        "scopes": SCOPES,
        "domains": sorted(ALLOWED_EMAIL_DOMAINS),
    }
