"""Pure offline smoke tests for Gallery -> Documents (run with unittest)."""
import base64
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

SOURCE = Path(__file__).resolve().parents[1] / 'models/gallery_sync_utils.py'
spec = importlib.util.spec_from_file_location('gallery_sync_utils_under_test', SOURCE)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)


def image_bytes(fmt='PNG'):
    output = io.BytesIO()
    Image.new('RGB', (8, 8), 'white').save(output, format=fmt)
    return output.getvalue()


class TestUpdate044GallerySync(unittest.TestCase):
    def test_extract_only_gallery_images_in_order(self):
        html = '<div><figure><img src="data:image/png;base64,abc"/></figure><img src="https://example.org/2.jpg"/></div>'
        self.assertEqual(utils.gallery_sources(html), ['data:image/png;base64,abc', 'https://example.org/2.jpg'])

    def test_base64_png_and_mime_sniff(self):
        raw = image_bytes()
        result = utils.read_image_source('data:image/png;base64,' + base64.b64encode(raw).decode())
        self.assertEqual(result, (raw, 'png', 'image/png'))

    def test_jpeg_source_mime_not_taken_on_trust(self):
        raw = image_bytes('JPEG')
        self.assertEqual(utils.checked_image(raw)[1:], ('jpg', 'image/jpeg'))

    def test_html_rejected_as_image(self):
        with self.assertRaises(utils.GallerySyncError):
            utils.checked_image(b'<html>not a png</html>')

    def test_data_too_large(self):
        with self.assertRaises(utils.GallerySyncError):
            utils.decode_data_image('data:image/png;base64,' + 'A' * (utils.MAX_SINGLE_IMAGE_BYTES * 2))

    def test_attachment_path_and_query(self):
        self.assertEqual(utils.attachment_id_for_url('/web/image/ir.attachment/123/datas'), 123)
        self.assertEqual(utils.attachment_id_for_url('/web/image/456-abc/xyz.png'), 456)
        self.assertEqual(utils.attachment_id_for_url('/web/image?model=ir.attachment&id=789'), 789)
        self.assertIsNone(utils.attachment_id_for_url('/web/image?model=res.users&id=2'))
        self.assertIsNone(utils.attachment_id_for_url('https://other.example/web/image/123', 'my.example'))

    def test_prohibit_private_address(self):
        with self.assertRaises(utils.GallerySyncError):
            utils._public_host_address('localhost', 443)
        with patch.object(utils.socket, 'getaddrinfo', return_value=[
            (utils.socket.AF_INET, utils.socket.SOCK_STREAM, 0, '', ('127.0.0.1', 443))
        ]):
            with self.assertRaises(utils.GallerySyncError):
                utils._public_host_address('example.com', 443)

    def test_block_unsafe_urls_without_network(self):
        for url in ('file:///etc/passwd', 'http://127.0.0.1:1234/a', 'ftp://host/pic.jpg',
                    'https://user:password@example.com/a', 'http://metadata.google.internal/a'):
            with self.subTest(url=url), self.assertRaises(utils.GallerySyncError):
                utils.fetch_public_image(url)

    def test_local_attachment_source_reads_from_orm_callback(self):
        raw = image_bytes()
        called = []
        got = utils.read_image_source('/web/content/312', lambda n: (called.append(n), raw)[1])
        self.assertEqual(called, [312])
        self.assertEqual(got[1:], ('png', 'image/png'))


if __name__ == '__main__':
    unittest.main()
