"""Update_027: who sees which CRM-002 funnel = Sales level (Odoo user form) x Department (Permissions button).

    Sales "No"                       no funnel at all
    Sales "User: Own Documents Only" the funnels given to the user's Department (Permissions button); never Sale
    Sales "User: All Documents" and Sales "Administrator" (which includes All Documents), Role Administrator
                                     every funnel, Departments ignored

The REAL service code (_sees_all, _has_sales, _allowed, _check_funnel, _visible_funnels, _mm_allowed,
landing_action, _no_access_action) runs against fakes.  Not covered here (check on Demo 2): the real `has_group`
of Odoo 19 and the user form.
"""
import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'models' / 'service.py').read_text()


class FakeAccess(Exception):
    pass


class FakeUser(Exception):
    pass


METHODS = ['_is_admin', '_sees_all', '_has_sales', '_allowed', '_check_funnel', '_visible_funnels', '_mm_allowed',
           'landing_action', '_no_access_action']


def load():
    tree = ast.parse(SRC)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in METHODS]
    assert sorted(f.name for f in funcs) == sorted(METHODS)
    for f in funcs:
        f.decorator_list = []
    consts = [n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id in ('GROUP_ORDER',)]
    ns = {'api': SimpleNamespace(model=lambda f: f), 'AccessError': FakeAccess, 'UserError': FakeUser}
    exec(compile(ast.Module(body=consts, type_ignores=[]), 's', 'exec'), ns)
    cls_node = ast.ClassDef(name='Svc', bases=[], keywords=[], body=funcs, decorator_list=[])
    mod = ast.Module(body=[cls_node], type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, 'service.py', 'exec'), ns)
    return ns['Svc']


Svc = load()

OWN = frozenset({'base.group_user', 'sales_team.group_sale_salesman'})
ALL = OWN | {'sales_team.group_sale_salesman_all_leads'}
SALES_ADMIN = ALL | {'sales_team.group_sale_manager'}
NO = frozenset({'base.group_user'})
ROLE_ADMIN_ONLY = frozenset({'base.group_user', 'base.group_system'})      # Role Administrator does not carry Sales groups
ROLE_ADMIN_FULL = ROLE_ADMIN_ONLY | SALES_ADMIN

ADMINISTRATION, MMC, CN = 1, 2, 3                                          # production departments


class Recs(list):
    def filtered(self, fn):
        return Recs(x for x in self if fn(x))

    def sorted(self, key):
        return Recs(sorted(self, key=key))


class Funnel:
    def __init__(self, id, code, group, depts, main=False):
        self.id, self.code, self.group_key, self.is_main = id, code, group, main
        self.sequence = id
        self.allowed_department_ids = SimpleNamespace(ids=list(depts))

    def sudo(self):
        return self


def production_funnels():
    """Exactly what Xinyang has today (read 02/11 14:2x)."""
    return Recs([
        Funnel(1, 'hunter', 'data', [MMC]),
        Funnel(2, 'pool', 'data', [CN, MMC]),
        Funnel(3, 'unverified', 'data', []),
        Funnel(4, 'face', 'data', []),
        Funnel(5, 'mm', 'mm', [MMC], main=True),
        Funnel(6, 'sale_new', 'sale', [ADMINISTRATION]),
        Funnel(7, 'sale_renew', 'sale', [ADMINISTRATION]),
    ])


class Table:
    def __init__(self, funnels):
        self.funnels = funnels

    def sudo(self):
        return self

    def search(self, domain):
        return Recs(self.funnels)


class Env:
    def __init__(self, groups, funnels, native):
        self.user = SimpleNamespace(has_group=lambda g: g in groups)
        self.funnels, self.native = funnels, native

    def __getitem__(self, name):
        if name == 'sgt.crm002.funnel':
            return Table(self.funnels)
        if name == 'crm.team':
            return SimpleNamespace(_sgt_crm002_native_pipeline=lambda: self.native)
        raise AssertionError(name)

    def ref(self, xmlid):
        return SimpleNamespace(id=9)


def service(groups, depts=(), opened=None):
    s = Svc()
    s.native = {'kind': 'mm_pipeline', 'context': {'default_type': 'opportunity', 'search_default_assigned_to_me': 1}}
    s.env = Env(groups, production_funnels(), s.native)
    s._user_department_ids = lambda: set(depts)

    def open_intake(code):
        if opened is not None:
            opened.append(code)
        return {'kind': 'intake', 'code': code}
    s.open_intake = open_intake
    return s


def codes(recs):
    return [f.code for f in recs]


EVERY = ['hunter', 'pool', 'unverified', 'face', 'mm', 'sale_new', 'sale_renew']


class VisibleFunnels(unittest.TestCase):
    def test_sales_no_sees_nothing_whatever_the_department(self):
        for depts in ((), (MMC,), (CN,), (ADMINISTRATION,), (MMC, CN, ADMINISTRATION)):
            self.assertEqual(codes(service(NO, depts)._visible_funnels()), [], depts)

    def test_own_documents_follows_the_departments(self):
        self.assertEqual(codes(service(OWN, (MMC,))._visible_funnels()), ['hunter', 'pool', 'mm'])
        self.assertEqual(codes(service(OWN, (CN,))._visible_funnels()), ['pool'])
        self.assertEqual(codes(service(OWN, ())._visible_funnels()), [])

    def test_own_documents_never_sees_the_sale_funnels_even_in_the_allowed_department(self):
        self.assertEqual(codes(service(OWN, (ADMINISTRATION,))._visible_funnels()), [])
        self.assertEqual(codes(service(OWN, (ADMINISTRATION, MMC))._visible_funnels()), ['hunter', 'pool', 'mm'])
        for depts in ((ADMINISTRATION,), (MMC,), (ADMINISTRATION, MMC, CN)):
            self.assertNotIn('sale_new', codes(service(OWN, depts)._visible_funnels()))
            self.assertNotIn('sale_renew', codes(service(OWN, depts)._visible_funnels()))

    def test_funnels_without_a_department_stay_hidden_from_own_documents(self):
        for depts in ((MMC,), (CN,), (ADMINISTRATION,), (MMC, CN)):
            visible = codes(service(OWN, depts)._visible_funnels())
            self.assertNotIn('unverified', visible)
            self.assertNotIn('face', visible)

    def test_all_documents_sales_administrator_and_role_administrator_see_every_funnel(self):
        for groups in (ALL, SALES_ADMIN, ROLE_ADMIN_ONLY, ROLE_ADMIN_FULL):
            for depts in ((), (CN,), (MMC,), (ADMINISTRATION,)):
                self.assertEqual(codes(service(groups, depts)._visible_funnels()), EVERY, (groups, depts))

    def test_role_administrator_keeps_every_funnel_even_with_sales_no(self):
        self.assertEqual(codes(service(ROLE_ADMIN_ONLY, ())._visible_funnels()), EVERY)


class Allowed(unittest.TestCase):
    def verdicts(self, groups, depts):
        s = service(groups, depts)
        return {f.code: s._allowed(f) for f in production_funnels()}

    def test_matrix(self):
        every = {c: True for c in EVERY}
        self.assertEqual(self.verdicts(ALL, ()), every)
        self.assertEqual(self.verdicts(SALES_ADMIN, (CN,)), every)
        self.assertEqual(self.verdicts(ROLE_ADMIN_ONLY, ()), every)
        self.assertEqual(self.verdicts(NO, (MMC,)), {c: False for c in EVERY})
        self.assertEqual(self.verdicts(OWN, (MMC,)), {'hunter': True, 'pool': True, 'unverified': False, 'face': False,
                                                      'mm': True, 'sale_new': False, 'sale_renew': False})
        self.assertEqual(self.verdicts(OWN, (ADMINISTRATION,)), {c: False for c in EVERY})

    def test_check_funnel_raises_for_what_is_not_allowed(self):
        sale = production_funnels()[5]
        s = service(OWN, (ADMINISTRATION,))
        self.assertRaises(FakeAccess, s._check_funnel, sale)
        self.assertRaises(FakeAccess, service(NO, (MMC,))._check_funnel, production_funnels()[0])
        service(ALL, ())._check_funnel(sale)                    # no error
        service(OWN, (MMC,))._check_funnel(production_funnels()[0])


class MatchMakingGate(unittest.TestCase):
    def test_who_may_read_the_match_making_pipeline(self):
        self.assertFalse(service(NO, (MMC,))._mm_allowed())
        self.assertTrue(service(OWN, (MMC,))._mm_allowed())
        self.assertFalse(service(OWN, (CN,))._mm_allowed())
        self.assertFalse(service(OWN, (ADMINISTRATION,))._mm_allowed())
        for groups in (ALL, SALES_ADMIN, ROLE_ADMIN_ONLY):
            self.assertTrue(service(groups, ())._mm_allowed(), groups)


class Landing(unittest.TestCase):
    def test_all_documents_lands_on_match_making_and_keeps_my_pipeline(self):
        for groups in (ALL, SALES_ADMIN):
            act = service(groups, (CN,)).landing_action()
            self.assertEqual(act['kind'], 'mm_pipeline')
            self.assertEqual(act['context']['search_default_assigned_to_me'], 1)

    def test_role_administrator_still_drops_my_pipeline(self):
        act = service(ROLE_ADMIN_FULL, ()).landing_action()
        self.assertEqual(act['kind'], 'mm_pipeline')
        self.assertEqual(act['context']['search_default_assigned_to_me'], 0)

    def test_sales_no_gets_the_empty_page(self):
        act = service(NO, (MMC,)).landing_action()
        self.assertEqual(act['domain'], [('id', '=', 0)])
        self.assertIn('chưa được phân quyền', act['help'])

    def test_own_documents_in_cn_lands_on_inbound_pool_not_on_sale(self):
        opened = []
        act = service(OWN, (CN,), opened).landing_action()
        self.assertEqual((act['kind'], opened), ('intake', ['pool']))

    def test_own_documents_in_administration_only_has_nothing(self):
        act = service(OWN, (ADMINISTRATION,)).landing_action()
        self.assertEqual(act['domain'], [('id', '=', 0)])


class Contract(unittest.TestCase):
    def method_src(self, name):
        tree = ast.parse(SRC)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
        return ast.unparse(next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name))

    def test_groups_checked(self):
        self.assertIn("'base.group_system'", self.method_src('_is_admin'))
        sees = self.method_src('_sees_all')
        self.assertIn('self._is_admin()', sees)
        self.assertIn("'sales_team.group_sale_salesman_all_leads'", sees)
        self.assertNotIn('group_sale_manager', sees)            # Sales Administrator includes All Documents already
        self.assertIn("'sales_team.group_sale_salesman'", self.method_src('_has_sales'))

    def test_sees_all_is_used_only_where_the_design_says(self):
        tree = ast.parse(SRC)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
        users = sorted(f.name for f in cls.body if isinstance(f, ast.FunctionDef) and f.name != '_sees_all'
                       and 'self._sees_all()' in ast.unparse(f))
        self.assertEqual(users, ['_allowed', '_mm_allowed', '_visible_funnels', 'landing_action'])

    def test_configuration_stays_with_the_role_administrator(self):
        for name in ('settings', 'save_permissions', 'save_filter', '_staff_domain', '_admin_directory'):
            body = self.method_src(name)
            self.assertIn('_check_admin()', body, name)
            self.assertNotIn('_sees_all', body, name)
        self.assertIn("'is_admin': admin", self.method_src('bootstrap'))
        self.assertIn('admin = self._is_admin()', self.method_src('bootstrap'))
        self.assertIn('self._is_admin()', self.method_src('landing_action'))         # My Pipeline off: Role Administrator only
        self.assertEqual(self.method_src('_check_admin').count('_is_admin'), 1)

    def test_acl_and_menus_are_untouched(self):
        acl = (ROOT / 'security' / 'ir.model.access.csv').read_text()
        for line in acl.strip().splitlines()[1:]:
            if 'stage_user' in line:
                self.assertIn('base.group_user', line)
            else:
                self.assertIn('base.group_system', line, line)
        self.assertNotIn('sales_team', acl)
        menu = (ROOT / 'views' / 'menu.xml').read_text()
        self.assertEqual(menu.count('groups="base.group_system"'), 3)
        self.assertNotIn('sales_team', menu)

    def test_no_new_field_model_cron_or_js(self):
        init = (ROOT / 'models' / '__init__.py').read_text()
        self.assertEqual(sorted(re.findall(r'import (\w+)', init)),
                         sorted(['crm_lead', 'crm_team', 'duplicate', 'funnel', 'funnel_stage', 'handoff_rule', 'progress',
                                 'service']))
        for name in ('service', 'duplicate'):
            src = (ROOT / 'models' / (name + '.py')).read_text()
            self.assertNotIn('fields.', src.replace('fields.Datetime.now', '').replace('fields.Datetime', ''))
        self.assertFalse(list((ROOT / 'data').glob('*cron*')))
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(manifest['version'], '19.0.1.26.0')
        self.assertIn('sales_team', manifest['depends'])


if __name__ == '__main__':
    unittest.main()
