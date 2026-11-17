from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class TestUpdate043(unittest.TestCase):
    def test_documents_auto_root(self):
        xml=(ROOT/'static/src/xml/documents_panel.xml').read_text()
        js=(ROOT/'static/src/js/documents_panel.js').read_text()
        self.assertIn('CRM Information',xml)
        self.assertIn('explorer_create_deal_folder',js)
        self.assertIn('CRM Information · Documents',js)
        self.assertNotIn('Admin cần chọn thư mục gốc',xml)
    def test_field_and_view_preserved(self):
        view=(ROOT/'views/crm_yp_lead_form.xml').read_text()
        self.assertIn('sgt_crm005_documents',view)
        self.assertIn('x_yp_evidence_html',view)
        self.assertIn('x_group_image_binary',view)
if __name__=='__main__':unittest.main(verbosity=2)
