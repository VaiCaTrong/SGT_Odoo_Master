"""CRM-005 Update_064: pure helpers for Documents -> Image Gallery (no Odoo import).

Only JPG / PNG / WebP are accepted. The real format is verified with Pillow, never taken from
the file name or the stored mimetype. Nothing is fetched from the network.
"""
import base64
import binascii
import hashlib
import io
import re
from html import escape, unescape

from PIL import Image, ImageOps, UnidentifiedImageError

PUSH_MAX_IMAGES = 200
PUSH_MAX_BYTES = 3 * 1024 * 1024          # per image stored in the Gallery HTML
PUSH_MAX_PIXELS = 60_000_000
PUSH_MAX_HTML_BYTES = 40 * 1024 * 1024    # whole Gallery field after the push
PUSH_SHRINK_EDGE = 1600
PUSH_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}

_DATA_URI_RE = re.compile(r'''src\s*=\s*["']data:image/[a-zA-Z0-9.+-]+;base64,([^"']+)["']''', re.I)


class PushImageError(Exception):
    """Per-image failure, safe to show to the employee."""


def existing_hashes(raw_html):
    """SHA1 of every inline (data URI) picture already in the Gallery HTML."""
    found = set()
    for match in _DATA_URI_RE.finditer(raw_html or ''):
        try:
            decoded = base64.b64decode(re.sub(r'\s+', '', match.group(1)), validate=True)
        except (binascii.Error, ValueError):
            continue
        if decoded:
            found.add(hashlib.sha1(decoded).hexdigest())
    return found


def prepare_image(data):
    """Return ``(stored_bytes, mimetype)`` for a picture, shrinking it if it is too heavy.

    Pictures up to PUSH_MAX_BYTES are stored byte for byte (so re-pushing the same file is
    detected as a duplicate). Heavier ones are scaled down to PUSH_SHRINK_EDGE px and stored
    as JPEG; if they are still too heavy the picture is refused.
    """
    if not data:
        raise PushImageError('File rỗng.')
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        width, height = img.size
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise PushImageError('Không đọc được file ảnh.')
    if fmt not in PUSH_FORMATS:
        raise PushImageError('Định dạng %s không được nhận (chỉ JPG/PNG/WebP).' % (fmt or 'không rõ'))
    if width * height > PUSH_MAX_PIXELS:
        raise PushImageError('Ảnh có kích thước quá lớn.')
    if len(data) <= PUSH_MAX_BYTES:
        return data, PUSH_FORMATS[fmt]
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        img = ImageOps.exif_transpose(img)
        img.thumbnail((PUSH_SHRINK_EDGE, PUSH_SHRINK_EDGE))
        if img.mode in ('RGBA', 'LA', 'P'):
            rgba = img.convert('RGBA')
            flat = Image.new('RGB', rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.split()[-1])
            img = flat
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        out = io.BytesIO()
        img.save(out, 'JPEG', quality=82, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise PushImageError('Không thu nhỏ được ảnh quá nặng.')
    stored = out.getvalue()
    if len(stored) > PUSH_MAX_BYTES:
        raise PushImageError('Ảnh quá nặng (>3MB) kể cả sau khi thu nhỏ.')
    return stored, 'image/jpeg'


def caption_from_name(name):
    """File name without extension, control characters removed, max 100 chars."""
    base = re.sub(r'\.[A-Za-z0-9]{1,5}$', '', name or '').strip()
    base = re.sub(r'[\x00-\x1f\x7f]', '', base)
    return base[:100]


def figure_html(name, mime, data):
    """One Gallery tile in the same shape the Chrome extension writes: figure > img + figcaption."""
    caption = escape(caption_from_name(name), quote=True)
    payload = base64.b64encode(data).decode('ascii')
    return ('<figure><img src="data:%s;base64,%s" alt="%s"><figcaption>%s</figcaption></figure>'
            % (mime, payload, caption, caption))


_ESCAPED_FIGURE_RE = re.compile(r'&lt;figure&gt;.*?&lt;/figure&gt;', re.S)


def heal_escaped_figures(raw_html):
    """Repair tiles written by Update_064 as visible text.

    Odoo returns Html values as markupsafe.Markup, and ``Markup + str`` HTML-escapes the str, so a push onto a
    Gallery that already had content stored ``&lt;figure&gt;...`` (shown as raw text). Only text that is clearly one
    of our own tiles (an escaped ``<img src="data:image/...``) is unescaped once; everything else is left alone.
    """
    def _fix(match):
        text = match.group(0)
        if '&lt;img src=&#34;data:image/' not in text and '&lt;img src="data:image/' not in text:
            return text
        return unescape(text)
    return _ESCAPED_FIGURE_RE.sub(_fix, str(raw_html or ''))


def merge_gallery_html(existing_html, figures):
    """Append new tiles after the existing HTML; existing pictures are never touched.

    Both sides are converted to plain str first: ``Markup + str`` would escape the new tiles.
    """
    return str(existing_html or '') + ''.join(str(f) for f in figures)
