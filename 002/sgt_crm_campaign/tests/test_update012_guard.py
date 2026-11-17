"""Update_012: server-side gate of the Match Making pipeline + crm.team landing override.

Runs the REAL `_search` override of crm.lead and the REAL `_mm_allowed` against fakes.
Not covered here (check on Demo 2): the context flag arriving from the action, ORM internals.
"""
import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text()


def method(path, cls_name, func_name):
    tree = ast.parse(read(path))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == func_name)


class Base:
    last = None

    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        Base.last = dict(domain=domain, offset=offset, limit=limit, order=order,
                         active_test=active_test, bypass_access=bypass_access)
        return 'QUERY'


def build_lead_class():
    fn = method('models/crm_lead.py', 'CrmLead', '_search')
    fn.decorator_list = []
    ns = {'Base': Base}
    mod = ast.Module(body=[ast.ClassDef(
        name='Lead', bases=[ast.Name(id='Base', ctx=ast.Load())], keywords=[], body=[fn], decorator_list=[])],
        type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, 'crm_lead.py', 'exec'), ns)
    return ns['Lead']


Lead = build_lead_class()


class Service:
    def __init__(self, allowed):
        self.allowed = allowed

    def _mm_allowed(self):
        return self.allowed


def make(ctx, allowed):
    lead = Lead()
    lead.env = SimpleNamespace(context=ctx, __getitem__=None)
    lead.env = _Env(ctx, Service(allowed))
    return lead


class _Env:
    def __init__(self, ctx, svc):
        self.context, self.svc = ctx, svc

    def __getitem__(self, name):
        assert name == 'sgt.crm002.service'
        return self.svc


class SearchGuard(unittest.TestCase):
    D = [('type', '=', 'opportunity')]

    def test_flag_without_permission_is_empty(self):
        self.assertEqual(make({'sgt_crm002_mm_guard': True}, False)._search(self.D, 5, 10, 'id'), 'QUERY')
        self.assertEqual(Base.last['domain'], [('id', '=', 0)])
        self.assertEqual((Base.last['offset'], Base.last['limit'], Base.last['order']), (5, 10, 'id'))

    def test_flag_with_permission_is_untouched(self):
        make({'sgt_crm002_mm_guard': True}, True)._search(self.D)
        self.assertEqual(Base.last['domain'], self.D)

    def test_no_flag_never_calls_service(self):
        lead = make({}, False)
        lead.env.svc = None  # would crash if consulted
        lead._search(self.D, active_test=False, bypass_access=True)
        self.assertEqual(Base.last['domain'], self.D)
        self.assertFalse(Base.last['active_test'])
        self.assertTrue(Base.last['bypass_access'])

    def test_domain_as_keyword(self):
        make({'sgt_crm002_mm_guard': True}, False)._search(domain=self.D)
        self.assertEqual(Base.last['domain'], [('id', '=', 0)])


class Funnel:
    def __init__(self, group, main=False):
        self.group_key, self.is_main = group, main


class MmAllowed(unittest.TestCase):
    def run_allowed(self, admin, funnels):
        fn = method('models/service.py', 'Crm002Service', '_mm_allowed')
        fn.decorator_list = []
        mod = ast.Module(body=[fn], type_ignores=[])
        ns = {}
        exec(compile(mod, 's.py', 'exec'), ns)
        svc = SimpleNamespace(_is_admin=lambda: admin, _sees_all=lambda: admin, _visible_funnels=lambda: funnels)
        return ns['_mm_allowed'](svc)

    def test_admin(self):
        self.assertTrue(self.run_allowed(True, []))

    def test_mm_funnel(self):
        self.assertTrue(self.run_allowed(False, [Funnel('data'), Funnel('mm', True)]))

    def test_main_flag(self):
        self.assertTrue(self.run_allowed(False, [Funnel('data', True)]))

    def test_only_data_and_sale(self):
        self.assertFalse(self.run_allowed(False, [Funnel('data'), Funnel('sale')]))

    def test_nothing(self):
        self.assertFalse(self.run_allowed(False, []))


class Wiring(unittest.TestCase):
    def test_team_override_and_helper(self):
        src = read('models/crm_team.py')
        self.assertIn("_inherit = 'crm.team'", src)
        a = method('models/crm_team.py', 'CrmTeam', 'action_your_pipeline')
        self.assertIn('landing_action', ast.unparse(a))
        h = method('models/crm_team.py', 'CrmTeam', '_sgt_crm002_native_pipeline')
        self.assertIn('super().action_your_pipeline()', ast.unparse(h))
        self.assertIn('from . import crm_team', read('models/__init__.py'))

    def test_landing_uses_helper_not_recursion(self):
        body = ast.unparse(method('models/service.py', 'Crm002Service', 'landing_action'))
        self.assertIn('_sgt_crm002_native_pipeline()', body)
        self.assertNotIn('.action_your_pipeline()', body)

    def test_action_context_has_flag_and_stock_keys(self):
        root = ET.fromstring(read('views/landing.xml').encode())
        rec = next(r for r in root.iter('record') if r.get('id') == 'crm.crm_lead_action_pipeline')
        ctx = ast.literal_eval(next(f for f in rec if f.get('name') == 'context').text.strip())
        self.assertIs(ctx['sgt_crm002_mm_guard'], True)
        self.assertEqual(ctx['default_type'], 'opportunity')
        self.assertEqual(ctx['search_default_assigned_to_me'], 1)
        self.assertEqual(ctx['show_user_team_stages'], 1)

    def test_intake_actions_do_not_carry_flag(self):
        # A Data/Sale funnel action must never be gated by the Match Making flag.
        self.assertNotIn('sgt_crm002_mm_guard', read('models/service.py'))
        self.assertEqual(read('views/intake_kanban.xml').count('sgt_crm002_mm_guard'), 0)

    def test_no_js_added(self):
        js = sorted(p.name for p in (ROOT / 'static/src/js').glob('*.js'))
        self.assertEqual(js, ['native_pipeline.js', 'workspace.js'])

    def test_manifest(self):
        m = ast.literal_eval(read('__manifest__.py'))
        self.assertEqual(m['version'], '19.0.1.26.0')


if __name__ == '__main__':
    unittest.main()
