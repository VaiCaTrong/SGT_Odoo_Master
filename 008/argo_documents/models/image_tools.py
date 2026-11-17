"""Nén ảnh & tạo thumbnail cho Kho tài liệu.

Nguyên tắc:
- Ảnh lớn hơn ``max_px`` được thu nhỏ (giữ tỉ lệ).
- Ảnh không dùng nền trong suốt -> JPEG (quality cấu hình), progressive.
- Ảnh có nền trong suốt -> giữ PNG (optimize).
- Không đụng tới GIF động, SVG, ICO, HEIC... (định dạng PIL không xử lý an toàn).
- Nếu kết quả không nhỏ hơn bản gốc thì giữ bản gốc.
"""
import io
import logging
import os

from PIL import Image, ImageOps

_logger = logging.getLogger(__name__)

# Chống "decompression bomb": ảnh quá 50 megapixel thì bỏ qua xử lý
MAX_PIXELS = 50_000_000
COMPRESSIBLE_FORMATS = {'JPEG', 'MPO', 'PNG', 'BMP', 'TIFF', 'WEBP'}
# Ảnh đã nhỏ & đủ kích thước thì không nén lại để tránh giảm chất lượng vô ích
SKIP_BELOW_BYTES = 300 * 1024


def _open(data):
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > MAX_PIXELS:
            return None
        img.load()
        return img
    except Exception:  # noqa: BLE001 - file không phải ảnh hợp lệ
        return None


def _uses_alpha(img):
    if img.mode in ('RGBA', 'LA', 'PA') or (img.mode == 'P' and 'transparency' in img.info):
        try:
            alpha = img.convert('RGBA').getchannel('A')
            return alpha.getextrema()[0] < 255
        except Exception:  # noqa: BLE001
            return True
    return False


def _encode(img, fmt, quality=80):
    out = io.BytesIO()
    if fmt == 'JPEG':
        img.save(out, 'JPEG', quality=quality, optimize=True, progressive=True)
    else:
        img.save(out, 'PNG', optimize=True)
    return out.getvalue()


def compress_image(data, filename, max_px=1920, quality=80):
    """Trả về (bytes, filename, mimetype) nếu nén có lợi, ngược lại None."""
    if not data:
        return None
    img = _open(data)
    if img is None or img.format not in COMPRESSIBLE_FORMATS or getattr(img, 'is_animated', False):
        return None
    src_format = img.format
    img = ImageOps.exif_transpose(img)
    need_resize = max_px and (img.width > max_px or img.height > max_px)
    if not need_resize and len(data) <= SKIP_BELOW_BYTES:
        return None
    if need_resize:
        img.thumbnail((max_px, max_px), Image.LANCZOS)

    base, ext = os.path.splitext(filename or 'image')
    candidates = []
    if _uses_alpha(img):
        candidates.append((_encode(img.convert('RGBA'), 'PNG'), '.png', 'image/png'))
    else:
        rgb = img.convert('RGB')
        candidates.append((_encode(rgb, 'JPEG', quality=int(quality or 80)), '.jpg', 'image/jpeg'))
        if src_format == 'PNG':
            # ảnh đồ họa/ảnh chụp màn hình đôi khi PNG lại nhẹ hơn JPEG
            candidates.append((_encode(rgb, 'PNG'), '.png', 'image/png'))
    result, new_ext, mimetype = min(candidates, key=lambda c: len(c[0]))
    if len(result) >= len(data):  # không lợi gì -> giữ bản gốc
        return None
    if ext.lower() in ('.jpg', '.jpeg') and new_ext == '.jpg':
        new_ext = ext  # giữ đuôi gốc .jpeg/.JPG
    _logger.info('Argo documents: nén ảnh %s %s -> %s bytes (%s)', filename, len(data), len(result), src_format)
    return result, base + new_ext, mimetype


def make_thumbnail(data, size=320):
    """Thumbnail JPEG nhỏ (~15-30KB) để hiển thị lưới, None nếu không phải ảnh."""
    img = _open(data)
    if img is None:
        return None
    try:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((size, size), Image.LANCZOS)
        if _uses_alpha(img):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').getchannel('A'))
            img = bg
        out = io.BytesIO()
        img.convert('RGB').save(out, 'JPEG', quality=75, optimize=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        _logger.info('Argo documents: không tạo được thumbnail', exc_info=True)
        return None
