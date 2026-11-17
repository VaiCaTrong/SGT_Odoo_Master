"""Run: python tests_update009_contract.py. Offline only; Odoo staging test required."""
import ast
import importlib.util
from pathlib import Path
import unittest
from lxml import etree
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('crm_folder_naming', ROOT / 'models/crm_folder_naming.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class NamingTests(unittest.TestCase):
    def test_company_tax_name(self):
        self.assertEqual(mod.folder_name_for_company('Công ty TNHH Mạnh Toàn', ' 0200123456 '),
                         'Công ty TNHH Mạnh Toàn - 0200123456')

    def test_legacy_and_new_tax_matching(self):
        self.assertTrue(mod.matches_company_tax_folder('0200123456', '0200123456'))
        self.assertTrue(mod.matches_company_tax_folder('Mạnh Toàn - 0200123456', '0200123456'))
        self.assertFalse(mod.matches_company_tax_folder('Mạnh Toàn - 00200123456', '0200123456'))
        self.assertFalse(mod.matches_company_tax_folder('Mạnh Toàn - 02001234567', '0200123456'))
        self.assertFalse(mod.matches_company_tax_folder('Mạnh Toàn 0200123456', '0200123456'))

    def test_invalid_tax_and_company(self):
        for name, tax in [('', '0123456789'),('Công ty',''),('Công ty','02 00123456')]:
            with self.assertRaises(ValueError):
                mod.folder_name_for_company(name,tax)

    def test_sanitization_and_length(self):
        result = mod.folder_name_for_company(' Công ty A/B : C ', '0123456789')
        self.assertEqual(result, 'Công ty A_B _ C - 0123456789')
        result = mod.folder_name_for_company('Z'*320, '0123456789')
        self.assertEqual(len(result),255)
        self.assertTrue(result.endswith(' - 0123456789'))

    def test_folder_server_contract(self):
        source=(ROOT/'models/folder.py').read_text()
        ast.parse(source)
        self.assertIn('SELECT pg_advisory_xact_lock',source)
        self.assertIn('matches_company_tax_folder(folder.name, tax)',source)
        self.assertIn("'crm_lead_ids': [(4, lead.id)]",source)
        self.assertIn("'lead_id': lead.id",source)
        self.assertIn("'parent_id': root.id",source)
        self.assertIn('folder_name_for_company(company_name, tax)',source)
        self.assertIn('self._require_create_parent(root)',source)
        self.assertIn("self.browse(folder.id)._can_level('edit')",source)
        self.assertIn('old_link',source)

    def test_explorer_search_name(self):
        source=(ROOT/'models/folder.py').read_text()
        self.assertIn("('name', 'ilike', search)",source)
        xml=etree.parse(str(ROOT/'static/src/explorer/explorer.xml'))
        self.assertIn('Tìm tên công ty / MST',etree.tostring(xml,encoding='unicode'))

if __name__ == '__main__': unittest.main(verbosity=2)
