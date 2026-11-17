"""Update_016 (+ 017 required list/red frames, + 025 no blocking, Evidence, auto red frames in 5/6): required data (bell), stage age (bar / label / list), column bar numbers.

Runs the REAL compute methods (`_compute_sgt_crm002_missing`, `_compute_sgt_crm002_gate`) and the real timing helpers against fakes;
views / templates / SCSS are checked as text and against the Xinyang production Scan views (xpath targets).
NOT covered here (check on Demo 2): Odoo accepting the `_read_group_groupby` SQL, the `web.ColumnProgress` template
extension, the CSS-only bell tooltips, real rendering, the bell on the Kanban card of the hand-edited view.
Usage: python3 -I test_update016_age_guard.py [odoo_views.csv]
"""
import ast
import csv
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'models'))
import timing  # noqa: E402  (pure module, no Odoo import)

SRC = (ROOT / 'models' / 'crm_lead.py').read_text()
VIEWS_CSV = None


class FakeUserError(Exception):
    pass


def load_methods(*names):
    """Real methods of CrmLead (decorators stripped), run against fakes."""
    tree = ast.parse(SRC)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CrmLead')
    fns = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(fns) == len(names), names
    for fn in fns:
        fn.decorator_list = []
    node = ast.ClassDef(name='L', bases=[], keywords=[], body=fns, decorator_list=[])
    mod = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {'UserError': FakeUserError, 'timing': timing}
    exec(compile(mod, 'crm_lead.py', 'exec'), ns)
    return ns['L']


Methods = load_methods('_compute_sgt_crm002_missing', '_compute_sgt_crm002_gate')


class Stage(SimpleNamespace):
    def __eq__(self, other):
        return getattr(other, 'id', None) == self.id

    def __hash__(self):
        return self.id


class Rec:
    """Many2one value: truthy when it holds a record, falsy when empty (like an Odoo recordset)."""
    def __init__(self, name=''):
        self.name = name

    def __bool__(self):
        return bool(self.name)


class FakeLead:
    def __init__(self, stage, **vals):
        self.stage_id = stage
        self.vals = {'partner_id': Rec('P'), 'email_from': 'a@b.vn', 'phone': '+84', 'source_id': Rec('S'),
                     'x_getfly_id': 'VN021404', 'street': 'Hải Dương',
                     'x_yp_evidence_html': '<p><img src="/web/image/12"></p>', **vals}
        self.display_name = vals.get('name', 'Mr. Việt')

    def __getitem__(self, key):
        return self.vals[key]


ALL_FIELDS = ('partner_id', 'email_from', 'phone', 'source_id', 'x_getfly_id', 'street', 'x_yp_evidence_html')


def compute(leads, fields=ALL_FIELDS):
    class Set(Methods):
        def __iter__(self_inner):
            return iter(leads)
    s = Set()
    s._fields = {f: None for f in fields}
    s._compute_sgt_crm002_missing()
    s._compute_sgt_crm002_gate()
    return leads


S4 = Stage(id=4, name='4.Interesting')
S5 = Stage(id=5, name='5.Match Making')
S6 = Stage(id=6, name='6.Approved Match Making')
S7 = Stage(id=7, name='7.Chờ xử lý')


class Update025Tests(unittest.TestCase):
    """2026-10-31 08:38: no more blocking popup; bell red as before + Evidence; auto red frames in columns 5/6."""

    def test_guard_is_gone(self):
        self.assertNotIn('def _sgt_crm002_check_stage_requirements', SRC)
        self.assertNotIn('self._sgt_crm002_check_stage_requirements(vals)', SRC)
        self.assertNotIn("'Không thể chuyển sang %s.'", SRC)
        w = SRC[SRC.index('    def write(self, vals):'):]
        w = w[:w.index('\n    def ', 10)]
        self.assertNotIn('missing_labels', w)          # write() does not look at the required data at all

    def test_complete_deal_is_green(self):
        (lead,) = compute([FakeLead(S5)])
        self.assertFalse(lead.sgt_crm002_missing_info)

    def test_missing_labels_in_user_words_with_evidence_last(self):
        (lead,) = compute([FakeLead(S5, phone=False, street='', x_yp_evidence_html='<p><br></p>')])
        self.assertEqual(lead.sgt_crm002_missing_info, 'Phone, Address, Evidence')

    def test_evidence_text_without_picture_is_missing(self):
        for html in (False, None, '', '<p><br></p>', '<p>đã gọi khách</p>'):
            (lead,) = compute([FakeLead(S4, x_yp_evidence_html=html)])
            self.assertEqual(lead.sgt_crm002_missing_info, 'Evidence', html)
        (lead,) = compute([FakeLead(S4, x_yp_evidence_html='<P><IMG SRC="data:image/png;base64,AA"></P>')])
        self.assertFalse(lead.sgt_crm002_missing_info)

    def test_without_crm005_evidence_is_not_required(self):
        (lead,) = compute([FakeLead(S5, x_yp_evidence_html=False)], fields=ALL_FIELDS[:-1])
        self.assertFalse(lead.sgt_crm002_missing_info)

    def test_field_missing_in_database_is_skipped_not_reported(self):
        (lead,) = compute([FakeLead(S4, x_getfly_id='')], fields=('partner_id', 'email_from', 'phone', 'source_id', 'street'))
        self.assertFalse(lead.sgt_crm002_missing_info)

    def test_gate_only_in_columns_5_and_6(self):
        leads = compute([FakeLead(S4), FakeLead(S5), FakeLead(S6), FakeLead(S7), FakeLead(Stage(id=0, name=False))])
        self.assertEqual([l.sgt_crm002_gate for l in leads], [False, True, True, False, False])

    def test_gate_and_evidence_fields_are_not_stored(self):
        self.assertIn("sgt_crm002_gate = fields.Boolean(\n        string='In Match Making Columns', compute='_compute_sgt_crm002_gate')", SRC)
        self.assertNotIn('store=True', SRC[SRC.index('sgt_crm002_gate = fields.Boolean('):SRC.index('def _sgt_crm002_since')])


class TimingTests(unittest.TestCase):
    now = datetime(2026, 10, 28, 12, 0)

    def test_buckets(self):
        self.assertEqual([timing.age_bucket(d) for d in (0, 3, 4, 7, 8, 30)],
                         ['fresh', 'fresh', 'warn', 'warn', 'late', 'late'])

    def test_won_has_no_colour(self):
        self.assertFalse(timing.age_bucket(50, closed=True))

    def test_age_days_whole_days(self):
        self.assertEqual(timing.age_days(self.now - timedelta(days=2, hours=23), self.now), 2)
        self.assertEqual(timing.age_days(self.now - timedelta(days=3), self.now), 3)
        self.assertEqual(timing.age_days(None, self.now), 0)
        self.assertEqual(timing.age_days(self.now + timedelta(days=1), self.now), 0)

    def test_stage_color_unchanged(self):
        self.assertEqual(timing.stage_color(3), 'green')
        self.assertEqual(timing.stage_color(4), 'yellow')
        self.assertEqual(timing.stage_color(8), 'red')

    def test_missing_labels(self):
        vals = {'phone': '', 'email_from': 'a@b', 'x_getfly_id': None, 'partner_id': Rec(''), 'source_id': Rec('S'), 'street': 'x'}
        self.assertEqual(timing.missing_labels(vals.get), ['Contact', 'Phone', 'VN Odoo ID'])
        self.assertEqual(timing.missing_labels(vals.get, available={'email_from'}), [])

    def test_required_list_is_the_one_chosen_by_the_user(self):
        # 2026-10-28 13:00: everything in screenshot 1 (Contact, Email, Phone, Source, VN Odoo ID) + Address
        self.assertEqual([l for _f, l in timing.MM_REQUIRED_FIELDS],
                         ['Contact', 'Email', 'Phone', 'Source', 'VN Odoo ID', 'Address'])
        self.assertEqual([f for f, _l in timing.MM_REQUIRED_FIELDS],
                         ['partner_id', 'email_from', 'phone', 'source_id', 'x_getfly_id', 'street'])


# ---- Update_023: the REAL search method, run against a tiny domain evaluator --------------------------
class OrderedSetLike:
    """Odoo 19 passes ('in', OrderedSet(['fresh'])) for ('=', 'fresh'): iterable, but neither list nor tuple."""
    def __init__(self, items):
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)


def load_search_methods():
    tree = ast.parse(SRC)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CrmLead')
    wanted = ('_sgt_crm002_bucket_domain', '_search_sgt_crm002_age_bucket')
    fns = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    for fn in fns:
        fn.decorator_list = []
    mod = ast.Module(body=[ast.ClassDef(name='L', bases=[], keywords=[], body=fns, decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(mod)
    fixed_now = datetime(2026, 10, 28, 12, 0)
    ns = {'UserError': FakeUserError, 'timing': timing,
          'fields': SimpleNamespace(Datetime=SimpleNamespace(now=staticmethod(lambda: fixed_now)))}
    exec(compile(mod, 'crm_lead.py', 'exec'), ns)
    return ns['L'](), fixed_now


def eval_domain(domain, rec):
    """Prefix-notation evaluator for the leaves used by the bucket domain."""
    it = iter(domain)

    def node():
        tok = next(it)
        if tok == '&':
            a, b = node(), node()
            return a and b
        if tok == '|':
            a, b = node(), node()
            return a or b
        if tok == '!':
            return not node()
        name, op, val = tok
        left = rec.get(name)
        if op == '=':
            return left == val
        if op == 'in':
            return left in val
        if left is None or left is False or val is None:     # SQL NULL: ordering comparisons are false
            return False
        return {'<': left < val, '<=': left <= val, '>': left > val}[op]
    res = node()
    assert next(it, None) is None, 'unused tokens in domain'
    return res


class SearchBucketTests(unittest.TestCase):
    def setUp(self):
        self.model, self.now = load_search_methods()
        self.deals = []
        for days in (0, 1, 3, 4, 7, 8, 30, 190):
            for since_set in (True, False):          # sgt_crm002_stage_since set / empty (old Deals)
                t = self.now - timedelta(days=days, hours=1)
                self.deals.append({'days': days, 'probability': 20,
                                   'sgt_crm002_stage_since': t if since_set else False,
                                   'date_last_stage_update': t})
        self.deals.append({'days': 5, 'probability': 100, 'sgt_crm002_stage_since': False,
                           'date_last_stage_update': self.now - timedelta(days=5)})   # Won: no colour

    def ids(self, operator, value):
        dom = self.model._search_sgt_crm002_age_bucket(operator, value)
        return [i for i, d in enumerate(self.deals) if eval_domain(dom, d)]

    def expected(self, *buckets):
        return [i for i, d in enumerate(self.deals)
                if timing.age_bucket(d['days'], closed=d['probability'] >= 100) in buckets]

    def test_every_value_shape_odoo_may_send(self):
        shapes = ('fresh', ['fresh'], ('fresh',), OrderedSetLike(['fresh']), frozenset(['fresh']))
        for shape in shapes:
            for op in ('=', 'in'):
                with self.subTest(op=op, shape=type(shape).__name__):
                    got = self.ids(op, shape)
                    self.assertTrue(got)                                   # the Update_016-022 bug: always empty
                    self.assertEqual(got, self.expected('fresh'))

    def test_each_bucket_matches_the_timing_rule(self):
        for b in ('fresh', 'warn', 'late'):
            self.assertEqual(self.ids('in', OrderedSetLike([b])), self.expected(b))

    def test_several_buckets_and_negation(self):
        self.assertEqual(self.ids('in', OrderedSetLike(['fresh', 'warn'])), self.expected('fresh', 'warn'))
        self.assertEqual(self.ids('in', ['fresh', 'warn', 'late']), self.expected('fresh', 'warn', 'late'))
        # "Other" bar of Odoo = not in (all keys) -> only the Won deal
        none_of = self.expected('fresh', 'warn', 'late')
        got = self.ids('not in', OrderedSetLike(['fresh', 'warn', 'late']))
        self.assertEqual(got, [i for i in range(len(self.deals)) if i not in none_of])
        self.assertEqual(self.ids('!=', 'late'), [i for i in range(len(self.deals)) if i not in self.expected('late')])

    def test_unknown_values_match_nothing(self):
        self.assertEqual(self.ids('in', OrderedSetLike(['bogus'])), [])


class SourceChecks(unittest.TestCase):
    def test_model_source(self):
        for text in ("sgt_crm002_stage_since = fields.Datetime(", "sgt_crm002_missing_info = fields.Char(",
                     "sgt_crm002_age_bucket = fields.Selection(", "sgt_crm002_age_days = fields.Integer(",
                     "def _read_group_groupby(self, alias, groupby_spec, query):",
                     "'sgt_crm002_stage_since': fields.Datetime.now()"):
            self.assertIn(text, SRC)
        self.assertNotIn('ir.cron', SRC)

    def test_stored_field_count(self):
        # exactly ONE new database column: the stage-since date; the other three are computed, not stored
        tree = ast.parse(SRC)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CrmLead')
        new = {}
        for n in cls.body:
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.startswith('sgt_crm002_age') \
                    or isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('sgt_crm002_stage_since', 'sgt_crm002_missing_info', 'sgt_crm002_gate'):
                kws = {k.arg for k in n.value.keywords}
                new[n.targets[0].id] = 'compute' in kws
        self.assertEqual(new, {'sgt_crm002_stage_since': False, 'sgt_crm002_age_days': True,
                               'sgt_crm002_age_bucket': True, 'sgt_crm002_missing_info': True,
                               'sgt_crm002_gate': True})

    def test_manifest_assets_and_data(self):
        m = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(m['version'], '19.0.1.26.0')
        self.assertIn('views/lead_age_bell.xml', m['data'])
        a = m['assets']['web.assets_backend']
        self.assertIn('sgt_crm_campaign/static/src/xml/column_progress.xml', a)
        self.assertIn('sgt_crm_campaign/static/src/scss/age_bell.scss', a)
        # still ONE JavaScript file pair, none new
        self.assertEqual(sorted(x for x in a if x.endswith('.js')),
                         ['sgt_crm_campaign/static/src/js/native_pipeline.js', 'sgt_crm_campaign/static/src/js/workspace.js'])

    def test_views_parse_and_content(self):
        t = ET.parse(ROOT / 'views' / 'lead_age_bell.xml').getroot()
        arch = {r.get('id'): ''.join(ET.tostring(r, encoding='unicode')) for r in t.iter('record')}
        k = arch['view_crm002_lead_kanban_age_bell']
        self.assertIn('field">sgt_crm002_age_bucket<', k)
        self.assertIn('"fresh": "success"', k)
        self.assertIn("//field[@name='rotting_days']", k)
        self.assertIn("record.sgt_crm002_missing_info.raw_value", k)
        self.assertNotIn('border-left', k)                  # no coloured left border on Kanban cards
        l = arch['view_crm002_lead_list_age_bell']
        self.assertIn('decoration-danger="sgt_crm002_age_bucket', l)
        f = arch['view_crm002_lead_form_bell']
        self.assertIn("contains(@class,'oe_title')", f)
        self.assertNotIn('hasclass', f)
        self.assertIn('invisible="not sgt_crm002_missing_info"', f)
        self.assertNotIn('x_phone', ''.join(arch.values()))   # technical names never shown
        self.assertIn('tabindex="0"', f)                      # bell is focusable: click = red frames

    def test_column_progress_template_is_limited_to_the_age_bar(self):
        x = (ROOT / 'static/src/xml/column_progress.xml').read_text()
        ET.fromstring(x)
        self.assertIn('t-inherit="crm.ColumnProgress"', x)      # Main Pipeline
        self.assertIn('t-inherit="web.ColumnProgress"', x)      # Update_030: Data/Sale funnels
        self.assertEqual(x.count("['fresh', 'warn', 'late'].includes"), 6)   # tooltip, segment, total x2
        self.assertIn('props.group.count', x)
        self.assertNotIn('{', x.split('t-attf-data-tooltip">')[1].split('</attribute>')[0].strip()[2:-2])  # no brace inside {{ }}

    def test_update017_red_frames_for_every_required_field(self):
        t = ET.parse(ROOT / 'views' / 'lead_age_bell.xml').getroot()
        form = next(r for r in t.iter('record') if r.get('id') == 'view_crm002_lead_form_bell')
        flags = {e.get('class').split()[-1].replace('sgt002-miss-', ''): e.get('invisible')
                 for e in form.iter('span') if 'sgt002-miss' in (e.get('class') or '')}
        names = [f for f, _l in timing.MM_REQUIRED_FIELDS]
        self.assertEqual(flags.pop('evidence'), None)      # Update_025: CSS decides (CRM-005 Evidence box)
        self.assertEqual(sorted(flags), sorted(names))
        for n in names:                       # the flag exists only while the field is empty
            self.assertEqual(flags[n], n)
        in_view = {e.get('name') for e in form.iter('field') if e.get('invisible') == '1'}
        self.assertTrue(set(names) <= in_view)  # modifiers need the fields present in the view
        scss = (ROOT / 'static/src/scss/age_bell.scss').read_text()
        for n in names:
            self.assertIn(n, scss.split('@each $f in (')[1].split(')')[0])
        self.assertIn('.sgt002-bell-btn:focus', scss)
        self.assertIn('.o_field_widget[name="#{$f}"]', scss)

    def test_update018_settings_buttons_light_grey(self):
        s = (ROOT / 'static/src/scss/workspace.scss').read_text()
        self.assertIn('.sgt002-native-settings > .sgt002-native-btn {', s)
        self.assertIn('background: #e3e6ea;', s)
        self.assertIn('.sgt002-native-settings > .sgt002-native-btn:hover { background: #d3d7dd; }', s)
        x = (ROOT / 'static/src/xml/native_pipeline.xml').read_text()
        self.assertEqual(x.count('class="sgt002-native-btn"'), 2)       # Permissions + Settings only

    def test_update019_no_forbidden_attribute_in_view_arch(self):
        # production error 2026-10-28 07:31: "Forbidden attribute used in arch (t-att-data-tooltip)".
        # Odoo 19 _validate_attributes forbids data-tooltip / data-tooltip-template / data-tooltip-info,
        # also with the t-att- / t-attf- prefix, in EVERY view arch.  Tooltips in arch use `title`.
        import re
        x = (ROOT / 'views' / 'lead_age_bell.xml').read_text()
        self.assertIsNone(re.search(r'(t-att-|t-attf-)?data-tooltip(-template|-info)?\s*=', x))
        for f in (ROOT / 'views').glob('*.xml'):
            self.assertIsNone(re.search(r'(t-att-|t-attf-)?data-tooltip(-template|-info)?\s*=', f.read_text()), f.name)
        self.assertIn('t-att-title="', x)
        self.assertIn('title="Đã đủ dữ liệu"', x)

    def test_update020_bell_icon_has_no_own_title(self):
        # 2026-10-28 14:38: hovering the bell showed "Dữ liệu" (title of the <i>) instead of the
        # missing-field list (title of the parent span): the nearest title wins in the browser.
        import re
        x = (ROOT / 'views' / 'lead_age_bell.xml').read_text()
        icons = re.findall(r'<i class="fa fa-bell"[^>]*/>', x)
        self.assertEqual(len(icons), 4)
        for i in icons:
            self.assertNotIn('title=', i)

    def test_update021_no_age_badge_on_card_and_no_global_age_class(self):
        # 2026-10-28 14:45: the "Nd" badge on the card was redundant (the bar already shows the days) and the global
        # .sgt002-age rule also restyled the existing workspace stage-days labels (class collision).
        x = (ROOT / 'views' / 'lead_age_bell.xml').read_text()
        k = x[:x.index('view_crm002_lead_list_age_bell')]
        self.assertNotIn('sgt002-age', k)
        self.assertNotIn('Số ngày ở stage', k)
        s = (ROOT / 'static/src/scss/age_bell.scss').read_text()
        self.assertNotIn('.sgt002-age {', s)
        self.assertNotIn('.sgt002-age-late', s)

    def test_update022_form_bell_is_a_number_above_the_title(self):
        # 2026-10-28 15:45: no field names in a tooltip (they got clipped); the bell shows a NUMBER and sits on its
        # own line above the title (the Won ribbon covered it).  The number is a CSS counter over the flag spans.
        import re
        x = (ROOT / 'views' / 'lead_age_bell.xml').read_text()
        f = x[x.index('view_crm002_lead_form_bell'):]
        self.assertIn('position="before"', f)
        self.assertNotIn('sgt002-bell-field', f)
        self.assertIn('sgt002-bell-num', f)
        first_flag = f.index('sgt002-miss sgt002-miss-')
        self.assertLess(first_flag, f.index('sgt002-bell-btn'))   # counter counts what precedes the bell
        s = (ROOT / 'static/src/scss/age_bell.scss').read_text()
        self.assertIn('counter-reset: sgt002miss', s)
        self.assertIn('counter-increment: sgt002miss', s)
        self.assertIn('counter(sgt002miss)', s)
        self.assertNotIn('bell-field', s)
        self.assertIsNone(re.search(r'\.sgt002-miss\s*\{[^}]*display:\s*none', s))   # only the evidence flag may be hidden

    def test_update025_auto_red_frames_in_columns_5_6_and_evidence(self):
        t = ET.parse(ROOT / 'views' / 'lead_age_bell.xml').getroot()
        form = next(r for r in t.iter('record') if r.get('id') == 'view_crm002_lead_form_bell')
        xml = ET.tostring(form, encoding='unicode')
        self.assertIn('<field name="sgt_crm002_gate" invisible="1" />', xml)
        self.assertIn('<span class="sgt002-gate-on" invisible="not sgt_crm002_gate" />', xml)
        self.assertLess(xml.index('sgt002-miss-evidence'), xml.index('sgt002-bell-btn'))   # counted before the bell
        self.assertNotIn('x_yp_evidence_html', xml)        # no hard dependency on CRM-005
        s = (ROOT / 'static/src/scss/age_bell.scss').read_text()
        self.assertIn('.o_form_view:has(.sgt002-gate-on):has(.sgt002-miss-#{$f}) .o_field_widget[name="#{$f}"]', s)
        self.assertIn('.o_form_view:has(.sgt002-gate-on):not(:has(.sgt_yp_evbox img)) .sgt_yp_evbox', s)
        self.assertIn('.o_form_view:has(.sgt002-bell-btn:focus):not(:has(.sgt_yp_evbox img)) .sgt_yp_evbox', s)
        self.assertIn('.o_form_view:has(.sgt_yp_evbox):not(:has(.sgt_yp_evbox img)) .sgt002-miss.sgt002-miss-evidence { display: block; }', s)
        import re
        self.assertIsNone(re.search(r':has\([^()]*:has\(', s))   # :has() cannot be nested

    def test_scss_has_no_container_query(self):
        s = (ROOT / 'static/src/scss/age_bell.scss').read_text()
        self.assertNotIn('@container', s)
        for token in ('.sgt002-bell-bad', '.sgt002-bell-ok', '.sgt002-bar-total'):
            self.assertIn(token, s)


@unittest.skipUnless(VIEWS_CSV, 'pass odoo_views.csv of the production Scan to check the xpath targets')
class ScanTargets(unittest.TestCase):
    def test_xpath_targets_exist_in_stock_views(self):
        csv.field_size_limit(10 ** 9)
        rows = {r['id']: r['arch_db'] for r in csv.DictReader(open(VIEWS_CSV, encoding='utf-8-sig'))}
        kanban, lst = rows['1042'], rows['1045']
        self.assertIn('<progressbar', kanban)
        self.assertIn('name="rotting_days"', kanban)
        self.assertIn('name="stage_id"', kanban)
        self.assertIn('name="stage_id"', lst)


if __name__ == '__main__':
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        VIEWS_CSV = sys.argv.pop(1)
        ScanTargets = unittest.skipUnless(True, '')(ScanTargets)
        ScanTargets.__unittest_skip__ = False
    unittest.main(verbosity=1)
