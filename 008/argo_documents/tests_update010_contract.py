"""Run: python3 -I tests_update010_contract.py — static contract of Documents-008 Update_010."""
import re
import subprocess
import unittest
from pathlib import Path
from lxml import etree

BASE = Path(__file__).resolve().parent
EXP = BASE / 'static/src/explorer'


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.xml = etree.parse(str(EXP / 'explorer.xml'))
        cls.folder = (BASE / 'models/folder.py').read_text()
        cls.js = (EXP / 'explorer.js').read_text()

    def test_version(self):
        self.assertIn("'version': '19.0.1.10.0'", (BASE / '__manifest__.py').read_text())

    def test_no_new_fields_no_migration(self):
        self.assertFalse(list((BASE / 'upgrades').glob('19.0.1.10*')))
        # same number of field declarations as the Update_009 base kept next to the sources
        base = Path(__file__).resolve().parent.parent / 'BASE_U009_folder.py'
        if base.exists():
            self.assertEqual(self.folder.count('fields.'), base.read_text().count('fields.'))

    def test_server_methods_are_read_or_delegated_only(self):
        start = self.folder.index('def _crm_link_folder')
        end = self.folder.index('def explorer_config')
        block = self.folder[start:end]
        self.assertNotIn('.create(', block)
        self.assertNotIn('.unlink(', block)
        self.assertNotIn('sudo().write', block)
        self.assertNotIn('execute(', block)
        # sudo only to find links / read parent_path, never to write
        self.assertIn("hasattr(Lead, 'crm005_push_documents_to_gallery')", block)
        self.assertIn("'crm_push_available': hasattr(self.env['crm.lead'], 'crm005_push_documents_to_gallery')", self.folder)

    def test_tree_menu_only_on_crm_branch(self):
        nodes = self.xml.xpath('//div[@t-on-contextmenu="(ev) => this.openTreeMenu(ev, node)"]')
        self.assertEqual(len(nodes), 1)
        loop = nodes[0].getparent()
        self.assertEqual(loop.get('t-foreach'), 'crmTreeRows')
        company_rows = self.xml.xpath('//t[@t-foreach="treeRows"]//div[@t-on-contextmenu]')
        self.assertEqual(company_rows, [])  # Company Information tree unchanged

    def test_menu_dispatch_and_templates(self):
        self.assertEqual(len(self.xml.xpath('//t[@t-name="argo_documents.TreeMenu"]')), 1)
        self.assertEqual(len(self.xml.xpath('//t[@t-name="argo_documents.CrmTargetDialog"]')), 1)
        self.assertEqual(len(self.xml.xpath('//t[@t-elif="state.menu.type === \'tree\'"]/t[@t-call="argo_documents.TreeMenu"]')), 1)
        item_menu = self.xml.xpath('//t[@t-name="argo_documents.ItemMenu"]')[0]
        self.assertEqual(len(item_menu.xpath('.//div[contains(@class,"o_gx_menu_crm")]')), 1)
        tree_menu = self.xml.xpath('//t[@t-name="argo_documents.TreeMenu"]')[0]
        self.assertEqual(len(tree_menu.xpath('.//div[contains(@class,"o_gx_menu_crm")]')), 1)

    def test_details_panel_has_three_buttons(self):
        aside = self.xml.xpath('//aside[contains(@class,"o_gx_details")]')[0]
        buttons = aside.xpath('.//button[contains(@class,"o_gx_push_crm")]')
        self.assertEqual(len(buttons), 3)  # single item / multi selection / current folder
        for b in buttons:
            self.assertEqual(b.get('t-on-click'), '() => this.pushFromInfo()')

    def test_dialog_registered_and_imported(self):
        self.assertIn('ArgoCrmTargetDialog', self.js.split('from "./dialogs"')[0])
        self.assertIn('export class ArgoCrmTargetDialog', (EXP / 'dialogs.js').read_text())
        self.assertIn('o_gx_menu_crm', (EXP / 'explorer.scss').read_text())

    def test_buttons_only_visible_when_feature_available(self):
        self.assertIn('crm_push_available', self.js)
        self.assertIn('get treePushAvailable', self.js)

    def test_existing_menus_untouched(self):
        for needle in ('Tải xuống (.zip)', 'Thay bằng file mới', 'Lock Folder', 'Quyền xem…', 'Dọn sạch thùng rác'):
            self.assertIn(needle, (EXP / 'explorer.xml').read_text())


class RunOthers(unittest.TestCase):
    def test_service_and_js(self):
        r = subprocess.run(['python3', '-I', str(BASE / 'tests_update010_service_mock.py')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        r = subprocess.run(['node', str(BASE / 'tests_update010_js.cjs')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])


if __name__ == '__main__':
    unittest.main(verbosity=1)
