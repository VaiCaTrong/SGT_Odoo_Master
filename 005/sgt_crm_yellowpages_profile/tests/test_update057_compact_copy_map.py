"""Update_057 contract checks: UI-only feature with Update_056 GPS persistence unchanged."""
import ast
import zipfile
import unittest
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/mnt/data/sgt_crm_yellowpages_profile_CRM-005_V01_Update_056.zip')

class Geo057CompactActions(unittest.TestCase):
    def test_compact_row_and_object_button(self):
        tree = etree.parse(str(ROOT / 'views/crm_yp_lead_form.xml'))
        cards = tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," sgt_yp_geoloc_compact ")]')
        self.assertEqual(len(cards), 1)
        card=cards[0]
        self.assertEqual([x.get('string') for x in card.xpath('.//label')], ['Lat','Lon'])
        self.assertEqual(len(card.xpath('.//field[@name="x_yp_latitude"]')), 1)
        self.assertEqual(len(card.xpath('.//field[@name="x_yp_longitude"]')), 1)
        get=card.xpath('.//button[@name="action_crm005_geolocate_now"]')
        self.assertEqual(len(get),1)
        self.assertEqual(get[0].get('type'),'object')
        self.assertEqual(get[0].get('string'),'Get Coordinates')
        self.assertEqual(len(card.xpath('.//field[@name="x_yp_geo_precision" and @widget="sgt_crm005_geo_actions"]')),1)
        self.assertEqual(len(card.xpath('.//field[@name="x_yp_geo_status" and @invisible="1"]')),1)
        self.assertFalse(card.xpath('.//div[contains(@class,"sgt_yp_geoloc_header")]'))
    def test_styles_one_row_and_responsive(self):
        css=(ROOT/'static/src/scss/yellowpages_profile.scss').read_text()
        self.assertIn('width: fit-content;', css)
        self.assertIn('max-width: 100%;', css)
        self.assertIn('flex-flow: row wrap;', css)
        self.assertIn('@media (max-width: 540px)',css)
        self.assertIn('background: #eaf3fb;',css)
    def test_assets_templates_and_maps(self):
        manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text())
        self.assertEqual(manifest['version'],'19.0.1.67.0')
        assets=manifest['assets']['web.assets_backend']
        self.assertTrue(any('/js/geo_coordinate_actions.js' in a for a in assets))
        self.assertTrue(any('/xml/geo_coordinate_actions.xml' in a for a in assets))
        template=etree.parse(str(ROOT/'static/src/xml/geo_coordinate_actions.xml'))
        self.assertEqual(len(template.xpath('//t[@t-name="sgt_crm_yellowpages_profile.GeoCoordinateActions"]')),1)
        self.assertEqual(len(template.xpath('//button[@t-on-click="copyCoordinates"]')),1)
        self.assertEqual(len(template.xpath('//a[@target="_blank" and @rel="noopener noreferrer"]')),1)
        code=(ROOT/'static/src/js/geo_coordinate_actions.js').read_text()
        self.assertIn('navigator.clipboard.writeText',code)
        self.assertIn('encodeURIComponent(this.coordinates)',code)
        self.assertIn('supportedTypes: ["selection"]',code)
    def test_no_backend_data_change(self):
        if not BASE.exists(): self.skipTest('Update_056 reference ZIP absent')
        with zipfile.ZipFile(BASE) as z:
            # Update_058 intentionally changes only Gallery -> Documents logic.
            # Every other backend model must remain identical to the stable 056.
            for f in (ROOT/'models').glob('*.py'):
                if f.name in ('gallery_sync.py', 'gallery_sync_utils.py', 'crm_lead.py'):
                    continue
                self.assertEqual(f.read_bytes(),z.read('sgt_crm_yellowpages_profile/models/'+f.name),f.name)
            f=ROOT/'data/ir_cron_geo.xml'
            self.assertEqual(f.read_bytes(),z.read('sgt_crm_yellowpages_profile/data/ir_cron_geo.xml'))

if __name__=='__main__':unittest.main()
