"""MM Evidence images of a Deal (Update_019), ported from the Management Dashboard (``report_mm_evidence_082``).

The Evidence of a Deal is the HTML field ``crm.lead.x_yp_evidence_html``. Its ``<img>`` tags point at

* ``data:image/...;base64,...``                       pasted straight into the HTML, or
* ``/web/image/<attachment id>[-<checksum>]/<name>``   what the Odoo 19 editor writes today (``5473-fc173dfd/image.png``), or
* ``/web/image/ir.attachment/<id>/datas`` / ``/web/content/<id>``   older forms.

The Dashboard v2.3.9 only knew the last two, so it would have skipped every image written by the current editor; the
``-<checksum>`` form is accepted here (all 21 images of the 29 Deals in MM / Approved MM were read this way on 2026-11-17).

Everything is read with the signed-in user's own environment: a user only gets the Evidence of Deals the CRM lets them see,
and Odoo's own attachment rights apply. Nothing is written and no URL outside this Odoo is ever fetched.
"""
from __future__ import annotations

import base64
import binascii
import io
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote, urlsplit

LEAD = "crm.lead"
ATTACHMENT = "ir.attachment"
FIELD_EVIDENCE = "x_yp_evidence_html"
MAX_HTML = 12 * 1024 * 1024
MAX_IMAGE = 8 * 1024 * 1024
MAX_IMAGES = 150
MAX_PIXELS = 40_000_000
SIZES = {"thumb": (360, 78), "large": (1600, 88)}      # longest side in px, JPEG quality

_DATA_RE = re.compile(r"^data:image/(?:png|jpe?g|gif|webp);base64,", re.I)
_ATT_RES = (re.compile(r"/web/(?:image|content)/ir\.attachment/(\d+)(?:/[^/]*)?/?"),
            re.compile(r"/web/(?:image|content)/(\d+)(?:-[0-9a-f]+)?(?:/[^/]*)?/?"))


class EvidenceError(ValueError):
    """Message that is safe to show to the user."""


class _Images(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        a = dict(attrs)
        src = (a.get("src") or a.get("data-src") or "").strip()
        if src:
            self.sources.append(src)


def image_sources(html: Any) -> list[str]:
    if not isinstance(html, str) or not html.strip():
        return []
    if len(html) > MAX_HTML:
        raise EvidenceError("Trường Evidence quá lớn để đọc an toàn.")
    parser = _Images()
    parser.feed(html)
    if len(parser.sources) > MAX_IMAGES:
        raise EvidenceError(f"Evidence có quá {MAX_IMAGES} ảnh; cần xử lý riêng để không bỏ sót.")
    return parser.sources


def classify(src: str, base_host: str | None = None) -> tuple[str, Any] | None:
    """('data', payload) | ('att', attachment id) | None when the source cannot be read safely (outside this Odoo, odd path)."""
    if _DATA_RE.match(src):
        return "data", src.split(",", 1)[1]
    parts = urlsplit(src)
    if parts.scheme or parts.netloc:
        if parts.scheme not in ("http", "https") or (base_host and (parts.hostname or "").lower() != base_host.lower()):
            return None
    path = unquote(parts.path)
    for rx in _ATT_RES:
        m = rx.fullmatch(path)
        if m:
            return "att", int(m.group(1))
    return None


def summarize(html: Any, base_host: str | None = None) -> tuple[list[int], int, str]:
    """(indexes of readable images, number of images found, note) — never says "no image" when a field could not be read."""
    try:
        sources = image_sources(html)
    except EvidenceError as exc:
        return [], 0, str(exc)
    usable = [i for i, s in enumerate(sources) if classify(s, base_host)]
    note = ""
    if len(usable) < len(sources):
        note = f"{len(sources) - len(usable)} ảnh nằm ngoài Odoo hoặc có dạng đường dẫn chưa hỗ trợ; không tự tải từ nơi khác."
    return usable, len(sources), note


def _decode(value: Any) -> bytes:
    if not isinstance(value, str) or not value or len(value) > MAX_IMAGE * 2:
        raise EvidenceError("File Evidence rỗng hoặc vượt giới hạn dung lượng.")
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise EvidenceError("File ảnh Evidence không phải dữ liệu base64 hợp lệ.") from exc
    if not data or len(data) > MAX_IMAGE:
        raise EvidenceError("Ảnh Evidence rỗng hoặc vượt 8 MB.")
    return data


def sniff(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise EvidenceError("Evidence không phải PNG/JPEG/GIF/WebP an toàn.")


def load_original(gateway, session, lead_id: int, index: int, base_host: str | None = None) -> bytes:
    """Bytes of image ``index`` of the Deal's Evidence, read with the caller's own rights."""
    if not (isinstance(lead_id, int) and lead_id > 0 and isinstance(index, int) and 0 <= index < MAX_IMAGES):
        raise EvidenceError("Yêu cầu ảnh Evidence không hợp lệ.")
    record = gateway.call(session, LEAD, "read", [[lead_id]], {"fields": ["id", FIELD_EVIDENCE]})
    if not isinstance(record, list) or len(record) != 1 or record[0].get("id") != lead_id:
        raise EvidenceError("Không đọc được Evidence của Deal này (không có quyền hoặc Deal không tồn tại).")
    sources = image_sources(record[0].get(FIELD_EVIDENCE))
    if index >= len(sources):
        raise EvidenceError("Deal không có ảnh Evidence ở vị trí này.")
    kind = classify(sources[index], base_host)
    if kind is None:
        raise EvidenceError("Ảnh Evidence này nằm ngoài Odoo hoặc có đường dẫn chưa hỗ trợ.")
    if kind[0] == "data":
        data = _decode(kind[1])
    else:
        att = gateway.call(session, ATTACHMENT, "read", [[kind[1]]], {"fields": ["id", "datas"]})
        if not isinstance(att, list) or len(att) != 1 or att[0].get("id") != kind[1]:
            raise EvidenceError("Không đọc được tệp đính kèm của ảnh Evidence.")
        data = _decode(att[0].get("datas") or "")
    sniff(data)
    return data


def render(data: bytes, size: str) -> tuple[bytes, str]:
    """Scaled copy (JPEG, white behind transparency) so a page of Deals stays light. Raises EvidenceError on a bad image."""
    if size not in SIZES:
        raise EvidenceError("Kích thước ảnh không hợp lệ.")
    from PIL import Image, ImageOps, UnidentifiedImageError   # Pillow ships with Odoo
    longest, quality = SIZES[size]
    try:
        image = Image.open(io.BytesIO(data))
        if image.width * image.height > MAX_PIXELS:
            raise EvidenceError("Ảnh Evidence có kích thước điểm ảnh quá lớn.")
        image.seek(0)
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            flat = Image.new("RGB", image.size, (255, 255, 255))
            flat.paste(image, mask=image.getchannel("A"))
            image = flat
        else:
            image = image.convert("RGB")
        image.thumbnail((longest, longest))
        out = io.BytesIO()
        image.save(out, "JPEG", quality=quality, optimize=True)
    except EvidenceError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise EvidenceError("Không giải mã được ảnh Evidence.") from exc
    return out.getvalue(), "image/jpeg"
