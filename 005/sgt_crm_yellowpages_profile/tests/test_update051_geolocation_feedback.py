"""Update_051 offline behavior regression; no live provider or Odoo DB."""
import ast
import sys
from pathlib import Path
import types
import unittest
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from test_update047_geolocation import GEO, FakeLead, UTIL

class FakeGeocoder:
    def __init__(self, results):
        self.results=list(results)
        self.queries=[]
        self.calls=[]
    def sudo(self): return self
    def geo_query_address(self, **kw):
        self.queries.append(kw)
        return '|'.join(str(kw.get(k) or '') for k in ('street','zip','city','state','country'))
    def geo_find(self, query, **kwargs):
        self.calls.append((query,kwargs))
        return self.results.pop(0) if self.results else None

class GeoUI051(unittest.TestCase):
    def test_success_reloads_and_updates_values(self):
        lead=FakeLead(lookup_result=(10.909,106.711))
        res=lead.action_crm005_geolocate_now()
        self.assertEqual(res, {'type':'ir.actions.client','tag':'reload'})
        self.assertEqual((lead.x_yp_latitude,lead.x_yp_longitude),(10.909,106.711))
    def test_failed_request_shows_persistent_warning_without_auto_reload(self):
        lead=FakeLead(lookup_result=None)
        res=lead.action_crm005_geolocate_now()
        self.assertEqual(res['tag'],'display_notification')
        self.assertTrue(res['params']['sticky'])
        self.assertNotIn('next',res['params'])
        self.assertEqual((lead.x_yp_latitude,lead.x_yp_longitude),(0,0))
        self.assertEqual(lead.x_yp_geo_status,'failed')
    def test_backend_error_is_distinguishable(self):
        lead=FakeLead()
        def crash(): raise RuntimeError('provider failure')
        lead._crm005_geo_lookup=crash
        res=lead.action_crm005_geolocate_now()
        self.assertEqual(res['params']['type'],'danger')
        self.assertTrue(res['params']['sticky'])
        self.assertEqual(lead.x_yp_geo_status,'failed')
    def test_existing_manual_coords_preserved(self):
        lead=FakeLead(x_yp_latitude=10.88,x_yp_longitude=106.78,x_yp_geo_status='manual',lookup_result=None)
        with self.assertRaises(Exception):
            lead.action_crm005_geolocate_now()
        self.assertEqual((lead.x_yp_latitude,lead.x_yp_longitude),(10.88,106.78))
        self.assertEqual(lead.x_yp_geo_status,'manual')
    def test_lookup_retries_once_with_street_never_city_only(self):
        g=FakeGeocoder([None,(10.7,106.8)])
        lead=FakeLead(street='Lô G7 đường số 6 KCN Sóng Thần 2',street2='Phường Dĩ An',
                      city='TP Hồ Chí Minh', state_id=types.SimpleNamespace(name='TP Hồ Chí Minh'),
                      country_id=types.SimpleNamespace(name='Vietnam'))
        lead.env=types.SimpleNamespace(context={},__getitem__=lambda x: None)
        class Env:
            def __getitem__(self,key):
                assert key=='base.geocoder'
                return g
        lead.env=Env()
        # Stub with_context, because real Odoo model supplies this.
        lead.with_context=lambda **kwargs:lead
        got=GEO.CrmLeadGeolocation._crm005_geo_lookup(lead)
        self.assertEqual(got,(10.7,106.8,'address'))
        self.assertEqual(len(g.calls),2)
        self.assertTrue(all('Lô G7' in call[0] for call in g.calls))
        self.assertTrue(all('Vietnam' in call[0] for call in g.calls))
        self.assertFalse(g.queries[1].get('city'))
    def test_no_fallback_to_city_center(self):
        g=FakeGeocoder([None,None])
        lead=FakeLead(street='123 Address',city='City Name',country_id=types.SimpleNamespace(name='Vietnam'))
        class Env:
            def __getitem__(self,key):return g
        lead.env=Env()
        lead.with_context=lambda **kwargs:lead
        self.assertIsNone(GEO.CrmLeadGeolocation._crm005_geo_lookup(lead))
        self.assertGreaterEqual(len(g.calls), 2)
        self.assertIn('123 Address', g.calls[0][0])
        self.assertTrue(any('City Name' in q for q,_ in g.calls[1:]))
    def test_manifest_and_layout(self):
        manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text('utf8'))
        self.assertEqual(manifest['version'],'19.0.1.67.0')
        tree=etree.parse(str(ROOT/'views/crm_yp_lead_form.xml'))
        row=tree.xpath("//div[contains(@class,'sgt_yp_geoloc_card')]")[0]
        self.assertEqual([x.get('string') for x in row.xpath('.//label')],['Lat','Lon'])
        self.assertEqual(len(row.xpath(".//button[@name='action_crm005_geolocate_now' and @string='Get Coordinates']")),1)
        scss=(ROOT/'static/src/scss/yellowpages_profile.scss').read_text('utf8')
        style=scss[scss.index('/* Update_057'):]
        self.assertIn('width: fit-content;',style)
        self.assertNotIn('width: 8.2rem;',style)
        self.assertIn('background: #eaf3fb;',style)

if __name__=='__main__': unittest.main()
