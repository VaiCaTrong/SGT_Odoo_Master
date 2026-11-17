"""Update_011: where the CRM menu lands. Runs the REAL landing_action code against fake records.
Proves the decision order only (Match Making first, else first allowed funnel, else empty page).
Menu override / server action / empty Kanban view must be checked on Demo 2."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


class FakeAccessError(Exception):
    pass


class FakeUserError(Exception):
    pass


def load():
    tree = ast.parse((ROOT / 'models' / 'service.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('landing_action', '_no_access_action')]
    ns = {'api': SimpleNamespace(model=lambda f: f), 'AccessError': FakeAccessError, 'UserError': FakeUserError,
          'GROUP_ORDER': [('data', 'Data Funnel'), ('sale', 'Sale'), ('mm', 'Match Making Campaign')]}
    exec(compile(ast.Module(body=funcs, type_ignores=[]), 'service.py', 'exec'), ns)
    return ns['landing_action'], ns['_no_access_action']


LANDING, NOACCESS = load()


class Recs(list):
    def filtered(self, fn):
        return Recs(x for x in self if fn(x))

    def sorted(self, key):
        return Recs(sorted(self, key=key))


def F(id, group, code, seq=10, is_main=False):
    return SimpleNamespace(id=id, group_key=group, code=code, sequence=seq, is_main=is_main)


class Svc:
    def __init__(self, funnels, admin=False, denied=()):
        self._f, self._admin, self.denied, self.opened = Recs(funnels), admin, set(denied), []
        team = SimpleNamespace(_sgt_crm002_native_pipeline=lambda: {'kind': 'mm_pipeline'})
        self.env = SimpleNamespace(
            __getitem__=None,
            ref=lambda x: SimpleNamespace(id=9))
        self.env = _Env(team)

    def _visible_funnels(self):
        return self._f

    def _is_admin(self):
        return self._admin

    def _sees_all(self):                 # Update_027: Role Administrator (or All Documents, tested elsewhere)
        return self._admin

    def open_intake(self, code):
        if code in self.denied:
            raise FakeAccessError(code)
        self.opened.append(code)
        return {'kind': 'intake', 'code': code}

    def _no_access_action(self):
        return NOACCESS(self)

    def landing(self):
        return LANDING(self)


class _Env:
    def __init__(self, team):
        self.team = team

    def __getitem__(self, name):
        assert name == 'crm.team'
        return self.team

    def ref(self, xmlid):
        assert xmlid == 'sgt_crm_campaign.view_crm002_noaccess_company_kanban'
        return SimpleNamespace(id=9)


MM = F(5, 'mm', 'mm', 30, True)
HUNTER = F(1, 'data', 'hunter', 10)
POOL = F(2, 'data', 'pool', 20)
NEW = F(7, 'sale', 'sale_new', 10)


class Landing(unittest.TestCase):
    def test_admin_goes_to_match_making(self):
        self.assertEqual(Svc([HUNTER, MM], admin=True).landing(), {'kind': 'mm_pipeline'})

    def test_match_making_allowed_goes_first(self):
        s = Svc([HUNTER, NEW, MM])
        self.assertEqual(s.landing(), {'kind': 'mm_pipeline'})
        self.assertEqual(s.opened, [])

    def test_without_match_making_first_data_funnel(self):
        s = Svc([NEW, POOL, HUNTER])
        self.assertEqual(s.landing(), {'kind': 'intake', 'code': 'hunter'})

    def test_only_sale_funnel(self):
        self.assertEqual(Svc([NEW]).landing(), {'kind': 'intake', 'code': 'sale_new'})

    def test_skips_funnel_that_cannot_open(self):
        self.assertEqual(Svc([HUNTER, POOL], denied={'hunter'}).landing(), {'kind': 'intake', 'code': 'pool'})

    def test_no_funnel_gives_empty_page(self):
        a = Svc([]).landing()
        self.assertEqual(a['domain'], [('id', '=', 0)])
        self.assertEqual(a['res_model'], 'res.company')      # Update_028: never crm.lead
        self.assertEqual(a['views'], [(9, 'kanban')])
        self.assertIs(a['context']['create'], False)
        self.assertIn('chưa được phân quyền', a['help'])

    def test_everything_denied_gives_empty_page(self):
        a = Svc([HUNTER], denied={'hunter'}).landing()
        self.assertEqual(a['domain'], [('id', '=', 0)])


class Wiring(unittest.TestCase):
    def test_manifest_and_files(self):
        m = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertIn('views/landing.xml', m['data'])
        x = (ROOT / 'views' / 'landing.xml').read_text()
        for needle in ('crm.menu_crm_opportunities', 'landing_action()', 'sales_team.model_crm_team',
                       'view_crm002_noaccess_company_kanban', 'create="0"',
                       'js_class="sgt_crm002_intake"'):
            self.assertIn(needle, x)


if __name__ == '__main__':
    unittest.main()
