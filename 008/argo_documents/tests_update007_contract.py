"""Offline safety assertions for Update_007. Run `python tests_update007_contract.py`.

These tests do not replace Odoo ORM/record-rule integration tests on Staging.
"""
import ast
from pathlib import Path
import unittest
from lxml import etree

BASE = Path(__file__).resolve().parent
FOLDER = (BASE / 'models/folder.py').read_text()
DOC = (BASE / 'models/document.py').read_text()
POLICY = etree.parse(str(BASE / 'security/security.xml'))
MENU = (BASE / 'views/menus.xml').read_text()
EXPLORER = (BASE / 'static/src/explorer/explorer.js').read_text()
TEMPLATE = (BASE / 'static/src/explorer/explorer.xml').read_text()

class TestUpdate007Contract(unittest.TestCase):
    def test_xml_dom_and_python_syntax(self):
        ast.parse(FOLDER)
        ast.parse(DOC)
        for path in BASE.rglob('*.xml'):
            etree.parse(str(path))

    def test_lock_guard_at_every_destructive_path(self):
        root = ast.parse(FOLDER)
        cls = next(x for x in root.body if isinstance(x, ast.ClassDef) and x.name=='ArgoDocumentFolder')
        functions = {x.name: ast.unparse(x) for x in cls.body if isinstance(x, ast.FunctionDef)}
        self.assertIn("self._require_unlocked_subtree()", functions['unlink'])
        self.assertIn("self._require_unlocked_subtree()", functions['write'])
        self.assertIn("root_folder._require_unlocked_subtree()", functions['explorer_trash'])
        self.assertIn("folders._require_unlocked_subtree()", functions['explorer_delete_forever'])
        self.assertIn("_all_descendants().filtered('is_locked')", functions['_cron_purge_trash'])
        self.assertIn('self._check_manager()', functions['explorer_toggle_folder_lock'])
        self.assertIn('isinstance(locked, bool)', functions['explorer_toggle_folder_lock'])
        self.assertIn('is_locked', EXPLORER)
        self.assertIn('Lock Folder', TEMPLATE)
        self.assertIn('Unlock Folder', TEMPLATE)

    def test_crm_root_view_only_and_user_create(self):
        self.assertIn("parent.crm_shared_root", FOLDER)
        self.assertIn("parent._require_level('view')", FOLDER)
        self.assertIn('crm_shared_root', FOLDER)
        self.assertIn('crm_tree', FOLDER)
        self.assertIn("target._require_level('edit')", DOC)
        self.assertIn("dest._require_level('edit')", DOC)
        self.assertIn("folder.parent_id.crm_shared_root or folder.parent_id.crm_tree", FOLDER)

    def test_mst_and_shared_folder(self):
        self.assertIn("lead['x_yp_tax_code']", FOLDER)
        self.assertIn("'crm_lead_ids': [(4, lead.id)]", FOLDER)
        self.assertIn("('name', 'ilike', tax)", FOLDER)
        self.assertIn('matches_company_tax_folder(folder.name, tax)', FOLDER)
        self.assertIn("pg_advisory_xact_lock", FOLDER)
        self.assertIn("Admin cần cấp quyền Edit", FOLDER)
        self.assertIn("'lead_id': False", FOLDER)

    def test_internal_access_does_not_open_legacy_folders(self):
        rules = POLICY.xpath('//record[@model="ir.rule"]')
        r = [rec for rec in rules if (rec.get('id') or '').startswith('rule_argo_crm_internal_')]
        self.assertEqual(len(r), 6)
        for rec in r:
            domain = rec.xpath("./field[@name='domain_force']")[0].text
            self.assertTrue('crm_shared_root' in domain or 'crm_tree' in domain)
            self.assertTrue('effective_' in domain)
            self.assertIn("base.group_user", etree.tostring(rec, encoding='unicode'))
        self.assertIn('base.group_user', MENU)
        self.assertIn("folder.parent_id.crm_shared_root", FOLDER)

if __name__ == '__main__':
    unittest.main(verbosity=2)
