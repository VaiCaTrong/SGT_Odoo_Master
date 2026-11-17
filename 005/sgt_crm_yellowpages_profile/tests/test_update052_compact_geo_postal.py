"""Update_052: small UI and invalid Vietnam ZIP removed from lookup query only."""
import ast
import sys
from pathlib import Path
import unittest
import types
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from test_update047_geolocation import GEO, FakeLead, UTIL
from test_update051_geolocation_feedback import FakeGeocoder

class Geo052(unittest.TestCase):
    def test_vietnam_zip_text_is_ignored_only_in_lookup(self):
        self.assertEqual(UTIL.geocoder_postal_code('TP Hồ Chí Minh', 'Vietnam'), '')
        self.assertEqual(UTIL.geocoder_postal_code('70000','Vietnam'),'70000')
        self.assertEqual(UTIL.geocoder_postal_code('700000','Việt Nam'),'700000')
        self.assertEqual(UTIL.geocoder_postal_code('SW1A 1AA','United Kingdom'),'SW1A 1AA')
    def test_geocoder_full_street_and_sanitized_zip(self):
        g=FakeGeocoder([(10.8,106.8)])
        lead=FakeLead(street='Lô G7, đường số 6, Khu công nghiệp Sóng Thần 2', street2='Phường Dĩ An', city='TP Hồ Chí Minh', zip='TP Hồ Chí Minh', state_id=types.SimpleNamespace(name='TP Hồ Chí Minh'), country_id=types.SimpleNamespace(name='Vietnam'))
        class Env:
            def __getitem__(self,key):
                self.key=key
                return g
        lead.env=Env()
        lead.with_context=lambda **kwargs:lead
        found=GEO.CrmLeadGeolocation._crm005_geo_lookup(lead)
        self.assertEqual(found,(10.8,106.8,'address'))
        self.assertEqual(g.queries[0]['zip'],'')
        self.assertEqual(g.queries[0]['street'],'Lô G7, đường số 6, Khu công nghiệp Sóng Thần 2, Phường Dĩ An')
        self.assertEqual(lead.zip,'TP Hồ Chí Minh')
    def test_no_match_returns_none_no_guessed_city_coords(self):
        g=FakeGeocoder([None,None])
        lead=FakeLead(zip='TP Hồ Chí Minh')
        class Env:
            def __getitem__(self,key):return g
        lead.env=Env()
        lead.with_context=lambda **kwargs:lead
        self.assertIsNone(GEO.CrmLeadGeolocation._crm005_geo_lookup(lead))
        self.assertTrue(any('123 Le Loi' in q for q,_ in g.calls))
    def test_small_box_without_help_or_status_text(self):
        tree=etree.parse(str(ROOT/'views/crm_yp_lead_form.xml'))
        boxes=tree.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' sgt_yp_geoloc_card ')]")
        self.assertEqual(len(boxes),1)
        box=boxes[0]
        self.assertEqual([x.get('string') for x in box.xpath('.//label')],['Lat','Lon'])
        self.assertEqual(len(box.xpath(".//button[@name='action_crm005_geolocate_now' and @string='Get Coordinates']")),1)
        self.assertFalse(box.xpath(".//*[contains(@class,'sgt_yp_geoloc_help')]"))
        scss=(ROOT/'static/src/scss/yellowpages_profile.scss').read_text('utf8')
        self.assertIn('width: fit-content;',scss)
        self.assertIn('border-radius: .5rem;',scss)
        self.assertIn('max-width: 100%;',scss)
        self.assertIn('background: #eaf3fb;',scss)
    def test_version_and_unchanged_contact_models(self):
        self.assertEqual(ast.literal_eval((ROOT/'__manifest__.py').read_text())['version'],'19.0.1.66.0')
        txt=(ROOT/'models/geo_lead.py').read_text()
        self.assertNotIn("self.env['res.partner'].create",txt)
        self.assertNotIn('res.partner.write',txt)
        self.assertIn("limit=5",txt)

if __name__=='__main__': unittest.main()
