"""Offline Update_042 Documents box integration smoke tests."""
import ast
from pathlib import Path
import unittest
from lxml import etree

BASE = Path(__file__).resolve().parents[1]
class TestCRM005Documents042(unittest.TestCase):
    def test_placement_and_one_widget(self):
        v=(BASE/'views/crm_yp_lead_form.xml').read_text()
        self.assertEqual(v.count('widget="sgt_crm005_documents"'),1)
        a,b,c = (v.index('name="sgt_crm005_partners_box"'),
                 v.index('name="crm005_documents_box"'),
                 v.index('name="sgt_crm005_evidence_box"'))
        self.assertTrue(a<b<c)
        etree.parse(str(BASE/'views/crm_yp_lead_form.xml'))
        etree.parse(str(BASE/'static/src/xml/documents_panel.xml'))

    def test_mst_not_user_chosen_and_api(self):
        widget=(BASE/'static/src/js/documents_panel.js').read_text()
        self.assertIn('"explorer_create_deal_folder", [this.leadId]',widget)
        self.assertNotIn('chooseFolder()',widget)
        self.assertNotIn('this.state.folderName',widget)
        view=(BASE/'static/src/xml/documents_panel.xml').read_text()
        self.assertIn('Create Folder',view)
        self.assertIn('Tên folder theo công ty và MST',view)
        self.assertIn('Kéo Catalog, ảnh hoặc file',view)
        self.assertIn('Open in Documents',view)
        self.assertIn('component: Crm005DocumentsPanel',widget)
        self.assertIn('supportedTypes: ["char"]',widget)

if __name__ == '__main__':
    unittest.main(verbosity=2)
