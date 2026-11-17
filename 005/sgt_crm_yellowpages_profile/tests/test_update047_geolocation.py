"""Offline contract and ORM-stub regression tests for Update_047.

This is not a substitute for Odoo 19 integration tests on a database clone.
"""
import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def _load():
    pkg = 'crm005_geo_testpkg'
    sys.modules.setdefault(pkg, types.ModuleType(pkg)).__path__ = [str(ROOT / 'models')]
    geo_utils_spec = importlib.util.spec_from_file_location(pkg + '.geo_utils', ROOT / 'models/geo_utils.py')
    util = importlib.util.module_from_spec(geo_utils_spec)
    sys.modules[pkg + '.geo_utils'] = util
    geo_utils_spec.loader.exec_module(util)
    original_odoo = sys.modules.get('odoo')
    original_exceptions = sys.modules.get('odoo.exceptions')
    odoo = types.ModuleType('odoo')
    sys.modules['odoo'] = odoo
    class StubModel:
        def write(self, vals):
            self.__dict__.update(vals)
            return True
    class FakeFields:
        class Datetime:
            def __new__(cls, *args, **kwargs):
                return None
            @staticmethod
            def now():
                return datetime(2026, 11, 11, 0, 0, 0)
        def __getattr__(self, unused):
            return lambda *a, **kw: None
    class FakeAPI:
        @staticmethod
        def model_create_multi(func):
            return func
        @staticmethod
        def model(func):
            return func
    odoo.fields = FakeFields()
    odoo.models = types.SimpleNamespace(Model=StubModel)
    odoo.api = FakeAPI
    odoo._ = lambda x: x
    exceptions = types.ModuleType('odoo.exceptions')
    exceptions.UserError = type('UserError', (Exception,), {})
    sys.modules['odoo.exceptions'] = exceptions
    spec = importlib.util.spec_from_file_location(pkg + '.geo_lead', ROOT / 'models/geo_lead.py')
    geo = importlib.util.module_from_spec(spec)
    sys.modules[pkg + '.geo_lead'] = geo
    try:
        spec.loader.exec_module(geo)
    finally:
        if original_odoo is None:
            sys.modules.pop('odoo', None)
        else:
            sys.modules['odoo'] = original_odoo
        if original_exceptions is None:
            sys.modules.pop('odoo.exceptions', None)
        else:
            sys.modules['odoo.exceptions'] = original_exceptions
    return util, geo


UTIL, GEO = _load()


class FakeLead(GEO.CrmLeadGeolocation):
    def __init__(self, **overrides):
        self.id = 42
        self.street = '123 Le Loi, District 1, Ho Chi Minh City'
        self.street2 = ''
        self.city = 'Ho Chi Minh City'
        self.state_id = None
        self.country_id = types.SimpleNamespace(name='Vietnam')
        self.zip = ''
        self.x_yp_latitude = 0.0
        self.x_yp_longitude = 0.0
        self.x_yp_geo_status = 'pending'
        self.x_yp_geo_updated_at = None
        self.x_yp_geo_attempted_at = None
        self.x_yp_geo_attempt_count = 0
        self.x_yp_geo_address_key = None
        self.lookup_result = (10.77, 106.69)
        self.env = types.SimpleNamespace(context={})
        self.__dict__.update(overrides)

    def __iter__(self):
        yield self

    def ensure_one(self):
        return self

    def _crm005_geo_internal_write(self, vals):
        self.__dict__.update(vals)
        return True

    def _crm005_geo_lookup(self):
        return self.lookup_result

    def check_access(self, mode):
        assert mode == 'write'


class GeoUpdate047(unittest.TestCase):
    def test_invalid_coordinates_and_location_eligibility(self):
        self.assertFalse(UTIL.valid_coordinates(0, 0))
        self.assertFalse(UTIL.valid_coordinates(float('nan'), 106))
        self.assertFalse(UTIL.valid_coordinates(91, 106))
        self.assertFalse(UTIL.valid_coordinates(10, 200))
        self.assertTrue(UTIL.valid_coordinates(0, 106))
        self.assertTrue(UTIL.valid_coordinates(10.123, 106.456))
        self.assertFalse(UTIL.address_is_usable('123 Le Loi', city='Ho Chi Minh City'))
        self.assertFalse(UTIL.address_is_usable('123 Le Loi, District 1, Ho Chi Minh City'))
        self.assertTrue(UTIL.address_is_usable('', city='Ho Chi Minh City', country='Vietnam'))
        self.assertFalse(UTIL.address_is_usable('X'))

    def test_import_rewriting_same_address_does_not_requeue(self):
        lead = FakeLead(x_yp_latitude=10.77, x_yp_longitude=106.69, x_yp_geo_status='estimated')
        lead.write({'street': '123 Le Loi, District 1, Ho Chi Minh City'})
        self.assertEqual(lead.x_yp_geo_status, 'estimated')
        self.assertEqual(lead.x_yp_latitude, 10.77)

    def test_extension_updates_address_and_preserves_last_known_coords(self):
        lead = FakeLead(x_yp_latitude=10.77, x_yp_longitude=106.69, x_yp_geo_status='estimated')
        lead.write({'street': '456 Nguyen Hue, District 1, Ho Chi Minh City'})
        self.assertEqual(lead.x_yp_geo_status, 'pending')
        self.assertEqual((lead.x_yp_latitude, lead.x_yp_longitude), (10.77, 106.69))

    def test_manual_coordinates_stay_after_extension_changes_address(self):
        lead = FakeLead()
        lead.write({'x_yp_latitude': 10.5, 'x_yp_longitude': 106.5})
        self.assertEqual(lead.x_yp_geo_status, 'manual')
        lead.write({'street': '456 Nguyen Hue, District 1, Ho Chi Minh City'})
        self.assertEqual(lead.x_yp_geo_status, 'review')
        self.assertEqual((lead.x_yp_latitude, lead.x_yp_longitude), (10.5, 106.5))

    def test_cron_success_marks_unverified_estimate(self):
        lead = FakeLead()
        self.assertEqual(lead._crm005_geo_process(), 'estimated')
        self.assertEqual((lead.x_yp_latitude, lead.x_yp_longitude), (10.77, 106.69))
        self.assertEqual(lead.x_yp_geo_status, 'estimated')
        self.assertTrue(lead.x_yp_geo_updated_at)

    def test_provider_failure_does_not_remove_manual_coordinates(self):
        lead = FakeLead(x_yp_latitude=10.5, x_yp_longitude=106.5,
                        x_yp_geo_status='manual', lookup_result=None)
        self.assertEqual(lead._crm005_geo_process(manual=True), 'failed_preserved')
        self.assertEqual((lead.x_yp_latitude, lead.x_yp_longitude), (10.5, 106.5))
        self.assertEqual(lead.x_yp_geo_status, 'manual')

    def test_address_only_city_never_gets_city_centroid(self):
        lead = FakeLead(street='', city='Hanoi')
        self.assertEqual(lead._crm005_geo_process(), 'estimated')
        self.assertEqual((lead.x_yp_latitude, lead.x_yp_longitude), (10.77, 106.69))

    def test_manifest_form_and_cron(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertIn('base_geolocalize', manifest['depends'])
        self.assertEqual(manifest['version'], '19.0.1.66.0')
        view = etree.parse(str(ROOT / 'views/crm_yp_lead_form.xml'))
        assert view.xpath("//div[contains(@class, 'sgt_yp_profile')]//field[@name='x_yp_latitude']")
        assert view.xpath("//div[contains(@class, 'sgt_yp_profile')]//field[@name='x_yp_longitude']")
        assert view.xpath("//button[@name='action_crm005_geolocate_now']")
        cron = etree.parse(str(ROOT / 'data/ir_cron_geo.xml'))
        assert cron.xpath("//record[@model='ir.cron']/field[@name='code' and text()='model._cron_crm005_geolocate_pending()']")
        src = (ROOT / 'models/geo_lead.py').read_text()
        self.assertNotIn("self.env['res.partner'].create", src)
        self.assertNotIn('res.partner.write', src)
        self.assertIn("limit=5", src)
        self.assertIn("if old_signature[lead.id] == lead._crm005_geo_signature()", src)


if __name__ == '__main__':
    unittest.main()
