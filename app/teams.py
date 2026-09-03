"""Microsoft Teams руу Adaptive Card илгээх.

**Чухал:** Office 365 Connector (`https://outlook.office.com/webhook/...`) нь
2025 оны эцэст бүрмөсөн зогссон. Одоо ажилладаг цорын ганц webhook хувилбар нь
Power Automate **Workflows** ("Post to a channel when a webhook request is
received") бөгөөд URL нь иймэрхүү харагдана:

    https://prod-23.westus.logic.azure.com:443/workflows/<guid>/triggers/
    manual/paths/invoke?api-version=2016-06-01&sig=...

Хязгаарлалт: Teams доторх карт дээрх үзэлтийг хэмжих боломжгүй. Зөвхөн
"Үзэх" товч дарж апп руу орсон үед л статистик бүртгэгдэнэ. Тиймээс картад
видеог шууд биш, зөвхөн товч тавина.
"""
import logging

import httpx

from .config import PUBLIC_BASE_URL

log = logging.getLogger("mp.teams")

TIMEOUT = httpx.Timeout(15.0, connect=8.0)
LEGACY_HOSTS = ("outlook.office.com", "outlook.office365.com")


def is_legacy_webhook(url: str) -> bool:
    """Зогсоосон O365 Connector webhook мөн эсэх."""
    return any(h in (url or "") for h in LEGACY_HOSTS)


def content_url(content_id: int, channel_id: int | None = None) -> str:
    """Картны "Үзэх" товчны хаяг.

    `?channel=` параметр ЗААВАЛ орно — аль channel-аас хэдэн үзэлт ирснийг
    ингэж байж ялгаж хэмжинэ (/content/{id} route үүнийг уншиж views.channel_id-д бичнэ).
    """
    base = PUBLIC_BASE_URL or ""
    url = f"{base}/content/{content_id}"
    if channel_id:
        url += f"?channel={channel_id}"
    return url


def build_card(title: str, description: str, content_id: int, channel_id: int | None,
               product: str = "", section: str = "", note: str = "") -> dict:
    """Teams-д илгээх Adaptive Card payload."""
    facts = []
    if product:
        facts.append({"title": "Бүтээгдэхүүн", "value": product})
    if section:
        facts.append({"title": "Хэсэг", "value": section})

    body = [{"type": "TextBlock", "text": title, "weight": "Bolder",
             "size": "Large", "wrap": True}]
    if note:
        body.append({"type": "TextBlock", "text": note, "wrap": True, "isSubtle": True})
    if description:
        body.append({"type": "TextBlock", "text": description[:600], "wrap": True})
    if facts:
        body.append({"type": "FactSet", "facts": facts})

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": body,
                "actions": [{
                    "type": "Action.OpenUrl",
                    "title": "Үзэх",
                    "url": content_url(content_id, channel_id),
                }],
            },
        }],
    }


def send(webhook_url: str, card: dict) -> tuple[bool, str]:
    """Картыг webhook руу илгээнэ. `(амжилттай_эсэх, тайлбар)` буцаана.

    Сүлжээний алдаа гарсан ч exception шиднэ гүй — түгээлтийн мөрөнд алдааг
    хадгалж, дараа нь дахин оролдох боломжтой байлгах нь зорилго.
    """
    if not webhook_url:
        return False, ("Webhook URL оруулаагүй байна. Teams → channel → ⋯ → Workflows → "
                       "'Post to a channel when a webhook request is received' үүсгэж, "
                       "URL-г Channel тохиргоонд нэмнэ үү.")
    if is_legacy_webhook(webhook_url):
        return False, ("Энэ бол зогсоосон Office 365 Connector webhook. Power Automate "
                       "Workflows-оор шинэ webhook үүсгэнэ үү.")
    if not PUBLIC_BASE_URL:
        return False, ("PUBLIC_BASE_URL тохируулаагүй тул картын 'Үзэх' товч ажиллахгүй. "
                       "Environment дээр PUBLIC_BASE_URL=https://<домэйн> нэмнэ үү.")
    try:
        r = httpx.post(webhook_url, json=card, timeout=TIMEOUT)
    except httpx.TimeoutException:
        return False, "Хугацаа хэтэрлээ (timeout). Дараа дахин оролдоно уу."
    except httpx.HTTPError as e:
        return False, f"Сүлжээний алдаа: {type(e).__name__}: {e}"[:400]

    # Power Automate амжилттай үед ихэвчлэн 202 Accepted буцаадаг
    if 200 <= r.status_code < 300:
        return True, f"HTTP {r.status_code}"
    body = (r.text or "").strip().replace("\n", " ")[:300]
    log.warning("Teams webhook %s -> %s %s", webhook_url[:60], r.status_code, body)
    return False, f"HTTP {r.status_code}: {body or 'хоосон хариу'}"
