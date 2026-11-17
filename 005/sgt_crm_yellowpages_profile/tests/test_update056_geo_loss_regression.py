"""P0 regression: imported address must not delete the last known GPS.

These are isolated Python/Odoo-stub tests, NOT Production integration tests.
"""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_update047_geolocation import FakeLead, UTIL


class Update056GeoPersistence(unittest.TestCase):
    def _located(self):
        ld = FakeLead(
            x_yp_latitude=10.8123456,
            x_yp_longitude=106.7123456,
            x_yp_geo_status='estimated',
            x_yp_geo_precision='address',
            x_yp_geo_updated_at='2026-11-12 09:00:00',
            lookup_result=(10.9, 106.9, 'city'),
        )
        ld.x_yp_geo_address_key = ld._crm005_geo_signature()
        return ld

    def test_001_address_changed_preserves_known_gps(self):
        ld = self._located()
        old_key, old_time = ld.x_yp_geo_address_key, ld.x_yp_geo_updated_at
        ld.write({'street': '99 Nguyen Hue, Ho Chi Minh City'})
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8123456, 106.7123456))
        self.assertEqual(ld.x_yp_geo_status, 'pending')
        self.assertEqual(ld.x_yp_geo_address_key, old_key)
        self.assertNotEqual(ld._crm005_geo_signature(), old_key)
        self.assertEqual(ld.x_yp_geo_updated_at, old_time)
        self.assertEqual(ld.x_yp_geo_precision, 'address')

    def test_002_failed_lookup_keeps_old_pair_and_key(self):
        ld = self._located()
        old_key = ld.x_yp_geo_address_key
        ld.write({'street2': 'New Ward'})
        ld.lookup_result = None
        self.assertEqual(ld._crm005_geo_process(manual=False), 'failed')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8123456, 106.7123456))
        self.assertEqual(ld.x_yp_geo_status, 'failed')
        self.assertEqual(ld.x_yp_geo_address_key, old_key)

    def test_003_valid_cron_replaces_pair_and_signature(self):
        ld = self._located()
        ld.write({'street': '99 Nguyen Hue, Ho Chi Minh City'})
        self.assertEqual(ld._crm005_geo_process(manual=False), 'estimated')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.9, 106.9))
        self.assertEqual(ld.x_yp_geo_precision, 'city')
        self.assertEqual(ld.x_yp_geo_address_key, ld._crm005_geo_signature())

    def test_004_address_change_when_country_removed_preserves_pair(self):
        ld = self._located()
        ld.write({'country_id': None})
        self.assertEqual(ld.x_yp_geo_status, 'missing')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8123456, 106.7123456))

    def test_005_identical_address_import_does_not_touch_pair(self):
        ld = self._located()
        ld.write({'street': ld.street})
        self.assertEqual(ld.x_yp_geo_status, 'estimated')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8123456, 106.7123456))

    def test_006_unrelated_extension_update_no_requeue(self):
        ld = self._located()
        ld.write({'phone': '+84900000000'})
        self.assertEqual(ld.x_yp_geo_status, 'estimated')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8123456, 106.7123456))

    def test_007_unchanged_gps_payload_plus_address_must_requeue(self):
        ld = self._located()
        ld.write({'street': '99 Nguyen Hue, Ho Chi Minh City',
                  'x_yp_latitude': 10.8123456, 'x_yp_longitude': 106.7123456})
        self.assertEqual(ld.x_yp_geo_status, 'pending')
        self.assertEqual(ld.x_yp_geo_precision, 'address')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8123456, 106.7123456))

    def test_008_explicit_new_gps_takes_precedence_and_marks_manual(self):
        ld = self._located()
        ld.write({'street': '99 Nguyen Hue, Ho Chi Minh City',
                  'x_yp_latitude': 10.9, 'x_yp_longitude': 106.9})
        self.assertEqual(ld.x_yp_geo_status, 'manual')
        self.assertEqual(ld.x_yp_geo_precision, 'manual')
        self.assertEqual(ld.x_yp_geo_address_key, ld._crm005_geo_signature())

    def test_009_manual_gps_and_review_preserved(self):
        ld = self._located()
        ld.write({'x_yp_latitude': 10.8, 'x_yp_longitude': 106.7})
        self.assertEqual(ld.x_yp_geo_status, 'manual')
        ld.write({'street': '99 Nguyen Hue, Ho Chi Minh City'})
        self.assertEqual(ld.x_yp_geo_status, 'review')
        self.assertEqual((ld.x_yp_latitude, ld.x_yp_longitude), (10.8, 106.7))

    def test_010_clear_pair_is_explicit_and_queues(self):
        ld = self._located()
        ld.write({'x_yp_latitude': 0.0, 'x_yp_longitude': 0.0})
        self.assertEqual(ld.x_yp_geo_status, 'pending')
        self.assertFalse(UTIL.valid_coordinates(ld.x_yp_latitude, ld.x_yp_longitude))

    def test_011_fresh_unlocated_failure_stays_zero(self):
        ld = FakeLead(lookup_result=None)
        self.assertEqual(ld._crm005_geo_process(), 'failed')
        self.assertEqual((ld.x_yp_latitude,ld.x_yp_longitude), (0,0))

    def test_012_geo_fields_unchanged_and_no_address_change_does_not_convert_to_manual(self):
        ld = self._located()
        ld.write({'x_yp_latitude':10.8123456,'x_yp_longitude':106.7123456})
        self.assertEqual(ld.x_yp_geo_status,'estimated')
        self.assertEqual(ld.x_yp_geo_precision,'address')


if __name__ == '__main__':
    unittest.main()
