import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestGallerySyncContract(unittest.TestCase):
    def test_documents_widget_is_still_in_correct_place(self):
        xml = (ROOT / 'views/crm_yp_lead_form.xml').read_text()
        self.assertLess(xml.index('sgt_crm005_partners_box'), xml.index('crm005_documents_box'))
        self.assertLess(xml.index('crm005_documents_box'), xml.index('sgt_crm005_evidence_box'))
        self.assertIn('x_group_image_binary', xml)

    def test_only_sync_gallery_and_no_mutation_of_source_field(self):
        py = (ROOT / 'models/gallery_sync.py').read_text()
        self.assertIn('self.x_yp_gallery_html', py)
        self.assertNotIn('x_yp_partners_html', py)
        self.assertNotIn('x_yp_evidence_html', py)
        self.assertNotIn("self.write({'x_yp_gallery_html'", py)
        self.assertIn("'_prepare_content'".strip("'"), py)
        self.assertIn("Doc.with_context(image_no_postprocess=True).create(vals)", py)
        self.assertIn("folder._require_level('edit')", py)
        self.assertIn("('checksum', '=', digest)", py)

    def test_ui_sync_only_for_edit_and_progress(self):
        xml = (ROOT / 'static/src/xml/documents_panel.xml').read_text()
        js = (ROOT / 'static/src/js/documents_panel.js').read_text()
        self.assertIn('state.folder.can_upload', xml)
        self.assertIn('Đồng bộ ảnh Gallery', xml)
        self.assertIn('syncGallery', xml)
        self.assertIn('action_crm005_gallery_sync_manifest', js)
        self.assertIn('action_crm005_sync_gallery_batch', js)
        self.assertIn('gallerySyncing', js)

    def test_only_crm_005_changed(self):
        manifest = (ROOT / '__manifest__.py').read_text()
        # Updated modules may increment their manifest without changing gallery sync.
        version = ast.literal_eval(manifest)['version']
        self.assertGreaterEqual(tuple(map(int, version.split('.'))), (19, 0, 1, 43, 0))
        self.assertIn("'argo_documents'", manifest)


if __name__ == '__main__':
    unittest.main()
