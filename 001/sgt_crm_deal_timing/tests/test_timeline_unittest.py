"""Dependency-free CRM-001 V03 verification (no Odoo / DB required)."""
import importlib.util
import pathlib
import re
import unittest
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('crm001_timeline', ROOT / 'models' / 'timeline.py')
timeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timeline)

BASE = datetime(2026, 10, 1, 12)
D = 86400


def evt(day, field, old, new, id=1):
    return {'at': BASE + timedelta(days=day), 'field': field, 'old': old, 'new': new, 'id': id}


def acc(day, current_stage, events, **kw):
    return timeline.cumulative_stage_seconds(
        created_at=BASE, now=BASE + timedelta(days=day),
        current_stage=current_stage, events=events, **kw)


class TimelineV03Test(unittest.TestCase):
    def test_initial_deal(self):
        self.assertEqual(acc(3, 1, []), {1: 3 * D})

    def test_stage_switch_starts_new_timer(self):
        vals = acc(5, 2, [evt(5, 'stage_id', 1, 2)])
        self.assertEqual(vals[1], 5 * D)
        self.assertEqual(vals.get(2, 0), 0)

    def test_revisit_accumulates_stage(self):
        vals = acc(10, 1, [evt(5, 'stage_id', 1, 2), evt(8, 'stage_id', 2, 1)])
        self.assertEqual((vals[1], vals[2]), (7 * D, 3 * D))

    def test_won_stage_keeps_counting(self):
        # V03: the Won stage is an ordinary stage, the counter never stops.
        vals = acc(20, 4, [evt(5, 'stage_id', 1, 4)], won_stage_ids={4})
        self.assertEqual(vals[1], 5 * D)
        self.assertEqual(vals[4], 15 * D)

    def test_won_then_reopened_counts_both(self):
        vals = acc(17, 1, [evt(5, 'stage_id', 1, 4), evt(15, 'stage_id', 4, 1)], won_stage_ids={4})
        self.assertEqual((vals[1], vals[4]), (7 * D, 10 * D))

    def test_lost_archive_keeps_counting(self):
        vals = acc(15, 1, [evt(5, 'active', 1, 0)], current_active=False, date_closed=BASE + timedelta(days=5))
        self.assertEqual(vals[1], 15 * D)

    def test_lost_and_reopen_keeps_counting(self):
        vals = acc(17, 1, [evt(5, 'active', 1, 0), evt(15, 'active', 0, 1)])
        self.assertEqual(vals[1], 17 * D)

    def test_hand_off_to_sale_inherits_counter(self):
        # Same record, same stage: a hand-off writes no stage_id event at all.
        vals = acc(30, 6, [evt(4, 'stage_id', 1, 6)])
        self.assertEqual(vals[6], 26 * D)

    def test_missing_stage_history_use_last_update(self):
        self.assertEqual(acc(10, 2, [], last_stage_update=BASE + timedelta(days=6))[2], 4 * D)

    def test_db_is_authoritative_when_chatter_misses_a_move(self):
        vals = acc(10, 3, [evt(5, 'stage_id', 1, 2)], last_stage_update=BASE + timedelta(days=8))
        self.assertEqual(vals[1], 5 * D)
        self.assertNotIn(2, vals)  # unverified stage gets no time
        self.assertEqual(vals[3], 2 * D)

    def test_days_are_elapsed_24h_blocks(self):
        self.assertEqual(timeline.elapsed_full_days(3 * D - 1), 2)
        self.assertEqual(timeline.elapsed_full_days(3 * D), 3)
        self.assertEqual(timeline.elapsed_full_days(-100), 0)

    def test_stage_color_boundary_values(self):
        for days, color in {0: 'green', 3: 'green', 4: 'yellow', 7: 'yellow', 8: 'red', 30: 'red'}.items():
            self.assertEqual(timeline.stage_color_from_days(days), color)

    def test_no_negative_when_future_created(self):
        self.assertEqual(timeline.cumulative_stage_seconds(BASE + timedelta(days=3), BASE, 1, events=[]), {})


class ContractV03Test(unittest.TestCase):
    def read(self, p):
        return (ROOT / p).read_text()

    def test_texts(self):
        code = self.read('models/crm_lead.py')
        self.assertIn("'Stage: %sd' % stage_days", code)
        self.assertIn("lead.sgt_crm001_total_text = '%sd' % elapsed_full_days(total_seconds)", code)
        for banned in ('ngày', 'Tổng', 'Đã dừng', 'stopped', 'won_status', 'is_won'):
            self.assertNotIn(banned, code, banned)

    def test_views_have_clock_icon_and_no_stopped_state(self):
        xml = self.read('views/crm_timing_views.xml')
        self.assertEqual(xml.count('fa fa-clock-o'), 3)  # leads kanban, opportunities kanban, form
        self.assertNotIn('stopped', xml)
        self.assertNotIn('ngày', xml)

    def test_css_one_slim_line(self):
        css = self.read('static/src/scss/crm_timing.scss')
        self.assertIn('justify-content: space-between', css)
        self.assertIn('white-space: nowrap', css)
        self.assertNotIn('border:', css)
        self.assertNotIn('stopped', css)
        self.assertEqual(css.count('{'), css.count('}'))

    def test_manifest_and_mm_isolation_untouched(self):
        self.assertIn("'version': '19.0.2.1.0'", self.read('__manifest__.py'))
        code = self.read('models/crm_lead.py')
        self.assertIn("mm_approval_mode", code)
        for name in ('def create', 'def write', 'def action_set_won', 'def action_set_lost'):
            self.assertNotIn(name, code)

    def test_parse_everything(self):
        import ast
        from lxml import etree
        for f in ROOT.rglob('*.py'):
            ast.parse(f.read_text())
        for f in ROOT.rglob('*.xml'):
            etree.parse(str(f))


if __name__ == '__main__':
    unittest.main()
