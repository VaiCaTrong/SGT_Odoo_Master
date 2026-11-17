"""Offline unit checks for CRM-002 stage windows. Run: python -m unittest discover -s tests"""
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import unittest

module_path = Path(__file__).resolve().parents[1] / 'models' / 'timing.py'
spec = importlib.util.spec_from_file_location('crm002_timing', module_path)
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)
BASE = datetime(2026, 10, 1)


def dt(days):
    return BASE + timedelta(days=days)


class TimeWindowsTest(unittest.TestCase):
    def test_normal_stage_accumulates(self):
        windows = timing.active_windows(dt(0), dt(10), 3, True, {9}, [])
        self.assertEqual(timing.full_days(timing.visit_seconds([(dt(1), None)], windows, dt(10))), 9)

    def test_return_to_stage_resumes(self):
        windows = timing.active_windows(dt(0), dt(10), 3, True, {9}, [])
        visits = [(dt(0), dt(2)), (dt(6), None)]
        self.assertEqual(timing.full_days(timing.visit_seconds(visits, windows, dt(10))), 6)

    def test_lost_period_excluded_and_reopen_resumes(self):
        changes = [
            {'at': dt(3), 'id': 1, 'field': 'active', 'old': 1, 'new': 0},
            {'at': dt(7), 'id': 2, 'field': 'active', 'old': 0, 'new': 1},
        ]
        windows = timing.active_windows(dt(0), dt(10), 3, True, {9}, changes)
        self.assertEqual(windows, [(dt(0), dt(3)), (dt(7), dt(10))])
        self.assertEqual(timing.full_days(timing.visit_seconds([(dt(0), None)], windows, dt(10))), 6)

    def test_won_period_excluded_and_reopen_resumes(self):
        events = [
            {'at': dt(2), 'id': 1, 'field': 'stage_id', 'old': 3, 'new': 9},
            {'at': dt(8), 'id': 2, 'field': 'stage_id', 'old': 9, 'new': 3},
        ]
        windows = timing.active_windows(dt(0), dt(10), 3, True, {9}, events)
        self.assertEqual(windows, [(dt(0), dt(2)), (dt(8), dt(10))])
        self.assertEqual(timing.full_days(timing.visit_seconds([(dt(0), None)], windows, dt(10))), 4)

    def test_won_current_stopped(self):
        events = [{'at': dt(2), 'id': 1, 'field': 'stage_id', 'old': 3, 'new': 9}]
        windows = timing.active_windows(dt(0), dt(10), 9, True, {9}, events, currently_closed=True)
        self.assertEqual(windows, [(dt(0), dt(2))])
        self.assertEqual(timing.stage_color(2, True), 'stopped')

    def test_stage_colors(self):
        self.assertEqual([timing.stage_color(x) for x in (0, 3, 4, 7, 8)],
                         ['green', 'green', 'yellow', 'yellow', 'red'])

    def test_fallback_date_closed(self):
        windows = timing.active_windows(dt(0), dt(10), 3, False, {9}, [],
                                        date_closed=dt(5), currently_closed=True)
        self.assertEqual(windows, [(dt(0), dt(5))])

    def test_total_age_not_excluded_by_status(self):
        total = timing.full_days((dt(10) - dt(0)).total_seconds())
        self.assertEqual(total, 10)


if __name__ == '__main__':
    unittest.main()
