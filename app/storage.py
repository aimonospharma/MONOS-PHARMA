"""Файл хадгалалт — бүх медиа app server дотор (`app/storage/`) байрлана."""
import mimetypes
import re
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse

from .config import (STORAGE_DIR, UPLOAD_DIR, THUMB_DIR, ALLOWED_EXT,
                     ALLOWED_VIDEO, ALLOWED_IMAGE, ALLOWED_DOC, MAX_UPLOAD_MB)

CHUNK = 1024 * 512


def kind_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_VIDEO:
        return "video"
    if ext in ALLOWED_DOC:
        return "pdf"
    return "image"


def save_upload(upload, subdir: str = "uploads") -> dict:
    """UploadFile-г диск рүү бичээд метадата буцаана."""
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Дэмжигдэхгүй файлын төрөл: {ext or '?'}")
    target_dir = STORAGE_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    dest = target_dir / name
    size = 0
    with dest.open("wb") as out:
        while True:
            chunk = upload.file.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(400, f"Файл хэт том байна (дээд хэмжээ {MAX_UPLOAD_MB}MB).")
            out.write(chunk)
    mime = upload.content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
    return {
        "file_name": upload.filename,
        "file_path": f"{subdir}/{name}",
        "mime": mime,
        "size_bytes": size,
        "kind": kind_for(upload.filename or name),
    }


PLACEHOLDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
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


def _xml_escape(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def make_placeholder_thumb(line1: str, line2: str, color: str = "#00e0a4") -> str:
    """Cover зураг оруулаагүй үед автоматаар gradient poster үүсгэнэ.

    `line1` — бүтээгдэхүүний нэр (эсвэл "MP team"), `line2` — контентын гарчиг.
    Текст нь SVG дотор зурагддаг тул гарчиг өөрчлөгдөх бүрд дахин дуудагдана.
    """
    name = f"auto-{uuid.uuid4().hex}.svg"
    (THUMB_DIR / name).write_text(
        PLACEHOLDER_SVG.format(
            line1=_xml_escape(str(line1).strip()[:22]),
            line2=_xml_escape(str(line2).strip()[:34]),
            c1=color, c2="#141a3a",
        ),
        encoding="utf-8",
    )
    return f"thumbs/{name}"


def is_auto_thumb(rel: str | None) -> bool:
    """Гарчиг шигтгэсэн автомат poster мөн үү? (`auto-*` — upload, `demo-*` — seed)

    Ийм зураг дээр текст нь зурагдчихсан байдаг тул гарчиг/өнгө өөрчлөгдөхөд
    дахин зурах шаардлагатай. Хэрэглэгчийн өөрөө оруулсан cover-т хамаарахгүй.
    """
    if not rel:
        return False
    name = Path(rel).name
    return rel.startswith("thumbs/") and (name.startswith("auto-") or name.startswith("demo-"))


def abs_path(rel: str) -> Path:
    p = (STORAGE_DIR / rel).resolve()
    if not str(p).startswith(str(STORAGE_DIR.resolve())):
        raise HTTPException(400, "Буруу зам.")
    return p


def delete_file(rel: str | None):
    if not rel:
        return
    try:
        abs_path(rel).unlink(missing_ok=True)
    except Exception:
        pass


RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def serve(rel: str, range_header: str | None = None, download_name: str | None = None):
    """Видео seek хийх боломжтой байхаар HTTP Range дэмжсэн файл түгээлт."""
    path = abs_path(rel)
    if not path.exists():
        raise HTTPException(404, "Файл олдсонгүй.")
    file_size = path.stat().st_size
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    headers = {"accept-ranges": "bytes", "cache-control": "public, max-age=3600"}
    if download_name:
        headers["content-disposition"] = f'attachment; filename="{download_name}"'

    if not range_header:
        return FileResponse(path, media_type=mime, headers=headers)

    m = RANGE_RE.match(range_header)
    if not m:
        return FileResponse(path, media_type=mime, headers=headers)
    start = int(m.group(1)) if m.group(1) else 0
    end = int(m.group(2)) if m.group(2) else file_size - 1
    end = min(end, file_size - 1)
    if start > end:
        return Response(status_code=416, headers={"content-range": f"bytes */{file_size}"})

    def iterator():
        with path.open("rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(CHUNK, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers.update({
        "content-range": f"bytes {start}-{end}/{file_size}",
        "content-length": str(end - start + 1),
    })
    return StreamingResponse(iterator(), status_code=206, media_type=mime, headers=headers)


def human_size(n: int) -> str:
    n = n or 0
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"
