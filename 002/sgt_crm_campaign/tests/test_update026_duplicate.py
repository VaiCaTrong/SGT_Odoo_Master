"""Update_026: system-wide Deal duplicate check (yp_* functions).

Runs the REAL code of models/duplicate.py and models/yp_utils.py against a small fake ORM:
  * who may see / update / create (Admin, Kinh doanh (MMC), Deal owner, everybody else);
  * phone / tax matching, Lost and archived Deals, 50-Deal cap, privacy of the answer;
  * rate limits, white lists, value checks, the two-cursor lock order.
NOT covered here (needs Odoo / Postgres): the SQL pre-filter on real data and two sessions racing.
The pre-filter and the lock were checked separately against a real PostgreSQL (see README_UPDATE_026_VI.md).
"""
import importlib
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOCK = {'now': datetime(2026, 11, 2, 9, 0, 0)}
WORLD = {}


class UserError(Exception):
    pass


class AccessError(UserError):
    pass


class ValidationError(UserError):
    pass


class FakeField:
    def __init__(self, type_='char', store=True, translate=False):
        self.type, self.store, self.translate = type_, store, translate


class Cursor:
    def __init__(self, world, name):
        self.world, self.name, self.rows = world, name, []

    def execute(self, sql, params=None):
        self.world.events.append((self.name, 'execute', sql, params))
        if '/* yp_scan */' in sql:                      # the scan reads every Deal page by page
            head = sql.split('SELECT', 1)[1].split('FROM', 1)[0]
            cols = [c.strip().strip('"') for c in head.split(',')]
            last, page = params
            rows = sorted((r for r in self.world.tables['crm.lead'].values() if r['id'] > last),
                          key=lambda r: r['id'])[:page]

            def raw(row, col):
                value = row.get(col)
                if col == 'active':
                    return bool(value)
                if isinstance(value, tuple):
                    return value[0]
                return None if value is False else value
            self.rows = [tuple(raw(r, c) for c in cols) for r in rows]
            self.world.scan_sql.append((sql, params))
        elif self.name != 'lock' and 'FROM "crm_lead"' in sql:
            self.world.sql_seen.append((sql, params))
            self.rows = [(i,) for i in self.world.candidate_ids()]

    def fetchall(self):
        return self.rows

    def savepoint(self):
        world = self.world

        class SP:
            def __enter__(self_):
                return self_

            def __exit__(self_, et, ev, tb):
                if et:
                    world.savepoint_rolled_back = True
                return False
        return SP()

    def __enter__(self):
        self.world.events.append((self.name, 'open'))
        return self

    def __exit__(self, et, ev, tb):
        self.world.events.append((self.name, 'rollback' if et else 'commit'))
        self.world.events.append((self.name, 'close'))
        return False


class Registry:
    def __init__(self, world):
        self.world, self.n = world, 0

    def cursor(self):
        names = ['lock', 'work', 'extra']
        cr = Cursor(self.world, names[min(self.n, 2)])
        self.n += 1
        return cr


class Env:
    def __init__(self, world, uid, context=None, cr=None):
        self.world, self.uid, self.context = world, uid, dict(context or {})
        self.cr = cr or Cursor(world, 'request')
        self.registry = Registry(world)
        self.user = types.SimpleNamespace(has_group=lambda g: g in world.groups_for(uid))

    def __getitem__(self, name):
        return Model(self, name)


class Model:
    def __init__(self, env, name, ids=(), su=False):
        self.env, self.name, self.ids, self.su = env, name, list(ids), su

    @property
    def world(self):
        return self.env.world

    @property
    def _fields(self):
        return self.world.fields[self.name]

    @property
    def _table(self):
        return self.name.replace('.', '_')

    def _new(self, ids=None, su=None):
        return Model(self.env, self.name, self.ids if ids is None else ids, self.su if su is None else su)

    def sudo(self):
        return self._new(su=True)

    def with_context(self, **kw):
        return self._new()

    def browse(self, ids):
        return self._new([ids] if isinstance(ids, int) else list(ids))

    def exists(self):
        return self._new([i for i in self.ids if i in self.world.tables[self.name]])

    def __bool__(self):
        return bool(self.ids)

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        return self._new([self.ids[i]])

    def __getattr__(self, attr):
        if attr in ('id',):
            return self.ids[0] if self.ids else False
        row = self.world.tables[self.name][self.ids[0]]
        return row.get(attr)

    def search(self, domain, order=None, limit=None):
        rows = [r for r in self.world.tables[self.name].values() if all(self._cond(r, c) for c in domain)]
        if order == 'create_date desc':
            rows.sort(key=lambda r: r['create_date'], reverse=True)
        else:
            rows.sort(key=lambda r: r['id'])
        ids = [r['id'] for r in rows][:limit] if limit else [r['id'] for r in rows]
        return self._new(ids)

    def _cond(self, row, cond):
        f, op, v = cond
        val = row.get(f)
        if self.name == 'hr.department' and op == 'child_of':
            top = set(v)
            cur = row
            while cur:
                if cur['id'] in top:
                    return True
                cur = self.world.tables['hr.department'].get(cur.get('parent'))
            return False
        if isinstance(val, tuple):
            val = val[0]
        if op == '=':
            return val == v
        if op == '>=':
            return val >= v
        raise AssertionError('operator not faked: %s' % op)

    def read(self, names):
        out = []
        for i in self.ids:
            row = self.world.tables[self.name][i]
            out.append({n: row.get(n, False) for n in names})
        return out

    def create(self, vals):
        w = self.world
        if self.env.uid in w.create_denied:
            raise AccessError('CRM-002: Bạn không được cấp quyền truy cập phễu này.')
        if w.create_error:
            raise w.create_error
        w.created.append({'uid': self.env.uid, 'su': self.su, 'vals': dict(vals)})
        w.next_id += 1
        row = {'id': w.next_id, 'active': True, 'create_uid': self.env.uid, 'create_date': CLOCK['now']}
        for k, v in vals.items():
            row[k] = (v, 'M%d' % v) if k.endswith('_id') and isinstance(v, int) else v
        w.tables['crm.lead'][w.next_id] = row
        return self._new([w.next_id])

    def write(self, vals):
        w = self.world
        if w.write_error:
            raise w.write_error
        w.writes.append({'uid': self.env.uid, 'su': self.su, 'ids': list(self.ids), 'vals': dict(vals)})
        for i in self.ids:
            w.tables['crm.lead'][i].update(vals)
        return True


OWN_DOCUMENTS = frozenset({'base.group_user', 'sales_team.group_sale_salesman'})
ALL_DOCUMENTS = OWN_DOCUMENTS | {'sales_team.group_sale_salesman_all_leads'}
SALES_ADMIN = ALL_DOCUMENTS | {'sales_team.group_sale_manager'}
SALES_NO = frozenset({'base.group_user'})                                   # Sales "No": internal user only
ROLE_ADMIN_ONLY = frozenset({'base.group_user', 'base.group_system'})       # Role Administrator, no Sales group
DEFAULT_GROUPS = OWN_DOCUMENTS

LEAD_FIELDS = (
    'id name active user_id partner_name x_company lost_reason_id probability stage_id sgt_crm002_funnel_id '
    'sgt_crm002_step sgt_crm002_sale_funnel_id sgt_crm002_sale_stage_id phone x_phone x_mobilephone '
    'x_yp_tax_code email_from create_uid create_date type tag_ids contact_name x_firstname x_lastname function '
    'website street street2 city state_id zip country_id x_yp_founded_year x_yp_employee_range x_type_contact '
    'x_fb_industry x_country referred x_yp_intro_en source_id x_image x_product_details x_yp_gallery_html '
    'x_yp_partners_html stage_id').split()


class World:
    def __init__(self):
        self.tables = {'crm.lead': {}, 'crm.stage': {
            1: {'id': 1, 'name': '1.Opportunity', 'sequence': 0},
            2: {'id': 2, 'name': '2.Connected', 'sequence': 1},
            8: {'id': 8, 'name': '3.Interacted', 'sequence': 2},
            3: {'id': 3, 'name': '4.Interesting', 'sequence': 4},
            6: {'id': 6, 'name': '5.Match Making', 'sequence': 5},
            4: {'id': 4, 'name': '6.Approved Match Making', 'sequence': 6},
        }, 'sgt.crm002.funnel': {
            2: {'id': 2, 'sequence': 20}, 6: {'id': 6, 'sequence': 60}, 7: {'id': 7, 'sequence': 70},
        }, 'sgt.crm002.funnel.stage': {
            1: {'id': 1, 'sequence': 10}, 2: {'id': 2, 'sequence': 10}, 20: {'id': 20, 'sequence': 20},
        }, 'hr.department': {
            1: {'id': 1, 'name': 'Administration', 'parent': None},
            2: {'id': 2, 'name': 'Kinh doanh (MMC)', 'parent': 1},
            3: {'id': 3, 'name': 'Công nghệ (CN)', 'parent': 1},
            4: {'id': 4, 'name': 'Sales Team A', 'parent': 2},       # child of Kinh doanh (MMC)
        }}
        self.fields = {
            'crm.lead': {n: FakeField('html' if n in ('description', 'x_yp_gallery_html') else 'char')
                         for n in LEAD_FIELDS + ['description']},
            'hr.department': {'name': FakeField()},
        }
        self.events, self.sql_seen, self.created, self.writes = [], [], [], []
        self.scan_sql = []
        self.create_denied, self.create_error, self.write_error = set(), None, None
        self.portal_uids = set()
        self.groups = {}                       # Update_027: uid -> set of group xml ids (default: Own Documents Only)
        self.savepoint_rolled_back = False
        self.next_id = 1000
        self.only_candidates = None

    def groups_for(self, uid):
        if uid in self.portal_uids:
            return set()
        return self.groups.get(uid, DEFAULT_GROUPS)

    def candidate_ids(self):
        # the SQL pre-filter may select MORE than the real matches; Python decides afterwards
        return list(self.only_candidates if self.only_candidates is not None else self.tables['crm.lead'])

    def add(self, id, name='Deal', owner=None, phone=False, desc=False, tax=False, active=True, lost=False,
            prob=None, **extra):
        row = {'id': id, 'name': name, 'active': active, 'phone': phone, 'description': desc,
               'x_yp_tax_code': tax, 'user_id': (owner, 'Owner %s' % owner) if owner else False,
               'lost_reason_id': (7, 'Too expensive') if lost else False,
               'probability': prob if prob is not None else (0 if lost else 10),
               'create_uid': 1, 'create_date': CLOCK['now'] - timedelta(days=3),
               'x_company': 'Cty %s' % id, 'partner_name': False,
               'sgt_crm002_funnel_id': (2, 'Inbound Pool'), 'sgt_crm002_step': 'data',
               'stage_id': (1, '1.Opportunity'), 'sgt_crm002_sale_funnel_id': False,
               'sgt_crm002_sale_stage_id': False, 'email_from': 'secret@example.com'}
        row.update(extra)
        self.tables['crm.lead'][id] = row
        return row


def load_module():
    saved = {k: sys.modules.get(k) for k in ('odoo', 'odoo.exceptions', 'sgt_crm_campaign', 'sgt_crm_campaign.models',
                                              'sgt_crm_campaign.models.duplicate', 'sgt_crm_campaign.models.yp_utils')}
    odoo = types.ModuleType('odoo')

    class AbstractModel:
        def __init__(self, env):
            self.env = env

        def _is_admin(self):
            return WORLD['admin']

        def _user_department_ids(self):
            return set(WORLD['depts'])

    odoo.models = types.SimpleNamespace(AbstractModel=AbstractModel)
    odoo.api = types.SimpleNamespace(model=lambda f: f, Environment=lambda cr, uid, ctx: Env(cr.world, uid, ctx, cr))
    odoo.fields = types.SimpleNamespace(Datetime=types.SimpleNamespace(now=lambda: CLOCK['now']))
    exc = types.ModuleType('odoo.exceptions')
    exc.AccessError, exc.UserError, exc.ValidationError = AccessError, UserError, ValidationError
    odoo.exceptions = exc
    pkg = types.ModuleType('sgt_crm_campaign')
    pkg.__path__ = [str(ROOT)]
    models = types.ModuleType('sgt_crm_campaign.models')
    models.__path__ = [str(ROOT / 'models')]
    sys.modules.update({'odoo': odoo, 'odoo.exceptions': exc, 'sgt_crm_campaign': pkg,
                        'sgt_crm_campaign.models': models})
    try:
        for k in ('sgt_crm_campaign.models.duplicate', 'sgt_crm_campaign.models.yp_utils'):
            sys.modules.pop(k, None)
        mod = importlib.import_module('sgt_crm_campaign.models.duplicate')
        utils = importlib.import_module('sgt_crm_campaign.models.yp_utils')
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod, utils


MOD, U = load_module()


class Base(unittest.TestCase):
    def setUp(self):
        CLOCK['now'] = datetime(2026, 11, 2, 9, 0, 0)
        self.w = World()
        WORLD.update(admin=False, depts=set())
        U.CHECK_LIMITER = U.SlidingLimiter(U.CHECK_LIMIT, clock=lambda: self.t)
        U.PROBE_LIMITER = U.SlidingLimiter(U.PROBE_LIMIT, clock=lambda: self.t)
        U.SCAN_LIMITER = U.SlidingLimiter(U.SCAN_LIMIT, U.SCAN_WINDOW_SECONDS, clock=lambda: self.t)
        self.t = 1000.0

    def svc(self, uid=22, admin=False, depts=()):
        """Service as seen by employee `uid`. depts = ids of the departments of that employee."""
        WORLD.update(admin=admin, depts=set(depts))
        return MOD.Crm002Duplicate(Env(self.w, uid))

    # the "outsider": different owner, no Kinh doanh department
    def outsider(self):
        return self.svc(uid=22, depts=(3,))

    def sales(self):
        return self.svc(uid=30, depts=(4,))       # Sales Team A is a child of Kinh doanh (MMC)


# ---------------------------------------------------------------------------------------------- helpers
class UtilsTests(Base):
    def test_phone_key_formats(self):
        for text in ('0912345678', '+84912345678', '+84 912 345 678', '0912.345.678', '(091) 234-5678', '912345678'):
            self.assertEqual(U.phone_key(text), '912345678', text)
        self.assertEqual(U.phone_key('12345'), '')
        self.assertEqual(U.phone_key(None), '')
        self.assertEqual(U.phone_key('0912345678'), U.phone_key(U.phone_key('0912345678')))   # idempotent

    def test_key_regex_shape(self):
        self.assertEqual(U.key_regex(['912345678']), '[ .()-]*'.join('912345678'))
        self.assertEqual(U.key_regex(['912345678', '988776655']).count('|'), 1)
        self.assertIn('&nbsp;', U.key_regex(['912345678'], html=True))
        with self.assertRaises(ValueError):
            U.key_regex(["1'; DROP TABLE crm_lead; --"])

    def test_key_regex_accepts_every_format_the_python_matcher_accepts(self):
        import re
        plain = re.compile(U.key_regex(['912345678']))
        for text in ('0912345678', '+84 912 345 678', '0912.345.678', '(091) 234-5678', '09 1234 5678', 'x912345678y'):
            self.assertTrue(plain.search(text), text)
            self.assertIn('912345678', U.phone_keys_in_text(text) or ['912345678'])
        self.assertFalse(plain.search('0912/345/678'))
        html = re.compile(U.key_regex(['912345678'], html=True), re.I)
        self.assertTrue(html.search('<p>0912&nbsp;345&NBSP;678</p>'))
        self.assertTrue(html.search('0912<b>345</b>678'))
        self.assertEqual(U.phone_keys_in_text('0912<b>345</b>678', html=True), ['912345678'])

    def test_numbers_inside_text_and_html(self):
        self.assertIn('912345678', U.phone_keys_in_text('Liên hệ: +84 912 345 678 (Mr A)'))
        self.assertEqual(U.phone_keys_in_text('<div style="width:912345678px">x</div>', html=True), [])
        self.assertEqual(U.phone_keys_in_text('<p>Tel&nbsp;0912 345 678</p>', html=True), ['912345678'])

    def test_clean_inputs(self):
        self.assertEqual(U.clean_inputs(['0912345678', '+84912345678'], 'mst-01.23')[:2], (['912345678'], 'MST0123'))
        for bad in (('x', ''), ([], ''), ([], '--'), (['1' * 41], ''), (list('0912345678' * 1) * 25, ''), ([5], ''), (['0912345678'], 5)):
            self.assertTrue(U.clean_inputs(*bad)[2], bad)

    def test_value_checks(self):
        ok = lambda v, allowed=U.WRITE_FIELDS: U.validate_values(v, allowed, set(LEAD_FIELDS))
        self.assertEqual(ok({'street': '', 'state_id': 5, 'country_id': 241, 'zip': '70000'}), '')
        self.assertTrue(ok({'state_id': '5'}))
        self.assertTrue(ok({'state_id': True}))
        self.assertTrue(ok({'name': ['x']}))
        self.assertTrue(ok({}))
        self.assertTrue(ok({'stage_id': 3}))
        self.assertEqual(ok({'tag_ids': [[6, 0, [1, 2]]], 'user_id': 5, 'type': 'opportunity'},
                            U.WRITE_FIELDS + U.CREATE_EXTRA_FIELDS), '')
        self.assertTrue(ok({'tag_ids': [[3, 5]]}, U.WRITE_FIELDS + U.CREATE_EXTRA_FIELDS))

    def test_limiter(self):
        lim = U.SlidingLimiter(3, 60, clock=lambda: self.t)
        self.assertEqual([lim.hit(1) for _ in range(3)], [0, 0, 0])
        self.assertEqual(lim.hit(1), 60)
        self.assertEqual(lim.hit(2), 0)                # another user is unaffected
        self.t += 59
        self.assertEqual(lim.hit(1), 1)
        self.t += 1.5
        self.assertEqual(lim.hit(1), 0)


# ---------------------------------------------------------------------------------------------- bài 1, 2, 3, 12, 13
class CheckTests(Base):
    def test_outsider_sees_foreign_deal_but_cannot_update_it(self):             # bài 1
        self.w.add(11, 'X', owner=5, phone='0912345678')
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertTrue(res['ok'])
        (m,) = res['matches']
        self.assertEqual((m['id'], m['can_update'], m['is_owner'], m['phone'], m['tax']), (11, False, False, True, False))
        self.assertFalse(res['can_update'])
        self.assertEqual((m['funnel'], m['step'], m['stage'], m['owner_name'], m['company']),
                         ('Inbound Pool', 'data', '1.Opportunity', 'Owner 5', 'Cty 11'))

    def test_answer_never_contains_contact_data(self):
        self.w.add(11, 'X', owner=5, phone='0912345678', description='<p>note 0912345678</p>')
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        allowed = {'id', 'name', 'company', 'owner_id', 'owner_name', 'phone', 'tax', 'funnel_id', 'funnel', 'step',
                   'stage', 'stage_seq', 'sale_funnel', 'sale_funnel_seq', 'sale_stage', 'sale_stage_seq', 'state',
                   'is_owner', 'can_update'}
        self.assertEqual(set(res['matches'][0]), allowed)
        self.assertNotIn('secret@example.com', repr(res))
        self.assertNotIn('0912345678', repr(res))

    def test_lost_and_archived_are_returned_with_state(self):                    # bài 2
        self.w.add(1, 'active', owner=5, phone='0912345678')
        self.w.add(2, 'lost', owner=5, phone='0912345678', active=False, lost=True)
        self.w.add(3, 'archived', owner=5, phone='0912345678', active=False, lost=False, prob=20)
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertEqual([(m['id'], m['state']) for m in res['matches']], [(1, 'active'), (2, 'lost'), (3, 'archived')])

    def test_every_phone_format_and_field_matches(self):                        # bài 3
        self.w.add(1, phone='0912345678')
        self.w.add(2, phone='+84912345678')
        self.w.add(3, phone='+84 912 345 678')
        self.w.add(4, phone=False, desc='<p>Gọi&nbsp;0912.345.678 nhé</p>')
        self.w.add(5, name='Công ty 091 234 5678', phone=False)
        self.w.add(6, phone=False, **{'x_phone': '(091) 234-5678'})
        self.w.add(7, phone='0987654321')                                            # other number
        self.w.add(8, phone=False, desc='<div style="width:912345678px">logo</div>')   # digits inside a tag
        res = self.outsider().yp_duplicate_check(['0912345678'], '')
        self.assertEqual([m['id'] for m in res['matches']], [1, 2, 3, 4, 5, 6])

    def test_tax_only_and_phone_only(self):                                        # bài 3
        self.w.add(1, phone='0911111111', tax='0123456789-001')
        self.w.add(2, phone='0912345678', tax='999')
        res = self.outsider().yp_duplicate_check([], '0123456789001')
        self.assertEqual([(m['id'], m['phone'], m['tax']) for m in res['matches']], [(1, False, True)])
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertEqual([(m['id'], m['phone'], m['tax']) for m in res['matches']], [(2, True, False)])

    def test_many_duplicates_in_many_funnels(self):                              # bài 13
        self.w.add(1, owner=5, phone='0912345678', **{'sgt_crm002_funnel_id': (1, 'Outbound Hunter')})
        self.w.add(2, owner=6, phone='0912345678', **{'sgt_crm002_funnel_id': (2, 'Inbound Pool')})
        self.w.add(3, owner=False, phone='0912345678', active=False, lost=True)
        self.w.add(4, owner=7, phone='0912345678', active=False)
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertEqual(len(res['matches']), 4)
        self.assertFalse(res['truncated'])

    def test_more_than_fifty_is_truncated(self):
        for i in range(1, 56):
            self.w.add(i, owner=5, phone='0912345678')
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertEqual((len(res['matches']), res['truncated']), (50, True))

    def test_owner_of_a_duplicate_may_update_only_that_one(self):                # bài 12 (check part)
        self.w.add(1, owner=22, phone='0912345678')
        self.w.add(2, owner=5, phone='0912345678')
        res = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertEqual([(m['id'], m['is_owner'], m['can_update']) for m in res['matches']],
                         [(1, True, True), (2, False, False)])
        self.assertTrue(res['can_update'])

    def test_sales_department_and_admin_may_update_everything(self):
        self.w.add(1, owner=5, phone='0912345678')
        res = self.sales().yp_duplicate_check(['912345678'], '')
        self.assertTrue(res['is_sales'] and res['matches'][0]['can_update'])
        res = self.svc(uid=1, admin=True).yp_duplicate_check(['912345678'], '')
        self.assertTrue(res['is_admin'] and res['matches'][0]['can_update'])

    def test_portal_user_is_refused_by_all_four_functions(self):
        self.w.add(11, 'X', owner=5, phone='0912345678')
        self.w.portal_uids = {77}
        s = self.svc(uid=77)
        answers = [s.yp_duplicate_check(['912345678'], ''), s.yp_read_lead(11, ['name']),
                   s.yp_update_lead(11, {'name': 'x'}), s.yp_create_lead({'name': 'x', 'phone': '0912345678'}, [], '')]
        self.assertEqual([a['code'] for a in answers], ['forbidden'] * 4)
        self.assertEqual((self.w.writes, self.w.created, self.w.sql_seen, self.w.events), ([], [], [], []))

    def test_department_outside_kinh_doanh_is_not_sales(self):
        res = self.svc(depts=(3, 1)).yp_duplicate_check(['912345678'], '')
        self.assertFalse(res['is_sales'])

    def test_missing_department_means_nobody_is_sales(self):
        del self.w.tables['hr.department'][2], self.w.tables['hr.department'][4]
        self.assertFalse(self.svc(depts=(4,)).yp_duplicate_check(['912345678'], '')['is_sales'])

    def test_database_without_mobile_or_tax_field_still_works(self):
        for gone in ('mobile', 'x_yp_tax_code'):
            self.w.fields['crm.lead'].pop(gone, None)
        self.w.add(1, phone='0912345678')
        self.assertEqual(len(self.outsider().yp_duplicate_check(['912345678'], 'ABC')['matches']), 1)
        sql, params = self.w.sql_seen[-1]
        self.assertNotIn('x_yp_tax_code', sql)
        self.assertNotIn('"mobile"', sql)

    def test_prefilter_sql_has_no_user_data_inline(self):
        self.w.add(1, phone='0912345678')
        self.outsider().yp_duplicate_check(['912345678'], 'MST9')
        sql, params = self.w.sql_seen[-1]
        self.assertNotIn('912345678', sql)
        self.assertNotIn('MST9', sql)
        self.assertEqual(sql.count('%s'), len(params))
        self.assertEqual(params[0], U.key_regex(['912345678']))                 # phone / name columns
        self.assertEqual(params[3], U.key_regex(['912345678'], html=True))     # description (HTML)
        self.assertEqual(params[-1], ['MST9'])
        self.assertIn('"description" ~* %s', sql)
        self.assertIn('"phone" ~ %s', sql)

    def test_bad_input_and_rate_limit(self):                                       # bài 6 (check part)
        s = self.outsider()
        self.assertEqual(s.yp_duplicate_check([], '')['code'], 'invalid')
        self.assertEqual(s.yp_duplicate_check('0912345678', '')['code'], 'invalid')
        results = [s.yp_duplicate_check(['912345678'], '') for _ in range(31)]
        self.assertTrue(all(r['ok'] for r in results[:30]))
        self.assertEqual((results[30]['code'], results[30]['retry_after']), ('rate_limit', 60))
        self.t += 61
        self.assertTrue(s.yp_duplicate_check(['912345678'], '')['ok'])


# ---------------------------------------------------------------------------------------------- bài 4, 8, 10
class ReadWriteTests(Base):
    def setUp(self):
        super().setUp()
        self.w.add(11, 'Foreign', owner=5, phone='0912345678')
        self.w.add(12, 'Mine', owner=22, phone='0988888888')
        self.w.add(13, 'Nobody', owner=False, phone='0977777777')

    def test_outsider_is_refused_alike_for_foreign_and_missing_ids(self):         # bài 4
        s = self.outsider()
        for lid in (11, 13, 99999):
            self.assertEqual(s.yp_read_lead(lid, ['name'])['code'], 'forbidden', lid)
            self.assertEqual(s.yp_update_lead(lid, {'name': 'x'})['code'], 'forbidden', lid)
        self.assertEqual(self.w.writes, [])

    def test_owner_reads_and_updates_only_his_deal(self):                         # bài 4, 12
        s = self.outsider()
        self.assertEqual(s.yp_read_lead(12, ['name', 'sgt_crm002_step'])['values'], {'name': 'Mine', 'sgt_crm002_step': 'data'})
        self.assertEqual(s.yp_update_lead(12, {'name': 'Mine 2'}), {'ok': True, 'id': 12})
        self.assertEqual(self.w.tables['crm.lead'][12]['name'], 'Mine 2')
        self.assertEqual(s.yp_update_lead(11, {'name': 'hack'})['code'], 'forbidden')

    def test_sales_and_admin_update_foreign_deals_and_get_not_found(self):          # bài 4
        for s in (self.sales(), self.svc(uid=1, admin=True)):
            self.assertTrue(s.yp_update_lead(11, {'name': 'by ' + str(s.env.uid)})['ok'])
            self.assertEqual(s.yp_update_lead(99999, {'name': 'x'})['code'], 'not_found')
            self.assertEqual(s.yp_read_lead(99999, ['name'])['code'], 'not_found')
            self.assertTrue(s.yp_read_lead(13, ['name'])['ok'])

    def test_write_keeps_real_user_and_uses_a_savepoint(self):                       # bài 8
        self.sales().yp_update_lead(11, {'name': 'n'})
        (w,) = self.w.writes
        self.assertEqual((w['uid'], w['su']), (30, True))        # sudo keeps env.uid: Chatter names the real person
        self.w.write_error = ValidationError('rule')
        res = self.sales().yp_update_lead(11, {'name': 'n2'})
        self.assertEqual((res['code'], res['message']), ('invalid', 'rule'))
        self.assertTrue(self.w.savepoint_rolled_back)
        self.w.write_error = AccessError('nope')
        self.assertEqual(self.sales().yp_update_lead(11, {'name': 'n3'})['code'], 'forbidden')

    def test_forbidden_keys_are_rejected_and_nothing_is_written(self):             # bài 4
        s = self.svc(uid=1, admin=True)
        for key, val in (('stage_id', 3), ('user_id', 9), ('tag_ids', [[6, 0, [1]]]), ('sgt_crm002_funnel_id', 1),
                         ('sgt_crm002_step', 'potential'), ('sgt_crm002_sale_funnel_id', 1),
                         ('sgt_crm002_sale_stage_id', 1), ('active', False), ('create_date', 'x'), ('write_date', 'x'),
                         ('date_closed', 'x')):
            res = s.yp_update_lead(11, {'name': 'ok', key: val})
            self.assertEqual(res['code'], 'invalid', key)
            self.assertIn(key, res['message'])
        self.assertEqual(self.w.writes, [])
        self.assertEqual(s.yp_read_lead(11, ['stage_id'])['code'], 'invalid')
        self.assertTrue(s.yp_read_lead(11, ['name', 'email_from', 'x_yp_gallery_html'])['ok'])
        self.assertEqual(s.yp_read_lead(11, ['name', 'probability'])['code'], 'invalid')

    def test_address_fields(self):                                                   # bài 10
        s = self.sales()
        self.assertTrue(s.yp_update_lead(11, {'street': '', 'street2': 'P. Bến Nghé', 'city': 'Quận 1',
                                              'state_id': 20, 'zip': '70000', 'country_id': 241})['ok'])
        row = self.w.tables['crm.lead'][11]
        self.assertEqual((row['street'], row['city']), ('', 'Quận 1'))
        self.assertTrue(s.yp_update_lead(11, {'state_id': False})['ok'])
        self.assertEqual(s.yp_update_lead(11, {'state_id': '20'})['code'], 'invalid')
        vals = s.yp_read_lead(11, ['street', 'street2', 'city', 'state_id', 'zip', 'country_id'])['values']
        self.assertEqual(set(vals), {'street', 'street2', 'city', 'state_id', 'zip', 'country_id'})

    def test_bad_arguments(self):
        s = self.sales()
        for lid in (True, 0, -1, '11', None, 1.5):
            self.assertEqual(s.yp_read_lead(lid, ['name'])['code'], 'invalid', lid)
        for names in ([], 'name', None, [1], ['name'] * 81):
            self.assertEqual(s.yp_read_lead(11, names)['code'], 'invalid', names)
        self.assertEqual(s.yp_update_lead(11, {})['code'], 'invalid')
        self.assertEqual(s.yp_update_lead(11, 'name')['code'], 'invalid')


# ---------------------------------------------------------------------------------------------- bài 1, 5, 6, 7, 11, 12
class CreateTests(Base):
    VALS = {'name': 'New', 'phone': '0912345678', 'type': 'opportunity', 'user_id': 22,
            'sgt_crm002_funnel_id': 2, 'tag_ids': [[6, 0, [3]]], 'street2': 'P. 1', 'state_id': 20, 'country_id': 241}

    def create(self, svc, vals=None, keys=('912345678',), tax='', force=False):
        return svc.yp_create_lead(dict(vals or self.VALS), list(keys), tax, force)

    def test_creates_with_the_employees_own_rights(self):                          # bài 7
        res = self.create(self.outsider())
        self.assertTrue(res['ok'])
        (c,) = self.w.created
        self.assertEqual((c['uid'], c['su']), (22, False))
        self.assertEqual(c['vals']['sgt_crm002_funnel_id'], 2)
        self.assertEqual(self.w.tables['crm.lead'][res['id']]['create_uid'], 22)

    def test_lock_comes_first_then_work_cursor_then_release(self):                  # bài 5 (order part)
        self.create(self.outsider(), tax='mst-9')
        ev = [e for e in self.w.events if e[0] in ('lock', 'work')]
        kinds = [(e[0], e[1]) for e in ev]
        self.assertEqual(kinds[0], ('lock', 'open'))
        self.assertLess(kinds.index(('lock', 'open')), kinds.index(('work', 'open')))
        self.assertLess(kinds.index(('work', 'close')), kinds.index(('lock', 'close')))
        sqls = [e[2] for e in ev if e[0] == 'lock' and e[1] == 'execute']
        self.assertIn('lock_timeout', sqls[0])
        names = [e[3][0] for e in ev if e[0] == 'lock' and e[1] == 'execute' and 'pg_advisory_xact_lock' in e[2]]
        self.assertEqual(names, sorted(names))
        self.assertEqual(names, ['yp-phone-912345678', 'yp-tax-MST9'])
        first_work_exec = next(i for i, e in enumerate(ev) if e[:2] == ('work', 'execute'))
        last_lock_exec = max(i for i, e in enumerate(ev) if e[:2] == ('lock', 'execute'))
        self.assertLess(last_lock_exec, first_work_exec)      # work snapshot starts AFTER every lock is granted

    def test_duplicate_blocks_creation_for_everybody_but_force_admin(self):         # bài 1, 11, 12
        self.w.add(11, 'X', owner=5, phone='0912345678')
        res = self.create(self.outsider())
        self.assertEqual((res['ok'], res['code'], res['can_update']), (False, 'duplicate', False))
        self.assertEqual(res['matches'][0]['id'], 11)
        self.assertEqual(self.w.created, [])
        for svc in (self.outsider(), self.sales(), self.svc(uid=1, admin=True)):
            self.assertEqual(self.create(svc)['code'], 'duplicate')                 # force defaults to False
        self.assertEqual(self.create(self.outsider(), force=True)['code'], 'duplicate')   # not admin
        self.assertEqual(self.create(self.sales(), force=True)['code'], 'duplicate')
        self.assertEqual(self.w.created, [])
        for loose in ('true', 1, 'True', None, [True]):
            self.assertEqual(self.create(self.svc(uid=1, admin=True), force=loose)['code'], 'duplicate', loose)
        self.assertTrue(self.create(self.svc(uid=1, admin=True), force=True)['ok'])
        self.assertEqual(len(self.w.created), 1)

    def test_owner_of_the_duplicate_is_blocked_too(self):                            # bài 12
        self.w.add(11, 'Mine', owner=22, phone='0912345678')
        res = self.create(self.outsider())
        self.assertEqual(res['code'], 'duplicate')
        self.assertEqual((res['matches'][0]['is_owner'], res['matches'][0]['can_update']), (True, True))
        self.assertTrue(res['can_update'])

    def test_caller_cannot_dodge_the_check_by_sending_empty_keys(self):
        self.w.add(11, 'X', owner=5, phone='0912345678')
        res = self.create(self.outsider(), keys=())
        self.assertEqual(res['code'], 'duplicate')
        res = self.create(self.outsider(), keys=('0999999999',))
        self.assertEqual(res['code'], 'duplicate')        # the Deal's own phone is checked as well
        ev = [e for e in self.w.events if e[0] == 'lock' and 'pg_advisory_xact_lock' in str(e[2:3])]
        self.assertIn(['yp-phone-912345678'], [e[3] for e in ev])

    def test_no_phone_and_no_tax_is_refused(self):
        res = self.outsider().yp_create_lead({'name': 'x', 'type': 'opportunity'}, [], '')
        self.assertEqual(res['code'], 'invalid')
        self.assertEqual(self.outsider().yp_create_lead(dict(self.VALS), 'x', '')['code'], 'invalid')

    def test_fields_outside_the_lists_are_refused(self):
        for bad in ({'stage_id': 4}, {'active': False}, {'sgt_crm002_step': 'potential'}, {'create_uid': 1}, {'probability': 100}):
            res = self.outsider().yp_create_lead({**self.VALS, **bad}, ['912345678'], '')
            self.assertEqual(res['code'], 'invalid', bad)
        self.assertEqual(self.w.created, [])

    def test_create_rate_limit_user_and_admin(self):                                 # bài 6
        def old(i, uid, secs):
            self.w.add(500 + i, owner=uid, phone='0900000%03d' % i, create_uid=uid,
                       create_date=CLOCK['now'] - timedelta(seconds=secs))
        for i in range(5):
            old(i, 22, 10 + i * 10)                      # 5 Deals by user 22 in the last minute (10..50 s ago)
        res = self.create(self.outsider())
        self.assertEqual((res['code'], res['retry_after']), ('rate_limit', 10))      # oldest leaves the window in 10 s
        self.assertEqual(self.w.created, [])
        CLOCK['now'] += timedelta(seconds=11)
        self.assertTrue(self.create(self.outsider())['ok'])
        CLOCK['now'] = datetime(2026, 11, 2, 9, 0, 0)
        for i in range(5, 10):
            old(i, 1, 5 + i)
        self.assertTrue(self.create(self.svc(uid=1, admin=True), vals={**self.VALS, 'phone': '0966666666'}, keys=('966666666',))['ok'])
        for i in range(10, 14):                          # 6 + 4 = 10 Deals by the Admin in the last minute
            old(i, 1, 3)
        res = self.create(self.svc(uid=1, admin=True), vals={**self.VALS, 'phone': '0955555555'}, keys=('955555555',))
        self.assertEqual(res['code'], 'rate_limit')

    def test_busy_lock_asks_to_retry(self):
        from psycopg2.errors import LockNotAvailable
        svc = self.outsider()
        orig = Cursor.execute

        def boom(cr, sql, params=None):
            if 'pg_advisory_xact_lock' in sql:
                raise LockNotAvailable('timeout')
            return orig(cr, sql, params)
        Cursor.execute = boom
        try:
            res = self.create(svc)
        finally:
            Cursor.execute = orig
        self.assertEqual((res['code'], res['retry_after'], res['reason']), ('rate_limit', 3, 'busy'))
        self.assertEqual(self.w.created, [])

    def test_funnel_permission_error_is_reported_not_raised(self):
        self.w.create_denied = {22}
        self.assertEqual(self.create(self.outsider())['code'], 'forbidden')
        self.w.create_denied = set()
        self.w.create_error = ValidationError('Phễu tiếp nhận không hợp lệ')
        res = self.create(self.outsider())
        self.assertEqual((res['code'], res['message']), ('invalid', 'Phễu tiếp nhận không hợp lệ'))


# ---------------------------------------------------------------------------------------------- source contracts
# ---------------------------------------------------------------------------------------------- Việc A
class OrderTests(Base):
    """yp_duplicate_check: column order numbers, furthest first, cut after sorting, total."""

    def deal(self, lead_id, stage=1, **kw):
        kw.setdefault('stage_id', (stage, self.w.tables['crm.stage'][stage]['name']))
        return self.w.add(lead_id, phone='0912345678', **kw)

    def check(self):
        return self.outsider().yp_duplicate_check(['912345678'], '')

    def test_matches_carry_the_column_order_numbers(self):
        self.deal(1, stage=4, sgt_crm002_sale_funnel_id=(6, 'New'), sgt_crm002_sale_stage_id=(20, '2.Quote'))
        self.deal(2, stage=3)
        by_id = {m['id']: m for m in self.check()['matches']}
        self.assertEqual((by_id[1]['stage_seq'], by_id[1]['sale_funnel_seq'], by_id[1]['sale_stage_seq']), (6, 60, 20))
        self.assertEqual((by_id[2]['stage_seq'], by_id[2]['sale_funnel_seq'], by_id[2]['sale_stage_seq']),
                         (4, None, None))

    def test_deal_without_stage_has_null_stage_seq(self):
        self.deal(1, stage_id=False)
        (m,) = self.check()['matches']
        self.assertIsNone(m['stage_seq'])

    def test_furthest_first_active_before_lost_and_archived(self):
        self.deal(101, stage=1, active=False, prob=10)                                # archived, stage 1
        self.deal(102, stage=4, active=False, lost=True)                              # lost, stage 6
        self.deal(103, stage_id=False, sgt_crm002_step='potential')                   # data funnel only
        self.deal(104, stage=6)                                                       # stage 5
        self.deal(105, stage=4)                                                       # stage 6
        self.deal(107, stage=1, sgt_crm002_sale_funnel_id=(6, 'New'), sgt_crm002_sale_stage_id=(1, '1.Data'))
        self.deal(108, stage=1, sgt_crm002_sale_funnel_id=(7, 'Renew'), sgt_crm002_sale_stage_id=(2, '1.Data'))
        order = [m['id'] for m in self.check()['matches']]
        self.assertEqual(order, [108, 107, 105, 104, 103, 102, 101])

    def test_data_funnel_step_ranks_potential_verified_data(self):
        for i, step in enumerate(('data', 'potential', 'verified'), start=1):
            self.deal(i, stage_id=False, sgt_crm002_step=step)
        self.assertEqual([m['id'] for m in self.check()['matches']], [2, 3, 1])

    def test_same_place_older_deal_first(self):
        self.deal(9, stage=3)
        self.deal(4, stage=3)
        self.assertEqual([m['id'] for m in self.check()['matches']], [4, 9])

    def test_cut_to_fifty_keeps_the_furthest_not_the_first(self):
        for i in range(1, 121):
            self.deal(i, stage=1, owner=5)
        self.deal(500, stage=4, owner=5)                      # high id, but the furthest
        res = self.check()
        self.assertEqual((len(res['matches']), res['total'], res['truncated']), (50, 121, True))
        self.assertEqual(res['matches'][0]['id'], 500)

    def test_total_equals_matches_when_not_truncated(self):
        self.deal(1)
        self.deal(2)
        res = self.check()
        self.assertEqual((res['total'], res['truncated'], len(res['matches'])), (2, False, 2))

    def test_active_deal_in_a_mark_lost_stage_counts_as_lost(self):
        self.w.tables['crm.stage'][9] = {'id': 9, 'name': '8.Mark Lost', 'sequence': 7}
        self.deal(1, stage=1)
        self.deal(2, stage=9)                                 # still active=True, but parked in Mark Lost
        res = self.check()
        self.assertEqual([(m['id'], m['state']) for m in res['matches']], [(1, 'active'), (2, 'lost')])

    def test_duplicate_answer_of_create_has_total(self):
        self.deal(1)
        res = self.outsider().yp_create_lead({'name': 'N', 'phone': '0912345678'}, ['912345678'], '')
        self.assertEqual((res['code'], res['total']), ('duplicate', 1))


# ---------------------------------------------------------------------------------------------- hàm quét S1-S10
class ScanTests(Base):
    def admin(self, uid=1):
        return self.svc(uid=uid, admin=True)

    def scan(self, svc=None, **opts):
        return (svc or self.admin()).yp_duplicate_scan(opts)

    def deal(self, lead_id, phone='', stage=1, **kw):
        kw.setdefault('stage_id', (stage, self.w.tables['crm.stage'][stage]['name']))
        return self.w.add(lead_id, phone=phone, **kw)

    def ids(self, group):
        return [m['id'] for m in group['members']]

    def scan_all(self, limit):
        """Scan the whole CRM batch by batch the way the extension does."""
        U.SCAN_LIMITER = U.SlidingLimiter(10000, U.SCAN_WINDOW_SECONDS, clock=lambda: self.t)
        groups, after, calls = [], 0, 0
        while True:
            res = self.scan(after_id=after, limit=limit)
            self.assertTrue(res['ok'], res)
            groups.extend(res['groups'])
            calls += 1
            if res['done']:
                return groups, calls
            self.assertGreater(res['next_after_id'], after)
            after = res['next_after_id']

    # S1 ------------------------------------------------------------------------------------------------
    def test_s1_only_admin_and_nothing_is_read_for_anybody_else(self):
        self.deal(1, '0912345678')
        self.deal(2, '0912345678')
        for svc in (self.outsider(), self.sales(), self.svc(uid=40, depts=())):
            for opts in ({'probe': True}, {}, {'limit': 999999}):
                res = svc.yp_duplicate_scan(opts)
                self.assertEqual(res, {'ok': False, 'code': 'forbidden', 'message': res.get('message')})
        self.assertEqual(self.w.events, [])                       # not a single query
        self.assertEqual(self.w.scan_sql, [])
        portal = self.svc(uid=77)
        self.w.portal_uids.add(77)
        self.assertEqual(portal.yp_duplicate_scan({'probe': True})['code'], 'forbidden')

    def test_s1_admin_probe_asks_nothing_from_the_database(self):
        res = self.scan(probe=True)
        self.assertEqual(res, {'ok': True, 'is_admin': True, 'probe': True, 'max_batch': 2000})
        self.assertEqual(self.w.events, [])

    def test_s1_limit_is_capped_at_2000(self):
        for i in range(1, 2106):
            self.deal(i, '09%08d' % i if i > 2100 else '')       # almost no keys: cheap
        res = self.scan(limit=999999)
        self.assertEqual((res['scanned'], res['to_id'], res['next_after_id'], res['done']), (2000, 2000, 2000, False))
        res = self.scan(after_id=2000, limit=999999)
        self.assertEqual((res['scanned'], res['done'], res['next_after_id']), (105, True, None))

    # S2 ------------------------------------------------------------------------------------------------
    def test_s2_one_group_parent_first_then_by_distance_then_inactive_last(self):
        P = '0912345678'
        self.deal(201, P, stage=4, owner=5)                                          # the furthest: 6.Approved MM
        self.deal(202, P, stage=1, sgt_crm002_step='potential', owner=6)             # data funnel potential
        self.deal(203, P, stage=4, active=False, lost=True, owner=7)                 # lost, even at stage 6
        self.deal(204, P, stage=1, active=False, prob=10, owner=8)                   # archived
        self.deal(205, P, stage=3, owner=9)                                          # 4.Interesting
        res = self.scan()
        self.assertEqual(len(res['groups']), 1)
        g = res['groups'][0]
        self.assertEqual(self.ids(g), [201, 205, 202, 203, 204])
        self.assertEqual([m['state'] for m in g['members']], ['active'] * 3 + ['lost', 'archived'])
        self.assertEqual((g['size'], g['truncated']), (5, False))
        self.assertEqual(g['members'][0]['stage_seq'], 6)
        self.assertEqual((res['scanned'], res['from_id'], res['to_id'], res['done'], res['next_after_id']),
                         (3, 201, 205, True, None))

    def test_s2_members_have_the_check_format_and_no_contact_data(self):
        self.deal(1, '0912345678', owner=5)
        self.deal(2, '0912345678', owner=6)
        res = self.scan()
        allowed = {'id', 'name', 'company', 'owner_id', 'owner_name', 'phone', 'tax', 'funnel_id', 'funnel', 'step',
                   'stage', 'stage_seq', 'sale_funnel', 'sale_funnel_seq', 'sale_stage', 'sale_stage_seq', 'state',
                   'is_owner', 'can_update'}
        for m in res['groups'][0]['members']:
            self.assertEqual(set(m), allowed)
        check = self.outsider().yp_duplicate_check(['912345678'], '')
        self.assertEqual(set(check['matches'][0]), allowed)
        self.assertNotIn('secret@example.com', repr(res))
        self.assertNotIn('0912345678', repr(res))
        self.assertEqual(set(res), {'ok', 'is_admin', 'max_batch', 'scanned', 'from_id', 'to_id',
                                    'next_after_id', 'done', 'groups'})

    # S3 ------------------------------------------------------------------------------------------------
    def test_s3_batches_never_repeat_a_group_and_groups_stay_complete(self):
        # pairs and triples spread over many ids so that batches of 3 cut straight through them
        self.deal(1, '0911111111')
        self.deal(2, '0922222222')
        self.deal(3, '0933333333')
        self.deal(4, '0944444444')
        self.deal(5, '0911111111')                      # joins 1 (other batch)
        self.deal(6, '0955555555')
        self.deal(7, '0922222222')                      # joins 2
        self.deal(8, '0922222222')                      # joins 2 again
        self.deal(9, '0933333333', active=False, lost=True)   # lost member of 3's group
        self.deal(10, '0966666666')
        self.deal(11, '0966666666')
        self.deal(12, '0977777777', active=False, lost=True)   # only lost Deals: never a group
        self.deal(13, '0977777777', active=False, lost=True)
        whole, _ = self.scan_all(limit=2000)
        expected = sorted(sorted(self.ids(g)) for g in whole)
        self.assertEqual(expected, [[1, 5], [2, 7, 8], [3, 9], [10, 11]])
        for limit in (1, 2, 3, 5, 7):
            groups, calls = self.scan_all(limit=limit)
            self.assertGreater(calls, 1)
            self.assertEqual(sorted(sorted(self.ids(g)) for g in groups), expected, limit)

    def test_s3_group_is_returned_by_the_batch_holding_its_smallest_active_id(self):
        self.deal(1, '0911111111')
        self.deal(5, '0911111111')
        self.deal(6, '0922222222')
        first = self.scan(after_id=0, limit=1)                 # batch = Deal 1 only
        self.assertEqual([self.ids(g) for g in first['groups']], [[1, 5]])
        second = self.scan(after_id=first['next_after_id'], limit=1)     # batch = Deal 5, a member of the same group
        self.assertEqual(second['groups'], [])

    def test_s3_cursor_past_the_end_is_done(self):
        self.deal(1, '0911111111')
        self.deal(2, '0911111111')
        res = self.scan(after_id=2)
        self.assertEqual((res['scanned'], res['from_id'], res['to_id'], res['next_after_id'], res['done'],
                          res['groups']), (0, None, None, None, True, []))

    def test_s3_every_deal_is_read_once_in_pages(self):
        for i in range(1, 2106):
            self.deal(i)
        self.scan(limit=5)
        self.assertEqual(len(self.w.scan_sql), 3)              # 2105 Deals, 1000 per page, whatever the batch size
        for sql, params in self.w.scan_sql:
            self.assertEqual(sql.count('%s'), 2)
            self.assertTrue(all(isinstance(p, int) for p in params))

    # S4 ------------------------------------------------------------------------------------------------
    def test_s4_chain_over_phone_then_tax_is_one_group(self):
        self.deal(1, '0911111111')                                        # A
        self.deal(2, '0911111111', x_yp_tax_code='0312345678')            # B: phone with A, tax with C
        self.deal(3, '0988888888', x_yp_tax_code='031.234.5678')          # C
        res = self.scan()
        self.assertEqual([self.ids(g) for g in res['groups']], [[1, 2, 3]])
        a, b, c = {m['id']: m for m in res['groups'][0]['members']}.values()
        self.assertEqual((a['phone'], a['tax']), (True, False))
        self.assertEqual((b['phone'], b['tax']), (True, True))
        self.assertEqual((c['phone'], c['tax']), (False, True))

    def test_s4_same_phone_in_two_batches_is_still_one_group(self):
        self.deal(1, '0911111111')
        for i in range(2, 8):
            self.deal(i)
        self.deal(8, '+84 911 111 111')
        groups, calls = self.scan_all(limit=3)
        self.assertGreater(calls, 1)
        self.assertEqual([self.ids(g) for g in groups], [[1, 8]])

    # S5 ------------------------------------------------------------------------------------------------
    def test_s5_tax_only_and_phone_only_groups(self):
        self.deal(1, '0911111111', x_yp_tax_code='0100000001')
        self.deal(2, '0922222222', x_yp_tax_code='0100000001')            # same tax, different phone
        self.deal(3, '0933333333', x_yp_tax_code='0100000009')
        self.deal(4, '0933333333', x_yp_tax_code='0100000008')            # same phone, different tax
        res = self.scan()
        self.assertEqual(sorted(self.ids(g) for g in res['groups']), [[1, 2], [3, 4]])
        tax_group = next(g for g in res['groups'] if self.ids(g) == [1, 2])
        self.assertTrue(all(m['tax'] and not m['phone'] for m in tax_group['members']))
        phone_group = next(g for g in res['groups'] if self.ids(g) == [3, 4])
        self.assertTrue(all(m['phone'] and not m['tax'] for m in phone_group['members']))

    def test_s5_numbers_in_notes_and_names_count_like_in_the_check(self):
        self.deal(1, description='<p>Gọi 0912.345.678</p>')
        self.deal(2, name='Cty B 0912 345 678')
        self.deal(3, description='<a href="tel:0912345678x">link</a>')   # digits in a tag attribute: not a phone
        res = self.scan()
        self.assertEqual([self.ids(g) for g in res['groups']], [[1, 2]])

    # S6 ------------------------------------------------------------------------------------------------
    def test_s6_big_group_is_cut_to_fifty_after_sorting(self):
        for i in range(1, 121):
            self.deal(i, '0912345678', stage=1)
        self.deal(300, '0912345678', stage=4)                          # furthest, high id
        res = self.scan()
        (g,) = res['groups']
        self.assertEqual((g['size'], g['truncated'], len(g['members'])), (121, True, 50))
        self.assertEqual(g['members'][0]['id'], 300)
        self.assertEqual(self.ids(g)[1:], list(range(1, 50)))

    # S7 ------------------------------------------------------------------------------------------------
    def test_s7_read_only(self):
        import copy
        self.deal(1, '0912345678')
        self.deal(2, '0912345678', active=False, lost=True)
        before = copy.deepcopy(self.w.tables)
        self.scan()
        self.scan(probe=True)
        self.assertEqual(self.w.tables, before)
        self.assertEqual((self.w.writes, self.w.created), ([], []))
        self.assertTrue(all('INSERT' not in str(e).upper() and 'UPDATE' not in str(e).upper()
                            for e in self.w.events))

    # S8 ------------------------------------------------------------------------------------------------
    def test_s8_seventh_scan_in_ten_minutes_is_refused_probe_is_free(self):
        for _ in range(20):
            self.assertTrue(self.scan(probe=True)['ok'])
        for _ in range(6):
            self.assertTrue(self.scan()['ok'])
        res = self.scan()
        self.assertEqual((res['ok'], res['code']), (False, 'rate_limit'))
        self.assertGreaterEqual(res['retry_after'], 1)
        self.t += res['retry_after'] + 1
        self.assertTrue(self.scan()['ok'])

    def test_s8_probe_has_its_own_limit_of_thirty_a_minute(self):
        for _ in range(30):
            self.assertTrue(self.scan(probe=True)['ok'])
        self.assertEqual(self.scan(probe=True)['code'], 'rate_limit')
        self.assertTrue(self.scan()['ok'])                          # scans are not affected by probes

    def test_s8_another_admin_has_his_own_counter(self):
        for _ in range(6):
            self.scan()
        self.assertEqual(self.scan()['code'], 'rate_limit')
        self.assertTrue(self.scan(svc=self.admin(uid=2))['ok'])

    # S10 -----------------------------------------------------------------------------------------------
    def test_s10_lost_and_mark_lost_stage_are_lost_and_last(self):
        self.w.tables['crm.stage'][9] = {'id': 9, 'name': '8.Mark Lost', 'sequence': 7}
        self.deal(1, '0912345678', stage=1)
        self.deal(2, '0912345678', stage=9)                              # active=True but in a Mark Lost column
        self.deal(3, '0912345678', stage=4, active=False, lost=True)
        self.deal(4, '0912345678', stage=6)
        res = self.scan()
        (g,) = res['groups']
        # active ones first; the two lost ones last, the one parked furthest (Mark Lost column) before the other
        self.assertEqual([(m['id'], m['state']) for m in g['members']],
                         [(4, 'active'), (1, 'active'), (2, 'lost'), (3, 'lost')])
        self.assertEqual(res['scanned'], 2)                  # Deal 2 is not a seed: it counts as lost

    def test_group_of_one_active_and_one_lost_is_returned_all_lost_is_not(self):
        self.deal(1, '0911111111')
        self.deal(2, '0911111111', active=False, lost=True)
        self.deal(3, '0922222222', active=False, lost=True)
        self.deal(4, '0922222222', active=False, prob=5)
        res = self.scan()
        self.assertEqual([self.ids(g) for g in res['groups']], [[1, 2]])

    def test_deal_with_two_numbers_bridges_groups(self):
        self.deal(1, '0911111111', x_phone='0922222222')
        self.deal(2, '0911111111')
        self.deal(3, '0922222222')
        self.deal(4, '0933333333')
        res = self.scan()
        self.assertEqual([self.ids(g) for g in res['groups']], [[1, 2, 3]])

    def test_one_deal_repeating_its_own_number_is_not_a_group(self):
        self.deal(1, '0911111111', x_phone='0911111111', description='0911111111', name='A 0911111111')
        self.assertEqual(self.scan()['groups'], [])

    def test_owner_and_update_flags_for_admin(self):
        self.deal(1, '0911111111', owner=1)
        self.deal(2, '0911111111', owner=5)
        res = self.scan(svc=self.admin(uid=1))
        flags = {m['id']: (m['is_owner'], m['can_update']) for m in res['groups'][0]['members']}
        self.assertEqual(flags, {1: (True, True), 2: (False, True)})

    # input checks -------------------------------------------------------------------------------------
    def test_bad_options_are_invalid_unknown_keys_ignored(self):
        self.deal(1, '0911111111')
        for bad in ('x', 5, [1], {'after_id': -1}, {'after_id': '5'}, {'after_id': True}, {'after_id': 1.5},
                    {'limit': 'x'}, {'limit': False}, {'probe': 'yes'}, {'probe': 1}):
            res = self.admin().yp_duplicate_scan(bad)
            self.assertEqual((res['ok'], res['code']), (False, 'invalid'), bad)
        self.assertTrue(self.admin().yp_duplicate_scan(None)['ok'])
        self.assertTrue(self.admin().yp_duplicate_scan({'whatever': 1, 'limit': None, 'after_id': None})['ok'])
        self.assertEqual(self.admin().yp_duplicate_scan({'limit': 0})['scanned'], 1)       # clamped to 1
        self.assertEqual(self.admin().yp_duplicate_scan({'limit': -5})['scanned'], 1)
        self.w.events.clear()

    def test_invalid_options_do_not_use_up_the_scan_limit(self):
        for _ in range(10):
            self.admin().yp_duplicate_scan({'after_id': -1})
        for _ in range(6):
            self.assertTrue(self.scan()['ok'])

    def test_database_without_optional_columns_still_scans(self):
        for name in ('mobile', 'x_yp_tax_code', 'x_company'):
            self.w.fields['crm.lead'].pop(name, None)
        self.deal(1, '0911111111')
        self.deal(2, '0911111111')
        res = self.scan()
        self.assertEqual([self.ids(g) for g in res['groups']], [[1, 2]])
        self.assertNotIn('x_yp_tax_code', self.w.scan_sql[0][0])

    def test_scan_sql_has_no_user_data_and_sets_no_write(self):
        self.deal(1, '0911111111')
        self.scan(after_id=0)
        (sql, params), = self.w.scan_sql
        self.assertNotIn('911111111', sql)
        self.assertTrue(sql.lstrip().startswith('/* yp_scan */ SELECT'))
        for word in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
            self.assertNotIn(word, sql.upper().replace('UPDATE_', ''))

    def test_log_line_has_counts_only(self):
        import logging
        self.deal(1, '0912345678')
        self.deal(2, '0912345678')
        with self.assertLogs(MOD._logger, level='INFO') as cm:
            self.scan()
        line = ' '.join(cm.output)
        self.assertIn('yp_duplicate_scan', line)
        self.assertNotIn('912345678', line)



class SalesGateTests(Base):
    """Update_027: every yp_* function needs the Sales right "User: Own Documents Only" or higher."""

    def as_(self, groups, uid=50, admin=False, depts=()):
        self.w.groups[uid] = set(groups)
        return self.svc(uid=uid, admin=admin, depts=depts)

    def refused_everywhere(self, s):
        self.w.add(11, 'X', owner=5, phone='0912345678')
        answers = [s.yp_duplicate_check(['912345678'], ''), s.yp_read_lead(11, ['name']),
                   s.yp_update_lead(11, {'name': 'x'}),
                   s.yp_create_lead({'name': 'x', 'phone': '0912345678'}, [], ''),
                   s.yp_duplicate_scan({'probe': True}), s.yp_duplicate_scan({})]
        return answers

    def test_sales_no_is_refused_by_every_function_and_nothing_is_touched(self):
        answers = self.refused_everywhere(self.as_(SALES_NO, depts=(2,)))
        self.assertEqual([a['code'] for a in answers], ['forbidden'] * 6)
        self.assertEqual((self.w.writes, self.w.created, self.w.sql_seen, self.w.events, self.w.scan_sql),
                         ([], [], [], [], []))

    def test_role_administrator_without_a_sales_group_is_refused_too_scan_included(self):
        answers = self.refused_everywhere(self.as_(ROLE_ADMIN_ONLY, admin=True))
        self.assertEqual([a['code'] for a in answers], ['forbidden'] * 6)
        self.assertEqual((self.w.writes, self.w.created, self.w.sql_seen, self.w.events, self.w.scan_sql),
                         ([], [], [], [], []))
        self.assertIn('Sales', answers[0]['message'])

    def test_every_sales_level_may_use_the_check(self):
        self.w.add(11, 'X', owner=5, phone='0912345678')
        for groups in (OWN_DOCUMENTS, ALL_DOCUMENTS, SALES_ADMIN, ROLE_ADMIN_ONLY | OWN_DOCUMENTS):
            res = self.as_(groups).yp_duplicate_check(['912345678'], '')
            self.assertTrue(res['ok'], groups)
            self.assertEqual([m['id'] for m in res['matches']], [11])

    def test_all_documents_does_not_become_admin_sales_or_owner(self):
        self.w.add(11, 'X', owner=5, phone='0912345678')
        for groups in (ALL_DOCUMENTS, SALES_ADMIN):
            res = self.as_(groups, depts=(3,)).yp_duplicate_check(['912345678'], '')
            self.assertEqual((res['is_admin'], res['is_sales'], res['can_update']), (False, False, False))
            self.assertFalse(res['matches'][0]['can_update'])
            self.assertEqual(self.as_(groups, depts=(3,)).yp_update_lead(11, {'name': 'x'})['code'], 'forbidden')
        self.assertEqual(self.w.writes, [])

    def test_scan_needs_role_administrator_and_a_sales_group(self):
        self.deal_pair()
        res = self.as_(ROLE_ADMIN_ONLY | OWN_DOCUMENTS, admin=True).yp_duplicate_scan({})
        self.assertTrue(res['ok'], res)
        self.assertEqual(len(res['groups']), 1)
        self.assertEqual(self.as_(SALES_ADMIN).yp_duplicate_scan({})['code'], 'forbidden')   # Sales Administrator is no Role Administrator
        self.assertEqual(self.as_(ALL_DOCUMENTS).yp_duplicate_scan({'probe': True})['code'], 'forbidden')

    def deal_pair(self):
        self.w.add(1, 'A', owner=5, phone='0912345678')
        self.w.add(2, 'B', owner=6, phone='0912345678')

    def test_create_with_sales_no_never_reaches_the_locks(self):
        res = self.as_(SALES_NO).yp_create_lead({'name': 'n', 'phone': '0912345678'}, ['912345678'], '')
        self.assertEqual(res['code'], 'forbidden')
        self.assertEqual(self.w.events, [])

    def test_gate_is_the_first_thing_every_public_function_does(self):
        src = (ROOT / 'models' / 'duplicate.py').read_text()
        self.assertIn("self.env.user.has_group(U.SALES_USER_GROUP)", src)
        self.assertEqual(U.SALES_USER_GROUP, 'sales_team.group_sale_salesman')
        for name, first in (('yp_duplicate_check', 'refused = self._yp_internal_only()'),
                            ('yp_create_lead', 'refused = self._yp_internal_only()')):
            body = src.split('    def %s(' % name, 1)[1].split('\n', 2)[1]
            self.assertEqual(body.strip(), first, name)
        scan = src.split('    def yp_duplicate_scan(', 1)[1]
        self.assertLess(scan.index('self._is_admin()'), scan.index('self._yp_internal_only()'))
        self.assertLess(scan.index('self._yp_internal_only()'), scan.index('U.parse_scan_options'))
        self.assertLess(src.index('def _yp_access('), src.index('refused = self._yp_internal_only()', src.index('def _yp_access(')) + 1)


class ContractTests(unittest.TestCase):
    def test_base_helpers_still_exist_in_service(self):
        src = (ROOT / 'models' / 'service.py').read_text()
        self.assertIn("def _is_admin(self):\n        return self.env.user.has_group('base.group_system')", src)
        self.assertIn('def _user_department_ids(self):', src)

    def test_models_init_loads_duplicate_after_service(self):
        init = (ROOT / 'models' / '__init__.py').read_text().split()
        self.assertLess(init.index('service'), init.index('duplicate'))

    def test_public_functions_and_no_private_rpc(self):
        src = (ROOT / 'models' / 'duplicate.py').read_text()
        for name in ('yp_duplicate_check', 'yp_duplicate_scan', 'yp_read_lead', 'yp_update_lead', 'yp_create_lead'):
            self.assertIn('    @api.model\n    def %s(' % name, src)
        self.assertIn("_inherit = 'sgt.crm002.service'", src)
        self.assertNotIn('print(', src)
        self.assertNotIn('phone_keys=%s', src)          # no phone numbers in logs

    def test_security_files_untouched_by_this_update(self):
        csv = (ROOT / 'security' / 'ir.model.access.csv').read_text()
        self.assertNotIn('yp_', csv)


if __name__ == '__main__':
    unittest.main()
