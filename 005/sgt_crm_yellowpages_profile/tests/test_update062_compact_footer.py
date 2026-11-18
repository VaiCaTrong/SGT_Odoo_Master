"""Update_062: Odoo 19 CRM Kanban compact footer regression tests."""
import ast
import hashlib
import unittest
from pathlib import Path
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
XML=ROOT/'views/crm_yp_lead_kanban.xml'
CSS=ROOT/'static/src/css/kanban_safe_links.css'
SCAN=ROOT/'tests/fixtures/odoo_scan_opportunity_base.xml'

class TestCompactFooter(unittest.TestCase):
    def setUp(self):
        self.tree=etree.parse(str(XML))
        self.specs=self.tree.xpath('//record[@id="view_crm005_yellowpages_lead_kanban"]/field[@name="arch"]/xpath')

    def test_only_stable_footer_xpaths_added(self):
        self.assertEqual(len(self.specs),7)
        last=self.specs[4:]
        self.assertEqual([x.get('position') for x in last],['attributes','inside','inside'])
        self.assertTrue(all(x.get('expr')=="//kanban/templates/t[@t-name='card']/footer" for x in last))

    def test_source_inside_native_footer(self):
        ins=self.specs[5]
        self.assertEqual(len(ins.xpath('./div[@class="sgt_crm005_safe_source"]/field[@name="source_id"]')),1)
        self.assertEqual(len(ins.xpath('.//field[@name="user_id"]')),0)

    def test_shortcuts_inside_footer_but_without_source(self):
        a=self.specs[6]
        self.assertEqual(len(a.xpath('./div[@class="sgt_crm005_safe_shortcuts"]/div[@class="sgt_crm005_safe_links"]')),1)
        self.assertEqual(len(a.xpath('.//field[@name="source_id"]')),0)
        self.assertEqual(len(a.xpath('.//a[@data-sgt-crm005-kind]')),4)
        self.assertEqual(len(a.xpath('.//button[@name="action_crm005_kanban_open_folder"]')),1)

    def test_palette_and_avatar_inherited_unchanged(self):
        scan=etree.parse(str(SCAN))
        self.assertEqual(len(scan.xpath('//field[@widget="kanban_color_picker"]')),1)
        self.assertEqual(len(scan.xpath('//footer//field[@name="user_id" and @widget="many2one_avatar_user"]')),1)
        self.assertEqual(len(self.tree.xpath('//xpath[@position="replace" and contains(@expr,"footer")]')),1)
        self.assertIn("kanban_activity",self.specs[3].get('expr'))

    def test_css_left_right_alignment_and_spacing(self):
        css=CSS.read_text()
        self.assertIn('footer.sgt_crm005_compact_footer',css)
        self.assertIn('order: -1;',css)
        self.assertIn('margin-left: auto !important;',css)
        self.assertIn('justify-content: flex-start;',css)
        self.assertIn('margin: 3px 0 0 !important;',css)
        self.assertNotIn('justify-content: space-between;',css)

    def test_new_and_drag_and_website_facebook(self):
        a={x.get('name'):x.text for x in self.specs[0].xpath('./attribute')}
        self.assertEqual(a['create'],'true')
        self.assertEqual(a['records_draggable'],'true')
        self.assertEqual(a['group_delete'],'false')
        s=etree.tostring(self.tree,encoding='unicode')
        self.assertIn('x_url_zalo_group',s)
        self.assertIn('x_link_fanpage',s)

    def test_no_python_js_changes_from_update061(self):
        # Stable hashes; models/crm_lead.py re-pinned by Update_066 and Update_067 (bulk delete added: tests/test_update066_bulk_delete.py covers it).
        original_hashes = {'models/crm_lead.py': '4c5122c07800518f56154a84b873540a84e3d09fbd4037d1e0de82af1c3c3333', 'models/geo_lead.py': '66d92c1b758f7893f1361caf524e36668803447810a4bc0c643547a5424f9bd5', 'static/src/js/kanban_shortcuts_safe.js': '97c6cf209745ebef0cb0feb6ee35939ef3df00830cf46e1462e495f3e2ce2987', 'static/src/js/kanban_deal_new_tab.js': '9bdc331ebbcec8c33e88dfc1d146bc8a1ca146aff3e942d619d60b3e8059a215'}
        for path, expected in original_hashes.items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)

    def test_manifest(self):
        manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text())
        self.assertEqual(manifest['version'],'19.0.1.67.0')
        self.assertIn('base_geolocalize',manifest['depends'])

if __name__=='__main__':unittest.main()
