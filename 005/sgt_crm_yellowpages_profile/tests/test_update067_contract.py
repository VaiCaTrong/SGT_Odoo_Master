"""Update_067 static contract: Image Gallery bulk delete is Administrator-only; delete confirmation box with thumbnails.

Run: python3 -I tests/test_update067_contract.py
Real-browser behaviour: pg_gallery_select_test.py (outside the addon).
"""
import ast
import re
import unittest
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'static/src/js/gallery_manage.js').read_text()
DLG = (ROOT / 'static/src/js/gallery_delete_dialog.js').read_text()
DXML = etree.parse(str(ROOT / 'static/src/xml/gallery_delete_dialog.xml'))
SCSS = (ROOT / 'static/src/scss/yellowpages_profile.scss').read_text()
PY = (ROOT / 'models/crm_lead.py').read_text()
MANIFEST = ast.literal_eval((ROOT / '__manifest__.py').read_text())


class AdminOnly(unittest.TestCase):
    def test_server_checks_system_group_in_bulk_only(self):
        bulk = PY.split('def action_crm005_delete_gallery_images', 1)[1].split('def action_crm005_delete_gallery_image(', 1)[0]
        self.assertIn('self.env.is_system()', bulk)
        self.assertIn('AccessError', bulk)
        single = PY.split('def action_crm005_delete_gallery_image(', 1)[1].split('# Update_060', 1)[0]
        self.assertNotIn('is_system', single)   # decision 14/11 22:5x: the x button stays as it is
        # the Administrator check comes right after the write-access check, before any parsing
        self.assertLess(bulk.index("check_access('write')"), bulk.index('is_system()'))
        self.assertLess(bulk.index('is_system()'), bulk.index('lxml_html.fragment_fromstring'))

    def test_access_error_imported(self):
        self.assertRegex(PY, r'from odoo\.exceptions import [^\n]*AccessError')

    def test_ui_gate_uses_system_not_erp_manager(self):
        # JS user.isAdmin is "Access Rights"; user.isSystem is "Settings" (= env.is_system on the server)
        self.assertIn('user.isSystem', JS)
        self.assertNotIn('user.isAdmin', JS)
        self.assertIn('import { user } from "@web/core/user";', JS)

    def test_single_x_button_not_gated_by_admin(self):
        self.assertIn('return this.debugEnabled && Boolean(this.props.record.resId) && !this.props.record.isNew;', JS)


class DeleteDialog(unittest.TestCase):
    def test_both_delete_paths_use_the_new_box(self):
        self.assertEqual(JS.count('this.dialog.add(SGTGalleryDeleteDialog'), 2)
        self.assertNotIn('ConfirmationDialog', JS)

    def test_rpc_names_unchanged(self):
        self.assertIn('"action_crm005_delete_gallery_image",', JS)
        self.assertIn('"action_crm005_delete_gallery_images",', JS)

    def test_nothing_sent_by_the_dialog_itself(self):
        self.assertNotIn('orm', DLG)
        self.assertNotIn('rpc', DLG.lower().replace('protected rpc', ''))
        self.assertIn('await this.props.confirm();', DLG)

    def test_manifest_assets_and_version(self):
        a = MANIFEST['assets']['web.assets_backend']
        self.assertIn('sgt_crm_yellowpages_profile/static/src/js/gallery_delete_dialog.js', a)
        self.assertIn('sgt_crm_yellowpages_profile/static/src/xml/gallery_delete_dialog.xml', a)
        self.assertEqual(MANIFEST['version'], '19.0.1.66.0')

    def test_template_name_matches_component(self):
        name = DXML.getroot()[0].get('t-name')
        self.assertEqual(name, 'sgt_crm_yellowpages_profile.GalleryDeleteDialog')
        self.assertIn('"%s"' % name, DLG)

    def test_dialog_has_danger_confirm_and_cancel_and_thumbs(self):
        self.assertEqual(len(DXML.xpath('//button[contains(@class,"btn-danger")][@t-on-click="onConfirm"]')), 1)
        self.assertEqual(len(DXML.xpath('//button[contains(@class,"sgt_yp_del_cancel")][@t-on-click="onCancel"]')), 1)
        self.assertEqual(len(DXML.xpath('//img[@t-foreach="props.thumbs"]')), 1)
        # both footer buttons are disabled while the request runs (no double click)
        self.assertEqual(len(DXML.xpath('//button[@t-att-disabled="state.busy"]')), 2)

    def test_thumb_cap_and_extra_counter(self):
        self.assertIn('DELETE_DIALOG_MAX_THUMBS = 24', DLG)
        self.assertIn('props.count - this.props.thumbs.length', DLG)

    def test_warns_when_everything_is_deleted(self):
        self.assertIn('get deletesAll()', DLG)
        self.assertEqual(len(DXML.xpath('//p[@t-if="deletesAll"]')), 1)

    def test_dialog_css_not_scoped_to_form(self):
        # the dialog is rendered under <body>, outside .o_form_view
        for sel in ('.sgt_yp_del_thumbs {', '.sgt_yp_del_thumbs .sgt_yp_del_thumb {', '.sgt_yp_del_all {'):
            self.assertIn('\n' + sel, SCSS)
        css = re.sub(r'/\*.*?\*/', '', SCSS, flags=re.S)
        self.assertIsNone(re.search(r'\.o_form_view[^{]*\.sgt_yp_del_', css))


if __name__ == '__main__':
    unittest.main()
