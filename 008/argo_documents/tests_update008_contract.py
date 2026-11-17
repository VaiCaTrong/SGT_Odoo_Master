"""Update_008: static security + root layout regression contracts.

These are NOT a substitute for Odoo 19 live ACL/ORM/UI integration tests.
"""
import ast
from pathlib import Path
import unittest
from lxml import etree

BASE = Path(__file__).resolve().parent
FOLDER = (BASE/'models/folder.py').read_text()
SEC = etree.parse(str(BASE/'security/security.xml'))
DATA = etree.parse(str(BASE/'data/config_data.xml'))
VIEW = etree.parse(str(BASE/'static/src/explorer/explorer.xml'))
JS = (BASE/'static/src/explorer/explorer.js').read_text()

class TestUpdate008(unittest.TestCase):
    def test_protected_crm_root_data(self):
        nodes=DATA.xpath('//record[@id="folder_crm_information_root"]')
        self.assertEqual(len(nodes),1)
        values={x.get('name'):(x.text or x.get('eval')) for x in nodes[0].findall('field')}
        self.assertEqual(values['name'],'CRM Information')
        for field in ('is_locked','system_root','crm_shared_root'):
            self.assertEqual(values[field],'True')
        self.assertEqual(values['public_level'],'view')
    def test_xml_id_routing_no_manual_settings(self):
        self.assertIn("env.ref('argo_documents.folder_crm_information_root'",FOLDER)
        self.assertIn('crm_root_folder_id', FOLDER)  # legacy config response only
        self.assertNotIn('argo_doc_crm_root_folder_id',(BASE/'models/res_config_settings.py').read_text())
        self.assertNotIn('argo_doc_crm_root_folder_id',(BASE/'views/res_config_settings_views.xml').read_text())
    def test_unremovable_root_even_by_admin(self):
        cls=next(n for n in ast.parse(FOLDER).body if isinstance(n, ast.ClassDef) and n.name=='ArgoDocumentFolder')
        funcs={f.name:ast.unparse(f) for f in cls.body if isinstance(f,ast.FunctionDef)}
        self.assertIn("subtree.filtered('system_root')",funcs['_require_unlocked_subtree'])
        self.assertIn("self.filtered('system_root')",funcs['write'])
        self.assertIn('self._require_unlocked_subtree()',funcs['unlink'])
        self.assertIn('folder.system_root',funcs['explorer_toggle_folder_lock'])
    def test_internal_defaults_without_group_cycle(self):
        user=SEC.xpath('//record[@id="group_argo_documents_user"]')[0]
        base=SEC.xpath('//record[@id="base.group_user"]')[0]
        u=' '.join((x.get('eval') or '') for x in user.xpath('./field[@name="implied_ids"]'))
        b=' '.join((x.get('eval') or '') for x in base.xpath('./field[@name="implied_ids"]'))
        self.assertIn("(3, ref('base.group_user'))",u)
        self.assertIn("(4, ref('argo_documents.group_argo_documents_user'))",b)
    def test_separate_virtual_and_real_roots(self):
        rendered=etree.tostring(VIEW,encoding='unicode')
        self.assertIn('Company Information',rendered)
        self.assertIn('CRM Information',rendered)
        self.assertIn('crmTreeRows',rendered)
        self.assertIn('_isInCrmTree',JS)
        self.assertIn('folders = folders.filtered(',FOLDER)
    def test_legacy_data_not_moved(self):
        mig=(BASE/'upgrades/19.0.1.8.0/post-10-configure-company-crm-root.py').read_text()
        self.assertIn('Do not clear crm_shared_root',mig)
        self.assertNotIn('unlink(',mig)
        self.assertNotIn("old.write",mig)

if __name__=='__main__':unittest.main(verbosity=2)
