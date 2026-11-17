"""CRM-005: bounded, SSRF-safe image extraction for Gallery -> Documents.

No Odoo credentials are sent to remote hosts. External image hosts are resolved and
connected by a validated *public* IP, not re-resolved after validation.
"""
import base64
import binascii
import http.client
import io
import ipaddress
import re
import socket
import ssl
import unicodedata
from urllib.parse import parse_qs, urlsplit

from lxml import etree
from lxml import html as lxml_html
from PIL import Image, UnidentifiedImageError

MAX_SINGLE_IMAGE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 60_000_000
MAX_GALLERY_IMAGES = 500
FORMAT_MAP = {
    'JPEG': ('jpg', 'image/jpeg'), 'PNG': ('png', 'image/png'),
    'GIF': ('gif', 'image/gif'), 'WEBP': ('webp', 'image/webp'),
    'BMP': ('bmp', 'image/bmp'), 'TIFF': ('tif', 'image/tiff'),
    'ICO': ('ico', 'image/x-icon'),
}


class GallerySyncError(Exception):
    """Per-image failure which is safe to display to the employee."""


def gallery_entries(raw_html):
    """Return ordered ``(image_source, figcaption)`` pairs from Gallery HTML.

    The note belongs to its image only when the enclosing figure contains a
    single image. This prevents assigning one note to several different images.
    Uncaptioned/ambiguous images keep the legacy numbered filename.
    """
    if not raw_html:
        return []
    try:
        root = lxml_html.fragment_fromstring(raw_html, create_parent='div')
    except (TypeError, ValueError, etree.ParserError) as exc:
        raise GallerySyncError('HTML của Image Gallery không hợp lệ.') from exc
    images = root.xpath('.//img')
    if len(images) > MAX_GALLERY_IMAGES:
        raise GallerySyncError('Gallery có hơn 500 ảnh. Liên hệ Admin để đồng bộ theo lô.')
    entries = []
    for tag in images:
        src = (tag.get('src') or tag.get('data-src') or tag.get('data-original') or '').strip()
        caption = ''
        figures = tag.xpath('ancestor::figure[1]')
        if figures and len(figures[0].xpath('.//img')) == 1:
            captions = figures[0].xpath('.//figcaption')
            if captions:
                caption = ' '.join(''.join(captions[0].itertext()).split())
        entries.append((src, caption))
    return entries


def gallery_sources(raw_html):
    """Backward-compatible source-only extractor used by earlier releases."""
    return [src for src, _caption in gallery_entries(raw_html)]


def gallery_image_filename(caption, index, extension):
    """Build a safe, readable image filename from the note beneath its picture.

    Keeps Vietnamese accents, never treats note text as a path, and leaves
    collision resolution to Documents-008's existing ``_unique_name`` method.
    """
    base = unicodedata.normalize('NFC', str(caption or ''))
    # Control/format characters include bidi overrides and invisible separators.
    base = ''.join(ch for ch in base if unicodedata.category(ch) not in ('Cc', 'Cf'))
    base = re.sub(r'[\\/:*?"<>|]', ' ', base)
    base = re.sub(r'\s+', ' ', base).strip(' .')[:100].rstrip(' .')
    # Caption may itself end with a file extension; trust sniffed image bytes.
    base = re.sub(r'\.(?:jpe?g|png|gif|webp|bmp|tiff?|ico)$', '', base, flags=re.I).rstrip(' .')
    if base.upper() in {'CON', 'PRN', 'AUX', 'NUL'} or re.fullmatch(r'(COM|LPT)[1-9]', base.upper()):
        base = ''
    if not base:
        base = 'Image_Gallery_%03d' % index
    return '%s.%s' % (base, extension)


def checked_image(data):
    """Sniff actual bytes (never trust MIME or the URL extension)."""
    if not data or len(data) > MAX_SINGLE_IMAGE_BYTES:
        raise GallerySyncError('Ảnh rỗng hoặc vượt 12 MB; hãy tải riêng ảnh này.')
    try:
        with Image.open(io.BytesIO(data)) as photo:
            image_format = photo.format
            if not photo.width or not photo.height or photo.width * photo.height > MAX_IMAGE_PIXELS:
                raise GallerySyncError('Ảnh có kích thước pixel quá lớn.')
            photo.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise GallerySyncError('Nguồn không chứa ảnh hợp lệ.') from exc
    if image_format not in FORMAT_MAP:
        raise GallerySyncError('Định dạng ảnh này chưa được hỗ trợ để đồng bộ.')
    return data, *FORMAT_MAP[image_format]


def decode_data_image(src):
    head, sep, payload = src.partition(',')
    if not sep or ';base64' not in head.lower() or not head.lower().startswith('data:image/'):
        raise GallerySyncError('Data URL không phải ảnh Base64 hợp lệ.')
    payload = re.sub(r'\s+', '', payload)
    if len(payload) > MAX_SINGLE_IMAGE_BYTES * 4 // 3 + 4096:
        raise GallerySyncError('Ảnh Base64 vượt 12 MB.')
    try:
        return base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise GallerySyncError('Ảnh Base64 bị lỗi.') from exc


def attachment_id_for_url(src, base_host=''):
    """Recognize only local /web/image or /web/content attachment URLs.

    Unknown model-based endpoints are deliberately not dereferenced.
    """
    parsed = urlsplit(src)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in ('http', 'https') or not base_host or (parsed.hostname or '').lower() != base_host.lower():
            return None
    path = parsed.path
    match = re.match(r'^/web/(?:image|content)/(?:ir\.attachment/)?(\d+)(?:[-/]|$)', path)
    if match:
        return int(match.group(1))
    if path in ('/web/image', '/web/content'):
        params = parse_qs(parsed.query)
        if params.get('model', ['ir.attachment'])[0] == 'ir.attachment':
            id_text = params.get('id', [''])[0]
            if re.fullmatch(r'[1-9]\d*', id_text):
                return int(id_text)
    return None


def _public_host_address(host, port):
    try:
        host_ascii = host.encode('idna').decode('ascii')
    except (UnicodeError, AttributeError) as exc:
        raise GallerySyncError('Tên miền ảnh không hợp lệ.') from exc
    if not host_ascii or len(host_ascii) > 253 or host_ascii.endswith('.') or not re.fullmatch(r'[A-Za-z0-9.-]+', host_ascii):
        raise GallerySyncError('Tên miền ảnh không hợp lệ.')
    if '.' not in host_ascii or host_ascii.lower().endswith(('.local', '.internal', '.localhost', '.test')):
        raise GallerySyncError('Địa chỉ ảnh nội bộ bị chặn.')
    try:
        records = socket.getaddrinfo(host_ascii, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise GallerySyncError('Không phân giải được tên miền ảnh.') from exc
    ips = []
    for record in records:
        ip_text = record[4][0]
        ip = ipaddress.ip_address(ip_text)
        if not ip.is_global:
            raise GallerySyncError('Nguồn ảnh có địa chỉ IP nội bộ hoặc bị hạn chế.')
        ips.append(ip_text)
    if not ips:
        raise GallerySyncError('Không có địa chỉ IP công khai cho ảnh.')
    return host_ascii, ips[0]


def fetch_public_image(src):
    """Download an image without redirects/proxies, pinned to checked public IP.

    Only HTTP(S) standard ports, no credentials, bounded size, TLS hostname
    verification on HTTPS. Do not follow redirects (SSRF defense).
    """
    parsed = urlsplit(src)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or not parsed.hostname:
        raise GallerySyncError('Chỉ hỗ trợ đường dẫn ảnh HTTP/HTTPS công khai.')
    try:
        if parsed.port not in (None, 80 if parsed.scheme == 'http' else 443):
            raise GallerySyncError('Không cho phép cổng mạng tùy chỉnh.')
    except ValueError as exc:
        raise GallerySyncError('Cổng mạng không hợp lệ.') from exc
    port = 443 if parsed.scheme == 'https' else 80
    host, ip = _public_host_address(parsed.hostname, port)
    path = parsed.path or '/'
    if parsed.query:
        path += '?' + parsed.query
    sock = None
    conn = None
    try:
        sock = socket.create_connection((ip, port), timeout=4)
        sock.settimeout(10)
        if parsed.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.sock = sock
        headers = {
            'Host': host,
            'Accept': 'image/png,image/jpeg,image/webp,image/gif,image/bmp,image/tiff,image/x-icon',
            'Accept-Encoding': 'identity',
            'User-Agent': 'XinyangGallerySync/1.0',
        }
        conn.request('GET', path, headers=headers)
        reply = conn.getresponse()
        if reply.status != 200:
            raise GallerySyncError('Nguồn ảnh không truy cập được (HTTP %s).' % reply.status)
        mime = (reply.getheader('Content-Type') or '').split(';', 1)[0].strip().lower()
        if mime not in ('application/octet-stream', '') and not mime.startswith('image/'):
            raise GallerySyncError('Đường dẫn không trả về dữ liệu ảnh.')
        length = reply.getheader('Content-Length') or ''
        if length.isdigit() and int(length) > MAX_SINGLE_IMAGE_BYTES:
            raise GallerySyncError('Ảnh trên máy chủ vượt 12 MB.')
        data = reply.read(MAX_SINGLE_IMAGE_BYTES + 1)
        return data
    except GallerySyncError:
        raise
    except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException) as exc:
        raise GallerySyncError('Không thể tải ảnh từ máy chủ nguồn.') from exc
    finally:
        if conn:
            conn.close()
        elif sock:
            sock.close()


def read_image_source(src, attachment_reader=None, base_host=''):
    if not src:
        raise GallerySyncError('Thẻ ảnh chưa có đường dẫn.')
    if src.lower().startswith('data:'):
        data = decode_data_image(src)
    else:
        if src.startswith('//'):
            src = 'https:' + src
        attachment_id = attachment_id_for_url(src, base_host)
        if attachment_id is not None:
            if not attachment_reader:
                raise GallerySyncError('Không hỗ trợ đọc attachment Odoo.')
            data = attachment_reader(attachment_id)
        else:
            parsed = urlsplit(src)
            if not parsed.scheme and not parsed.netloc:
                raise GallerySyncError('Đường dẫn ảnh Odoo này chưa được hỗ trợ.')
            data = fetch_public_image(src)
    return checked_image(data)
