"""Offline view-only regression for CRM-005 Update_049."""
import ast
from pathlib import Path
import unittest
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]

class GeolocationCompactUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = etree.parse(str(ROOT / 'views/crm_yp_lead_form.xml'))
        cls.card = cls.doc.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' sgt_yp_geoloc_card ')]")[0]

    def test_only_two_coordinates_and_button_visible(self):
        lat = self.card.xpath(".//field[@name='x_yp_latitude']")
        lon = self.card.xpath(".//field[@name='x_yp_longitude']")
        status = self.card.xpath(".//field[@name='x_yp_geo_status' and @invisible='1']")
        self.assertEqual(len(lat), 1)
        self.assertEqual(len(lon), 1)
        self.assertEqual(len(status), 1)
        self.assertEqual(len(self.card.xpath('.//button')), 1)
        self.assertFalse(self.card.xpath(".//*[contains(@class,'sgt_yp_geoloc_help')]"))
        self.assertEqual(len(self.card.xpath(".//*[contains(@class,'sgt_yp_geoloc_header')]")), 0)
        self.assertEqual(len(self.card.xpath(".//*[contains(@class,'sgt_yp_geoloc_controls')]")), 1)
        self.assertFalse(self.card.xpath(".//*[contains(@class,'sgt_yp_geoloc_foot')]"))

    def test_english_button_and_functional_action(self):
        btn = self.card.xpath(".//button[@name='action_crm005_geolocate_now']")
        self.assertEqual(len(btn), 1)
        self.assertEqual(btn[0].get('type'), 'object')
        self.assertEqual(btn[0].get('string'), 'Get Coordinates')
        self.assertEqual(self.card.xpath(".//label[@string='Lat']")[0].get('for'), 'crm005_geo_lat')
        self.assertEqual(self.card.xpath(".//label[@string='Lon']")[0].get('for'), 'crm005_geo_lon')

    def test_cron_and_backend_unchanged(self):
        import zipfile
        original = Path('/mnt/data/sgt_crm_yellowpages_profile_CRM-005_V01_Update_059.zip')
        if original.exists():
            with zipfile.ZipFile(original) as src:
                for name in ('data/ir_cron_geo.xml', 'models/geo_lead.py'):
                    n = 'sgt_crm_yellowpages_profile/'+name
                    self.assertEqual(src.read(n), (ROOT/name).read_bytes())

    def test_manifest_version(self):
        manifest=ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(manifest['version'], '19.0.1.67.0')

if __name__ == '__main__':
    unittest.main()
