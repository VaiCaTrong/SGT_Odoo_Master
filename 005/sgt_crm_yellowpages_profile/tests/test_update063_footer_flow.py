"""Update_063: no-source cards promote quick links to the native footer line."""
import ast
import unittest
from pathlib import Path
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]

class NoSourceFooter(unittest.TestCase):
    def setUp(self):
        self.tree=etree.parse(str(ROOT/'views/crm_yp_lead_kanban.xml'))
        self.xpaths=self.tree.xpath('//record[@id="view_crm005_yellowpages_lead_kanban"]/field[@name="arch"]/xpath')
        self.css=(ROOT/'static/src/css/kanban_safe_links.css').read_text()

    def test_source_and_links_share_native_footer(self):
        self.assertEqual(len(self.xpaths),7)
        self.assertEqual([xp.get('position') for xp in self.xpaths[-3:]],['attributes','inside','inside'])
        self.assertEqual(len(self.xpaths[-2].xpath('./div[@class="sgt_crm005_safe_source"]')),1)
        self.assertEqual(len(self.xpaths[-1].xpath('./div[@class="sgt_crm005_safe_shortcuts"]')),1)
        self.assertEqual(len(self.tree.xpath('//xpath[@position="after" and contains(@expr, "footer")]')),0)

    def test_no_source_uses_left_slot_right_widgets_unchanged(self):
        self.assertIn('> .sgt_crm005_safe_source ~ .sgt_crm005_safe_shortcuts',self.css)
        self.assertIn('flex-wrap: wrap;',self.css)
        self.assertIn('margin-left: auto !important;',self.css)
        self.assertIn('flex: 1 1 0%;',self.css)
        self.assertIn('flex: 0 0 100%;',self.css)
        self.assertIn('order: 2;',self.css)

    def test_emtpy_links_collapse(self):
        self.assertIn(':not(:has(.sgt_crm005_safe_link[data-sgt-crm005-ready="1"], .sgt_crm005_safe_folder:not([hidden])))',self.css)
        self.assertIn('  display: none;',self.css)

    def test_native_behavior_fields_preserved(self):
        scan=etree.parse(str(ROOT/'tests/fixtures/odoo_scan_opportunity_base.xml'))
        self.assertEqual(len(scan.xpath('//footer//field[@name="user_id" and @widget="many2one_avatar_user"]')),1)
        self.assertEqual(len(scan.xpath('//footer//field[@name="rotting_days"]')),1)
        self.assertEqual(len(self.tree.xpath('//xpath[@position="replace" and contains(@expr,"footer")]')),1)
        self.assertIn('kanban_activity',self.xpaths[3].get('expr'))
        self.assertEqual(ast.literal_eval((ROOT/'__manifest__.py').read_text())['version'],'19.0.1.66.0')

if __name__=='__main__':unittest.main()
