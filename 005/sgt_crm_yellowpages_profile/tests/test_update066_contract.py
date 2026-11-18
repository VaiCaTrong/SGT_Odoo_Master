"""Update_066 static contract: Image Gallery multi-select delete (developer mode only).

Run: python3 -I tests/test_update066_contract.py
The real-browser behaviour test (OWL 2 + Chromium) lives outside the addon: pg_gallery_select_test.py.
"""
import ast
import re
import unittest
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'static/src/js/gallery_manage.js').read_text()
XML = etree.parse(str(ROOT / 'static/src/xml/gallery_manage.xml'))
SCSS = (ROOT / 'static/src/scss/yellowpages_profile.scss').read_text()
PY = (ROOT / 'models/crm_lead.py').read_text()


class Contract(unittest.TestCase):
    def test_manifest(self):
        m = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(m['version'], '19.0.1.67.0')

    def test_no_new_field_or_view_change(self):
        # Image Gallery only: the field stays the same readonly custom widget, no new column
        view = etree.parse(str(ROOT / 'views/crm_yp_lead_form.xml'))
        f = view.xpath("//field[@name='x_yp_gallery_html']")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].get('widget'), 'sgt_gallery_manage')
        self.assertEqual(f[0].get('readonly'), '1')
        self.assertEqual(len(view.xpath("//field[@name='x_yp_partners_html' and @widget='html']")), 1)
        self.assertEqual(len(view.xpath("//field[@name='x_yp_evidence_html' and @widget='html']")), 1)
        # no field declared by this update: the 8 fields that existed in Update_065
        self.assertEqual(len(re.findall(r'^    \w+ = fields\.', PY, re.M)), 8)

    def test_select_only_in_debug(self):
        # the bar is gated by the same getter as the x button
        self.assertIn('return Boolean(user.isSystem) && this.canShowDelete && this.galleryMarkup && this._memo.total > 0;', JS)
        bar = XML.xpath('//section[@class="sgt_yp_select_bar"]')[0]
        self.assertEqual(bar.get('t-if'), 'canSelect')

    def test_bar_is_a_section_direct_child_of_root(self):
        root = XML.xpath('//div[@t-on-click="onGalleryClick"]')[0]
        self.assertEqual(root.get('class'), 'o_readonly sgt_yp_gallery_managed')
        self.assertEqual(root.get('t-ref'), 'root')
        self.assertIn(root.xpath('./section[@class="sgt_yp_select_bar"]')[0], list(root))
        # the gallery grid flattens p/div/span/a: none of those may carry the bar or its buttons
        self.assertEqual(XML.xpath('//section//div | //section//p | //section//span | //section//a'), [])

    def test_buttons_do_not_bubble_to_gallery_click(self):
        for b in XML.xpath('//section//button'):
            self.assertTrue(any(k.startswith('t-on-click.stop') for k in b.attrib), etree.tostring(b))

    def test_rpc_payload_and_confirmation(self):
        self.assertIn('"action_crm005_delete_gallery_images"', JS)
        self.assertIn('[this.props.record.resId], indexes, prefixes, total', JS)
        self.assertIn('this.dialog.add(SGTGalleryDeleteDialog', JS)
        self.assertIn('cannot be undone', (ROOT / 'static/src/js/gallery_delete_dialog.js').read_text())
        # nothing is sent outside the confirm callback
        before_confirm = JS.split('confirmDeleteSelected() {', 1)[1].split('confirm: async', 1)[0]
        self.assertNotIn('orm.call', before_confirm)

    def test_memo_is_mutated_not_reassigned_in_getter(self):
        # OWL runs template getters on a context that inherits from the component: reassigning
        # this._memo there creates a throw-away copy (found by the real-browser test).
        getter = JS.split('get galleryMarkup() {', 1)[1].split('// ---- Update_066', 1)[0]
        self.assertIn('Object.assign(this._memo,', getter)
        code = re.sub(r'//[^\n]*', '', getter)
        self.assertNotRegex(code, r'this\._memo\s*=[^=]')

    def test_single_delete_and_lightbox_kept(self):
        self.assertIn('"action_crm005_delete_gallery_image"', JS)
        self.assertIn('this.confirmDelete(button)', JS)
        self.assertIn('this.openViewer(event.currentTarget, image)', JS)
        # select mode returns before the lightbox is reached
        click = JS.split('onGalleryClick(event) {', 1)[1].split('confirmDelete(button) {', 1)[0]
        self.assertLess(click.index('this.state.select'), click.index('openViewer'))

    def test_css_matches_root_that_is_also_the_gallery_class(self):
        # the field root is BOTH .sgt_yp_gallery and .sgt_yp_select_mode: never require the former
        # as an ancestor of the latter
        self.assertNotIn('.sgt_yp_gallery .sgt_yp_select_mode', SCSS)
        for token in ('.sgt_yp_select_mode .sgt_yp_image_remove { display: none; }',
                      '.sgt_yp_select_mode .sgt_yp_image_pick {', 'sgt_yp_selected',
                      'grid-column: 1 / -1;'):
            self.assertIn(token, SCSS)

    def test_ui_limit_equals_server_limit(self):
        js = int(re.search(r'const BULK_DELETE_MAX = (\d+);', JS).group(1))
        py = int(re.search(r'GALLERY_BULK_DELETE_MAX = (\d+)', PY).group(1))
        self.assertEqual(js, py)

    def test_server_method_present_and_guarded(self):
        body = PY.split('def action_crm005_delete_gallery_images', 1)[1].split('def action_crm005_delete_gallery_image(', 1)[0]
        for token in ("check_access('write')", 'GALLERY_BULK_DELETE_MAX', 'len(set(indexes)) != len(indexes)',
                      'expected_count != len(images)', "[:128] != prefix"):
            self.assertIn(token, body)
        self.assertEqual(PY.count('_crm005_remove_gallery_node('), 3)  # def + single + bulk


if __name__ == '__main__':
    unittest.main()
