"""Update_015: funnel stage bar on the Deal form, Sidebar order / centring, admin without My Pipeline.

Real service code (bootstrap, landing_action, open_intake) runs against fakes; XML / JS / SCSS are
checked as text.  NOT covered here (check on Demo 2): Odoo accepting `context.get(...)` in the form
modifiers, the clickable statusbar writing through CRM-002 write(), real rendering.
"""
import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'models/service.py').read_text()


class FakeError(Exception):
    pass


def load(names):
    tree = ast.parse(SRC)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(funcs) == len(names), names
    for f in funcs:
        f.decorator_list = []
    consts = [n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id in
              ('GROUP_ORDER', 'SIDEBAR_ORDER', 'VIEW_MODES')]
    ns = {'api': SimpleNamespace(model=lambda f: f), 'AccessError': FakeError, 'UserError': FakeError}
    exec(compile(ast.Module(body=consts, type_ignores=[]), 's', 'exec'), ns)
    cls_node = ast.ClassDef(name='Svc', bases=[], keywords=[], body=funcs, decorator_list=[])
    mod = ast.Module(body=[cls_node], type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, 'service.py', 'exec'), ns)
    return ns['Svc']


class Recs(list):
    def filtered(self, fn):
        return Recs(x for x in self if fn(x))

    def sorted(self, key):
        return Recs(sorted(self, key=key))


def funnel(code, group, seq=1, main=False):
    return SimpleNamespace(id=seq, code=code, name=code.title(), group_key=group, is_main=main, sequence=seq)


class Sidebar(unittest.TestCase):
    def groups(self, admin):
        Svc = load(['bootstrap', '_list_funnel_data', '_funnel_counts', '_funnel_count_domain'])
        s = Svc()
        s._is_admin = lambda: admin
        s._visible_funnels = lambda: Recs([funnel('new', 'sale', 3), funnel('hunter', 'data', 1), funnel('mm', 'mm', 2, True)])
        s.env = {'crm.lead': SimpleNamespace(search_count=lambda d: 1)}
        s._admin_directory = lambda: []
        return [g['key'] for g in s.bootstrap()['groups']]

    def test_sale_is_under_match_making(self):
        self.assertEqual(self.groups(True), ['data', 'mm', 'sale'])
        self.assertEqual(self.groups(False), ['data', 'mm', 'sale'])

    def test_fallback_landing_order_is_unchanged(self):
        ns = {}
        exec(compile(ast.Module(body=[n for n in ast.parse(SRC).body if isinstance(n, ast.Assign)
                                      and n.targets[0].id == 'GROUP_ORDER'], type_ignores=[]), 's', 'exec'), ns)
        self.assertEqual([k for k, _ in ns['GROUP_ORDER']], ['data', 'sale', 'mm'])


class SidebarCounts(unittest.TestCase):
    """Update_024: number of Deals at the end of every funnel row and group row."""
    DOMAIN_COUNTS = {}

    def boot(self, funnels, admin=True, per_domain=None):
        Svc = load(['bootstrap', '_list_funnel_data', '_funnel_counts', '_funnel_count_domain'])
        s = Svc()
        s._is_admin = lambda: admin
        s._visible_funnels = lambda: Recs(funnels)
        s._admin_directory = lambda: []
        seen = []

        def search_count(domain):
            seen.append(domain)
            return per_domain(domain)
        s.env = {'crm.lead': SimpleNamespace(search_count=search_count)}
        return s.bootstrap(), seen

    @staticmethod
    def by_domain(domain):
        d = repr(domain)
        if 'sgt_crm002_sale_funnel_id' in d:
            return {'7': 23, '8': 9}[str(domain[0][2])]
        if 'sgt_crm002_funnel_id' in d:
            return {1: 128, 2: 54, 3: 312, 4: 41}[domain[0][2]]
        return 87                                   # Match Making pipeline

    def funnels(self):
        return [funnel('hunter', 'data', 1), funnel('pool', 'data', 2), funnel('odata', 'data', 3),
                funnel('gb', 'data', 4), funnel('mm', 'mm', 5, True), funnel('new', 'sale', 7), funnel('renew', 'sale', 8)]

    def test_children_and_parents(self):
        data, _ = self.boot(self.funnels(), per_domain=self.by_domain)
        g = {x['key']: x for x in data['groups']}
        self.assertEqual([f['count'] for f in g['data']['funnels']], [128, 54, 312, 41])
        self.assertEqual(g['data']['count'], 535)                      # parent = sum of its funnels
        self.assertEqual((g['mm']['count'], g['mm']['funnels'][0]['count']), (87, 87))
        self.assertEqual([f['count'] for f in g['sale']['funnels']], [23, 9])
        self.assertEqual(g['sale']['count'], 32)
        self.assertEqual([f['count'] for f in data['funnels']][:4], [128, 54, 312, 41])   # flat list carries it too

    def test_match_making_group_is_counted_once(self):
        fs = [funnel('mm', 'mm', 5, True), funnel('mm2', 'mm', 6)]
        data, _ = self.boot(fs, per_domain=lambda d: 87)
        self.assertEqual(data['groups'][1]['count'], 87)               # not 174

    def test_domains_are_the_ones_of_the_boards(self):
        _, seen = self.boot(self.funnels(), per_domain=self.by_domain)
        self.assertIn([('type', '=', 'opportunity')], seen)
        self.assertIn([('sgt_crm002_sale_funnel_id', '=', 7)], seen)
        self.assertIn([('sgt_crm002_funnel_id', '=', 1), ('sgt_crm002_step', 'in', ['data', 'verified', 'potential'])], seen)
        src = (ROOT / 'models/service.py').read_text()
        mine = src[src.index('def _funnel_count_domain'):src.index('def _list_funnel_data')]
        self.assertNotIn('.sudo(', mine)                                # counted with the user's own access

    def test_access_error_counts_zero_and_empty_group_is_zero(self):
        def boom(domain):
            raise FakeError('no access')
        data, _ = self.boot([funnel('hunter', 'data', 1)], per_domain=boom)
        g = {x['key']: x for x in data['groups']}
        self.assertEqual((g['data']['count'], g['sale']['count'], g['mm']['count']), (0, 0, 0))

    def test_template_and_css(self):
        x = (ROOT / 'static/src/xml/native_pipeline.xml').read_text()
        ET.fromstring(x)
        self.assertIn('t-esc="group.count"', x)
        self.assertIn('t-esc="f.count"', x)
        css = (ROOT / 'static/src/scss/workspace.scss').read_text()
        for token in ('.sgt002-native-count', '.sgt002-native-has-count', '.sgt002-native-item.active > .sgt002-native-count'):
            self.assertIn(token, css)


class AdminLanding(unittest.TestCase):
    def run_landing(self, admin, context):
        Svc = load(['landing_action'])
        s = Svc()
        s._is_admin = lambda: admin
        s._sees_all = lambda: admin
        s._visible_funnels = lambda: Recs([funnel('mm', 'mm', 2, True)])
        native = {'kind': 'mm', 'context': context}
        s.env = {'crm.team': SimpleNamespace(_sgt_crm002_native_pipeline=lambda: native)}
        return s.landing_action()

    def test_admin_has_no_my_pipeline_default(self):
        act = self.run_landing(True, {'default_type': 'opportunity', 'search_default_assigned_to_me': 1})
        self.assertEqual(act['context']['search_default_assigned_to_me'], 0)
        self.assertEqual(act['context']['default_type'], 'opportunity')

    def test_normal_user_keeps_my_pipeline(self):
        act = self.run_landing(False, {'default_type': 'opportunity', 'search_default_assigned_to_me': 1})
        self.assertEqual(act['context']['search_default_assigned_to_me'], 1)


class FunnelGroupContext(unittest.TestCase):
    def test_actions_carry_their_group(self):
        Svc = load(['open_intake', '_open_sale', '_funnel_views'])

        class Env:
            def ref(self, x, raise_if_not_found=True):
                return SimpleNamespace(id=1)
        for group, expected in (('data', 'data'), ('sale', 'sale')):
            s = Svc()
            s.env = Env()
            s._find_funnel = lambda c, g=group: SimpleNamespace(id=7, name='F', code='c', is_main=False, group_key=g)
            s._check_funnel = lambda f: None
            s._staff_domain = lambda *a: []
            self.assertEqual(s.open_intake('c')['context']['sgt_crm002_funnel_group'], expected)


class FormBar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = ET.fromstring((ROOT / 'views/lead_form_funnel.xml').read_bytes())
        cls.rec = root.find('record')
        arch = next(f for f in cls.rec if f.get('name') == 'arch')
        cls.xpaths = arch.findall('xpath')

    def test_inherits_the_stock_form_and_keeps_stock_bar(self):
        self.assertEqual(next(f for f in self.rec if f.get('name') == 'inherit_id').get('ref'), 'crm.crm_lead_view_form')
        attrs = self.xpaths[0]
        self.assertEqual(attrs.get('position'), 'attributes')
        attr = attrs.find('attribute')
        self.assertEqual(attr.get('name'), 'invisible')
        self.assertEqual(attr.get('separator'), ' or ')
        self.assertIsNotNone(attr.get('add'))              # `add`, never a replace of the stock expression
        self.assertIn("sgt_crm002_step != 'potential'", attr.get('add'))
        self.assertIn("context.get('sgt_crm002_funnel_group') == 'sale'", attr.get('add'))

    def test_two_clickable_funnel_bars(self):
        fields = {f.get('name'): f for f in self.xpaths[1].findall('field')}
        for name in ('sgt_crm002_step', 'sgt_crm002_sale_stage_id'):
            self.assertEqual(fields[name].get('widget'), 'statusbar')
            self.assertEqual(fields[name].get('options'), "{'clickable': '1'}")
        self.assertIn("sgt_crm002_funnel_group') != 'sale'", fields['sgt_crm002_sale_stage_id'].get('invisible'))
        self.assertIn("sgt_crm002_step == 'potential'", fields['sgt_crm002_step'].get('invisible'))
        self.assertIn("('funnel_id', '=', sgt_crm002_sale_funnel_id)", fields['sgt_crm002_sale_stage_id'].get('domain'))
        for name in ('sgt_crm002_funnel_id', 'sgt_crm002_sale_funnel_id'):
            self.assertEqual(fields[name].get('invisible'), '1')

    def test_manifest_loads_the_view_after_the_lists(self):
        data = ast.literal_eval((ROOT / '__manifest__.py').read_text())['data']
        self.assertLess(data.index('views/intake_kanban.xml'), data.index('views/lead_form_funnel.xml'))

    def test_every_modifier_field_exists_on_the_form(self):
        used = set()
        for f in self.xpaths[1].findall('field'):
            for attr in ('invisible', 'readonly'):
                expr = f.get(attr, '')
                if expr and expr not in ('1', '0'):
                    used |= {n.id for n in ast.walk(ast.parse(expr, mode='eval')) if isinstance(n, ast.Name)}
        used -= {'context', 'not', 'type'}
        stock_or_own = {'won_status', 'active', 'sgt_crm002_funnel_id', 'sgt_crm002_step',
                        'sgt_crm002_sale_funnel_id', 'sgt_crm002_sale_stage_id'}
        self.assertEqual(used - stock_or_own, set())


class SidebarFiles(unittest.TestCase):
    def test_js_admin_without_my_pipeline_and_no_new_js_file(self):
        js = (ROOT / 'static/src/js/native_pipeline.js').read_text()
        self.assertIn('search_default_assigned_to_me: 0', js)
        self.assertIn('this.crm002State.isAdmin ?', js)
        self.assertEqual(sorted(p.name for p in (ROOT / 'static/src/js').glob('*.js')),
                         ['native_pipeline.js', 'workspace.js'])

    def test_logo_is_centred_and_collapsed_rail_unchanged(self):
        css = (ROOT / 'static/src/scss/workspace.scss').read_text()
        top = css[css.index('.sgt002-native-top {'):css.index('.sgt002-native-brand {')]
        self.assertIn('justify-content: center', top)
        self.assertIn('.sgt002-native-toggle {\n        position: absolute', css)
        self.assertIn('&.sgt002-collapsed .sgt002-native-toggle { position: static; }', css)


if __name__ == '__main__':
    unittest.main()
