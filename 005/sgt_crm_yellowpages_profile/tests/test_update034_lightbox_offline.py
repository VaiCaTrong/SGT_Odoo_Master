"""Static QA for Update_034 (does not replace live Odoo 19 testing)."""
import ast
from pathlib import Path
import unittest
from lxml import etree

MODULE = Path(__file__).resolve().parents[1]

class GalleryLightboxOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = ast.literal_eval((MODULE / '__manifest__.py').read_text())
        cls.js = (MODULE / 'static/src/js/gallery_manage.js').read_text()
        cls.scss = (MODULE / 'static/src/scss/yellowpages_profile.scss').read_text()
        cls.view = etree.parse(str(MODULE / 'views/crm_yp_lead_form.xml'))
        cls.widget = etree.parse(str(MODULE / 'static/src/xml/gallery_manage.xml'))

    def test_manifest_version_and_assets(self):
        self.assertGreaterEqual(tuple(map(int, self.manifest['version'].split('.'))), (19, 0, 1, 33, 0))
        assets = self.manifest['assets']['web.assets_backend']
        self.assertTrue(any(p.endswith('static/src/js/gallery_manage.js') for p in assets))
        self.assertTrue(any(p.endswith('static/src/scss/yellowpages_profile.scss') for p in assets))

    def test_widget_remains_readonly_and_in_place(self):
        fields = self.view.xpath("//field[@name='x_yp_gallery_html']")
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].get('widget'), 'sgt_gallery_manage')
        self.assertEqual(fields[0].get('readonly'), '1')

    def test_other_galleries_untouched(self):
        self.assertEqual(len(self.view.xpath("//field[@name='x_yp_partners_html' and @widget='html']")), 1)
        self.assertEqual(len(self.view.xpath("//field[@name='x_yp_evidence_html' and @widget='html']")), 1)

    def test_template_keeps_click_delegation(self):
        root = self.widget.getroot()
        self.assertEqual(root.xpath("//div[@t-on-click='onGalleryClick']")[0].get('class'),
                         'o_readonly sgt_yp_gallery_managed')

    def test_preview_requires_click_on_genuine_image(self):
        self.assertIn('target.closest("img")', self.js)
        self.assertIn('event.currentTarget.contains(image)', self.js)
        self.assertIn('event.preventDefault();', self.js)

    def test_delete_still_dev_only_and_server_enforced(self):
        self.assertIn('get canShowDelete()', self.js)
        self.assertIn('this.debugEnabled &&', self.js)
        self.assertIn('action_crm005_delete_gallery_image', self.js)
        self.assertIn('this.confirmDelete(button)', self.js)
        model = (MODULE / 'models/crm_lead.py').read_text()
        self.assertIn("self.check_access('write')", model)

    def test_viewer_has_navigation_zoom_and_close(self):
        for token in ('openViewer(', 'closeViewer()', 'changeViewerImage(', 'setViewerZoom(',
                      '"ArrowRight"', '"ArrowLeft"', '"Escape"',
                      'aria-modal', 'object-fit: contain', 'onWillUnmount'):
            self.assertTrue(token in self.js or token in self.scss, token)

    def test_preview_does_not_call_orm(self):
        preview = self.js.split('    openViewer(galleryRoot, selectedImage) {', 1)[1]
        self.assertNotIn('this.orm.call(', preview)
        self.assertNotIn('this.props.record.update(', preview)

    def test_viewer_does_not_inject_captions_as_html(self):
        self.assertIn('querySelector(".sgt_yp_lightbox_title").textContent = item.title;', self.js)
        self.assertIn('image.src = item.src;', self.js)

    def test_mobile_layout_and_fullscreen(self):
        for token in ('.sgt_yp_lightbox {', 'position: fixed;', 'height: 100dvh;',
                      '@media (max-width: 600px)', 'max-width: 100%;'):
            self.assertIn(token, self.scss)

if __name__ == '__main__':
    unittest.main()
