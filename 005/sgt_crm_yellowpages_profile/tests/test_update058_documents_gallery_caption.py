"""CRM-005 Update_058: collapsed Documents file list and Gallery caption filenames.

Runs without Odoo server; service integration remains a staging smoke test.
"""
import ast
import importlib.util
from pathlib import Path
import re
import unittest

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('crm005_gallery_utils058', ROOT / 'models/gallery_sync_utils.py')
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)


class TestGalleryNotes(unittest.TestCase):
    def test_caption_is_associated_with_exact_image(self):
        html = ('<div>'
                '<figure><a href="/p"><img src="/web/image/1"/></a>'
                '<figcaption>Thiết bị <b>làm lạnh</b> công nghiệp</figcaption></figure>'
                '<figure><img src="/web/image/2"/><figcaption>Kho lạnh 5°C</figcaption></figure>'
                '<img src="/web/image/3"/>'
                '</div>')
        self.assertEqual(utils.gallery_entries(html), [
            ('/web/image/1', 'Thiết bị làm lạnh công nghiệp'),
            ('/web/image/2', 'Kho lạnh 5°C'),
            ('/web/image/3', ''),
        ])
        self.assertEqual(utils.gallery_sources(html), ['/web/image/1', '/web/image/2', '/web/image/3'])

    def test_no_cross_image_caption_leakage(self):
        html = '<figure><img src="a"/><img src="b"/><figcaption>Chung</figcaption></figure>'
        self.assertEqual(utils.gallery_entries(html), [('a', ''), ('b', '')])

    def test_filename_uses_caption_and_keeps_vietnamese(self):
        self.assertEqual(utils.gallery_image_filename('Hệ thống điều khiển nhiệt độ', 1, 'jpg'),
                         'Hệ thống điều khiển nhiệt độ.jpg')
        self.assertEqual(utils.gallery_image_filename('  Kho lạnh < 0°C / KCN Sóng Thần  ', 4, 'png'),
                         'Kho lạnh 0°C KCN Sóng Thần.png')
        self.assertEqual(utils.gallery_image_filename('Kho lạnh.jpg', 7, 'png'), 'Kho lạnh.png')
        self.assertEqual(utils.gallery_image_filename('<script>alert(1)</script>', 7, 'gif'),
                         'script alert(1) script.gif')

    def test_blank_unsafe_and_too_long_caption(self):
        for caption in ('', '  ', '/ \\ : * ?', 'CON', 'LPT4', '\u202e\x00'):
            self.assertEqual(utils.gallery_image_filename(caption, 4, 'webp'),
                             'Image_Gallery_004.webp')
        long_name = utils.gallery_image_filename('Thiết bị ' * 200, 8, 'jpg')
        self.assertLessEqual(len(long_name[:-4]), 100)
        self.assertTrue(long_name.endswith('.jpg'))
        self.assertNotIn('/', long_name)

    def test_source_cap_is_preserved(self):
        html = '<div>' + '<img src="a"/>' * 501 + '</div>'
        with self.assertRaises(utils.GallerySyncError):
            utils.gallery_entries(html)


class TestDocumentsInterface(unittest.TestCase):
    def test_file_list_is_collapsed_natively(self):
        xml = ROOT / 'static/src/xml/documents_panel.xml'
        tree = etree.parse(str(xml))
        node = tree.xpath('//details[@class="sgt_crm005_docs_files"]')
        self.assertEqual(len(node), 1)
        self.assertNotIn('open', node[0].attrib)
        summary = node[0].xpath('./summary')
        self.assertEqual(len(summary), 1)
        self.assertTrue(node[0].xpath('.//*[@t-foreach="state.files"]'))
        self.assertTrue(node[0].xpath('.//a[@t-att-href="fileHref(file)"]'))
        self.assertIn('t-esc="state.files.length"', xml.read_text())

    def test_gallery_sync_respects_existing_duplicate_and_uniqueness(self):
        code = (ROOT / 'models/gallery_sync.py').read_text()
        self.assertIn("('checksum', '=', digest)", code)
        self.assertIn("Folder._unique_name(folder, vals['name'], 'file')", code)
        self.assertIn('gallery_image_filename(caption, i + 1, extension)', code)
        self.assertIn('image_source, caption = sources[i]', code)
        self.assertNotIn('self.write(', code)

    def test_only_one_addon_version_bump(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(manifest['version'], '19.0.1.67.0')
        self.assertIn('argo_documents', manifest['depends'])


if __name__ == '__main__':
    unittest.main()
