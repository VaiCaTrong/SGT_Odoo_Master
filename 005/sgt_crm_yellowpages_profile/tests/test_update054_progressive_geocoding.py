
"""Update_054: precise-to-approximate tiers, manual safety and approved UI.

All tests are offline/Odoo-stub tests, not live geocoder integration.
"""
import ast
import sys
import types
from pathlib import Path
import unittest
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from test_update047_geolocation import GEO, FakeLead, UTIL
from test_update051_geolocation_feedback import FakeGeocoder

class Env:
    def __init__(self, geocoder): self.geocoder=geocoder
    def __getitem__(self, model):
        assert model=='base.geocoder'
        return self.geocoder

def lead_with_provider(results, **extra):
    g=FakeGeocoder(results)
    ld=FakeLead(
        street='Lô G7, đường số 6, KCN Sóng Thần 2',
        street2='Phường Dĩ An',city='TP Hồ Chí Minh',
        state_id=types.SimpleNamespace(name='TP Hồ Chí Minh'),
        zip='',country_id=types.SimpleNamespace(name='Vietnam'),
        **extra)
    ld.env=Env(g)
    ld.with_context=lambda **kw: ld
    ld._crm005_geo_lookup=lambda: GEO.CrmLeadGeolocation._crm005_geo_lookup(ld)
    return ld,g

class Update054(unittest.TestCase):
    def test_first_query_full_address_has_address_precision(self):
        lead,g=lead_with_provider([(10.85,106.68)])
        self.assertEqual(lead._crm005_geo_process(), 'estimated')
        self.assertEqual(lead.x_yp_geo_precision,'address')
        self.assertEqual(len(g.calls),1)
        self.assertIn('Lô G7',g.calls[0][0])
    def test_city_only_fallback_keeps_approximate_precision(self):
        lead,g=lead_with_provider([None,None,None,None,(10.82,106.63)])
        self.assertEqual(lead._crm005_geo_process(), 'estimated')
        self.assertEqual(lead.x_yp_geo_precision,'city')
        self.assertEqual(len(g.calls),5)
        self.assertEqual(lead.x_yp_geo_status,'estimated')
    def test_neighborhood_fallback(self):
        lead,g=lead_with_provider([None,None,(10.89,106.75)])
        self.assertEqual(lead._crm005_geo_process(), 'estimated')
        self.assertEqual(lead.x_yp_geo_precision,'neighborhood')
    def test_region_fallback_does_not_masquerade_as_address(self):
        lead,g=lead_with_provider([None]*5+[(10.82,106.62)])
        self.assertEqual(lead._crm005_geo_process(), 'estimated')
        self.assertEqual(lead.x_yp_geo_precision,'region')
    def test_failed_all_stages_never_assigns_fake_latlon(self):
        lead,g=lead_with_provider([None]*8)
        self.assertEqual(lead._crm005_geo_process(), 'failed')
        self.assertEqual((lead.x_yp_latitude,lead.x_yp_longitude),(0,0))
        self.assertEqual(lead.x_yp_geo_status,'failed')
    def test_missing_country_does_not_guessed_coordinates(self):
        self.assertFalse(UTIL.address_is_usable('12 Main',city='Ha Noi',country=''))
        self.assertFalse(UTIL.address_is_usable('12 Main',country='Vietnam'))
        self.assertTrue(UTIL.address_is_usable('',city='Ha Noi',country='Vietnam'))
    def test_only_region_country_can_return_explicitly_approximate(self):
        ld=FakeLead(street='', street2='', city='',
                    state_id=types.SimpleNamespace(name='Hanoi'),
                    country_id=types.SimpleNamespace(name='Vietnam'))
        self.assertTrue(ld._crm005_geo_is_usable())
    def test_manual_input_works_and_is_protected_on_change(self):
        ld=FakeLead()
        ld.write({'x_yp_latitude':10.5,'x_yp_longitude':106.5})
        self.assertEqual(ld.x_yp_geo_precision,'manual')
        ld.write({'city':'Ha Noi'})
        self.assertEqual(ld.x_yp_geo_status,'review')
        self.assertEqual((ld.x_yp_latitude,ld.x_yp_longitude),(10.5,106.5))
    def test_manual_coordinates_block_one_click_provider_overwrite(self):
        ld=FakeLead(x_yp_latitude=10.5,x_yp_longitude=106.5,x_yp_geo_status='manual')
        with self.assertRaises(Exception):ld.action_crm005_geolocate_now()
        self.assertEqual((ld.x_yp_latitude,ld.x_yp_longitude),(10.5,106.5))
    def test_extension_readdress_preserves_last_known_auto_precision_as_historical(self):
        ld=FakeLead(x_yp_latitude=10.7,x_yp_longitude=106.6,
                    x_yp_geo_status='estimated',x_yp_geo_precision='region')
        ld.write({'street':'37 Nguyen Trai','state_id':types.SimpleNamespace(name='Hanoi')})
        self.assertEqual(ld.x_yp_geo_status,'pending')
        self.assertEqual(ld.x_yp_geo_precision, 'region')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.7, 106.6))
    def test_ui_only_title_values_and_one_button(self):
        tree=etree.parse(str(ROOT/'views/crm_yp_lead_form.xml'))
        nodes=tree.xpath('//div[contains(@class,"sgt_yp_geoloc_card")]')
        self.assertEqual(len(nodes),1)
        box=nodes[0]
        self.assertTrue(box.xpath('.//i[contains(@class,"sgt_yp_geoloc_pin")]'))
        self.assertEqual([l.get('string') for l in box.xpath('.//label')],['Lat','Lon'])
        self.assertEqual([b.get('name') for b in box.xpath('.//button')],['action_crm005_geolocate_now'])
        self.assertFalse(box.xpath('.//*[contains(@class,"sgt_yp_geoloc_help")]'))
        self.assertIn('x_yp_geo_precision',[f.get('name') for f in box.xpath('.//field')])
    def test_no_contact_created_or_modified(self):
        src=(ROOT/'models/geo_lead.py').read_text()
        self.assertNotIn("self.env['res.partner'].create",src)
        self.assertNotIn('res.partner.write',src)
        self.assertIn("self.env['base.geocoder'].sudo()",src)
        self.assertIn("limit=5",src)
    def test_manifest_and_xml(self):
        self.assertEqual(ast.literal_eval((ROOT/'__manifest__.py').read_text())['version'],'19.0.1.67.0')
        for xml in (ROOT/'views').glob('*.xml'): etree.parse(str(xml))
        for xml in (ROOT/'data').glob('*.xml'): etree.parse(str(xml))
if __name__ == '__main__': unittest.main()
