"""Update_053: no artificial coordinates; actionable map fallback."""
import ast
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import unittest
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from test_update047_geolocation import GEO, FakeLead

class Geo053(unittest.TestCase):
    def test_map_action_uses_company_and_full_address(self):
        lead=FakeLead(street='Lô G7, đường số 6, KCN Sóng Thần 2',street2='Phường Dĩ An',city='TP Hồ Chí Minh')
        lead.partner_name='Kho lạnh ARC Bình Dương'
        lead.check_access=lambda mode: None
        got=lead.action_crm005_find_on_map()
        self.assertEqual(got['type'],'ir.actions.act_url')
        self.assertEqual(got['target'],'new')
        p=urlparse(got['url'])
        self.assertEqual(p.scheme,'https')
        self.assertEqual(p.hostname,'www.google.com')
        q=parse_qs(p.query)['query'][0]
        self.assertIn('Kho lạnh ARC Bình Dương',q)
        self.assertIn('Lô G7',q)
        self.assertIn('Phường Dĩ An',q)
        self.assertIn('Vietnam',q)
    def test_map_action_does_not_write_coordinates(self):
        lead=FakeLead(x_yp_latitude=10.91,x_yp_longitude=106.74,x_yp_geo_status='manual')
        lead.partner_name='ARC'
        lead.check_access=lambda mode: None
        lead.action_crm005_find_on_map()
        self.assertEqual((lead.x_yp_latitude,lead.x_yp_longitude),(10.91,106.74))
        self.assertEqual(lead.x_yp_geo_status,'manual')
    def test_no_coordinate_result_is_actionable(self):
        lead=FakeLead(lookup_result=None)
        res=lead.action_crm005_geolocate_now()
        self.assertEqual(res['tag'],'display_notification')
        self.assertIn('No coordinates found',res['params']['message'])
        self.assertEqual((lead.x_yp_latitude,lead.x_yp_longitude),(0,0))
    def test_layout_has_compact_box_and_both_actions(self):
        root=etree.parse(str(ROOT/'views/crm_yp_lead_form.xml'))
        box=root.xpath('//div[contains(@class,"sgt_yp_geoloc_card")]')[0]
        self.assertEqual([x.get('string') for x in box.xpath('.//label')],['Lat','Lon'])
        buttons=box.xpath('.//button[@type="object"]')
        self.assertEqual([x.get('name') for x in buttons],['action_crm005_geolocate_now'])
        self.assertEqual(ast.literal_eval((ROOT/'__manifest__.py').read_text())['version'],'19.0.1.67.0')
    def test_guard_against_faking_coordinates(self):
        src=(ROOT/'models/geo_lead.py').read_text()
        self.assertIn('valid_coordinates(coords[0], coords[1])',src)
        self.assertNotIn("self.env['res.partner'].create",src)
        self.assertIn("'x_yp_geo_status': 'failed'",src)

if __name__=='__main__': unittest.main()
