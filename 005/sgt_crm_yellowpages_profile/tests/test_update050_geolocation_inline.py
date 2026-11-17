"""Offline regression for CRM-005 Update_050: minimal inline Latitude/Longitude."""
import ast
from pathlib import Path
import unittest
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]

class GeoInlineUI(unittest.TestCase):
    def test_form_has_minimal_fields_and_action(self):
        tree = etree.parse(str(ROOT/'views/crm_yp_lead_form.xml'))
        rows = tree.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' sgt_yp_geoloc_card ')]")
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual([l.get('string') for l in row.xpath('.//label')], ['Lat','Lon'])
        self.assertEqual(len(row.xpath(".//field[@name='x_yp_latitude']")),1)
        self.assertEqual(len(row.xpath(".//field[@name='x_yp_longitude']")),1)
        self.assertEqual(len(row.xpath(".//field[@name='x_yp_geo_status' and @invisible='1']")),1)
        self.assertEqual(len(row.xpath(".//button[@name='action_crm005_geolocate_now' and @type='object' and @string='Get Coordinates']")),1)
        self.assertFalse(row.xpath(".//*[contains(@class,'sgt_yp_geoloc_help') or contains(@class,'sgt_yp_geoloc_foot')]"))

    def test_compact_box_css(self):
        scss=(ROOT/'static/src/scss/yellowpages_profile.scss').read_text('utf-8')
        start=scss.index('.o_form_view .sgt_yp_geoloc_card.sgt_yp_geoloc_compact {')
        stop=scss.index('}',start)
        rule=scss[start:stop]
        for val in ('width: fit-content;', 'border: 1px solid', 'background: #eaf3fb;', 'box-shadow: none;'):
            self.assertIn(val, rule)
        self.assertIn('display: inline-flex;',scss)
        self.assertIn('flex-flow: row wrap;',scss)

    def test_manifest_version(self):
        manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text('utf-8'))
        self.assertEqual(manifest['version'],'19.0.1.66.0')

    def test_unchanged_geo_backend_and_cron(self):
        from zipfile import ZipFile
        z=Path('/mnt/data/sgt_crm_yellowpages_profile_CRM-005_V01_Update_059.zip')
        if not z.exists():self.skipTest('Source ZIP not available')
        with ZipFile(z) as source:
            for rel in ('models/geo_lead.py','data/ir_cron_geo.xml'):
                self.assertEqual((ROOT/rel).read_bytes(),source.read('sgt_crm_yellowpages_profile/'+rel),rel)

if __name__ == '__main__':unittest.main()
