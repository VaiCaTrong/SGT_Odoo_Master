"""Update_013: view switcher (Kanban, List, Calendar, Pivot, Graph, Activity) on the Data / Sale funnels.

Runs the REAL open_intake / _open_sale / _funnel_views code against fake records.
Not covered here (check on Demo 2): Odoo accepting the group_by / pivot_row_groupby / graph_groupbys
context keys, the stock view ids on the live database.
"""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'models' / 'service.py').read_text()


class FakeError(Exception):
    pass


def load():
    tree = ast.parse(SRC)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
    names = ('open_intake', '_open_sale', '_funnel_views')
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(funcs) == 3
    const = [n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == 'VIEW_MODES']
    ns = {'api': SimpleNamespace(model=lambda f: f), 'UserError': FakeError, 'AccessError': FakeError}
    exec(compile(ast.Module(body=const, type_ignores=[]), 's', 'exec'), ns)
    cls_node = ast.ClassDef(name='Svc', bases=[], keywords=[], body=funcs, decorator_list=[])
    for f in funcs:
        f.decorator_list = []
    mod = ast.Module(body=[cls_node], type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, 'service.py', 'exec'), ns)
    return ns['Svc'], ns['VIEW_MODES']


Svc, VIEW_MODES = load()
STOCK = {
    'crm.crm_case_tree_view_oppor': 11, 'crm.crm_case_calendar_view_leads': 12,
    'crm.crm_lead_view_pivot': 13, 'crm.crm_lead_view_graph': 14, 'crm.crm_lead_view_activity': 15,
    'sgt_crm_campaign.view_crm002_intake_kanban': 21, 'sgt_crm_campaign.view_crm002_sale_kanban': 22,
    'sgt_crm_campaign.view_crm002_intake_list': 31, 'sgt_crm_campaign.view_crm002_sale_list': 32,
}


class FakeEnv:
    def __init__(self, missing=()):
        self.missing = set(missing)

    def ref(self, xmlid, raise_if_not_found=True):
        if xmlid in self.missing:
            if raise_if_not_found:
                raise FakeError(xmlid)
            return None
        return SimpleNamespace(id=STOCK[xmlid])


def service(group, missing=()):
    s = Svc()
    s.env = FakeEnv(missing)
    s._find_funnel = lambda code: SimpleNamespace(id=7, name='F', code='c', is_main=False, group_key=group)
    s._check_funnel = lambda f: None
    s._staff_domain = lambda *a: []
    return s


class FunnelViews(unittest.TestCase):
    def test_modes_order_matches_stock_switcher(self):
        self.assertEqual(VIEW_MODES, 'kanban,list,calendar,pivot,graph,activity,form')

    def check(self, act, kanban_id, field, list_id):
        self.assertEqual(act['view_mode'], VIEW_MODES)
        self.assertEqual([t for _i, t in act['views']], VIEW_MODES.split(','))
        self.assertEqual(act['views'][0], (kanban_id, 'kanban'))
        self.assertEqual(dict((t, i) for i, t in act['views'])['list'], list_id)   # Update_014: funnel list
        self.assertEqual(dict((t, i) for i, t in act['views'])['pivot'], 13)
        ctx = act['context']
        self.assertEqual(ctx['group_by'], [field])
        self.assertEqual(ctx['pivot_row_groupby'], [field])
        self.assertEqual(ctx['graph_groupbys'], [field])
        # previous keys are kept
        self.assertEqual(ctx['search_default_assigned_to_me'], 0)
        self.assertEqual(ctx['show_user_team_stages'], 0)
        self.assertNotIn('sgt_crm002_mm_guard', ctx)

    def test_data_funnel(self):
        act = service('data').open_intake('data1')
        self.check(act, 21, 'sgt_crm002_step', 31)
        self.assertEqual(act['domain'][0], ('sgt_crm002_funnel_id', '=', 7))
        self.assertEqual(act['context']['default_type'], 'opportunity')

    def test_sale_funnel(self):
        act = service('sale').open_intake('new')
        self.check(act, 22, 'sgt_crm002_sale_stage_id', 32)
        self.assertEqual(act['domain'], [('sgt_crm002_sale_funnel_id', '=', 7)])

    def test_missing_stock_view_falls_back_to_default(self):
        act = service('data', missing=['crm.crm_lead_view_graph']).open_intake('data1')
        self.assertEqual(dict((t, i) for i, t in act['views'])['graph'], False)

    def test_match_making_still_uses_stock_pipeline(self):
        s = service('mm')
        with self.assertRaises(FakeError):
            s.open_intake('mm')


class Wiring(unittest.TestCase):
    def test_no_new_js_field_or_model(self):
        js = sorted(p.name for p in (ROOT / 'static/src/js').glob('*.js'))
        self.assertEqual(js, ['native_pipeline.js', 'workspace.js'])
        self.assertNotIn('fields.', SRC[SRC.index('def _funnel_views'):SRC.index('def _open_sale')])



class ListViews(unittest.TestCase):
    """Update_014: the funnel List replaces the CRM Stage column ('1.Opportunity') by the funnel's own stage."""

    @classmethod
    def setUpClass(cls):
        import xml.etree.ElementTree as ET
        root = ET.fromstring((ROOT / 'views/intake_kanban.xml').read_bytes())
        cls.recs = {r.get('id'): r for r in root.iter('record')}

    def field(self, rec, name):
        return next(f for f in rec if f.get('name') == name)

    def test_two_primary_lists_of_the_stock_opportunity_list(self):
        for rid, new in (('view_crm002_intake_list', 'sgt_crm002_step'),
                         ('view_crm002_sale_list', 'sgt_crm002_sale_stage_id')):
            rec = self.recs[rid]
            self.assertEqual(self.field(rec, 'inherit_id').get('ref'), 'crm.crm_case_tree_view_oppor')
            self.assertEqual(self.field(rec, 'mode').text, 'primary')
            arch = self.field(rec, 'arch')
            xp = arch.find('xpath')
            self.assertEqual(xp.get('expr'), "//field[@name='stage_id']")
            self.assertEqual(xp.get('position'), 'replace')
            fld = xp.find('field')
            self.assertEqual(fld.get('name'), new)
            self.assertEqual(fld.get('string'), 'Stage')

    def test_manifest_loads_the_file(self):
        self.assertIn("'views/intake_kanban.xml'", (ROOT / '__manifest__.py').read_text())


if __name__ == '__main__':
    unittest.main()
