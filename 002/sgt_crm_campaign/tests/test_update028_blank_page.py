"""Update_028: a user without any funnel permission gets a BLANK page, never an Access Error.

Bug (user, Demo 2, 02/11 15:33): Sales = "No" -> clicking CRM showed
"You are not allowed to access 'Lead' (crm.lead) records" over the old screen (the deals behind
the dialog were just the previous screen left on display because the new one failed to load).
Cause: the empty page was a crm.lead Kanban with domain `id = 0`.  Odoo checks the model access
right BEFORE it applies any domain, and a user with Sales = No has no access right on crm.lead.

Fix: the empty page is a res.company Kanban (readable by every internal user, stock ACL
`access_res_company_employee`) with domain `id = 0`; no deal is read at all.

The REAL `_no_access_action` and `landing_action` run against fakes that RAISE if crm.lead is touched.
Not covered here (check on Demo 2): that Odoo 19 renders the res.company Kanban with the sidebar.
"""
import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'models' / 'service.py').read_text()
LANDING_XML = (ROOT / 'views' / 'landing.xml').read_text()

# Models a plain internal user (base.group_user) can always read: stock base ACL, Odoo 19
# (odoo/addons/base/security/ir.model.access.csv: access_res_company_employee perm_read=1).
READABLE_BY_EVERY_INTERNAL_USER = {'res.company'}
NEW_XMLID = 'sgt_crm_campaign.view_crm002_noaccess_company_kanban'
OLD_XMLID = 'view_crm002_noaccess_kanban'


class FakeAccess(Exception):
    pass


class FakeUser(Exception):
    pass


METHODS = ['_is_admin', '_sees_all', '_has_sales', '_visible_funnels', '_mm_allowed', 'landing_action',
           '_no_access_action']


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
    mod = ast.Module(body=[ast.ClassDef(name='Svc', bases=[], keywords=[], body=funcs, decorator_list=[])],
                     type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, 'service.py', 'exec'), ns)
    return ns['Svc']


Svc = load()


class Recs(list):
    def filtered(self, fn):
        return Recs(x for x in self if fn(x))

    def sorted(self, key):
        return Recs(sorted(self, key=key))


class Env:
    """crm.lead (and anything the user cannot read) raises, exactly like a user with Sales = No."""

    def __init__(self, groups):
        self.user = SimpleNamespace(has_group=lambda g: g in groups)
        self.refs = []
        self.touched = []

    def __getitem__(self, name):
        self.touched.append(name)
        if name == 'sgt.crm002.funnel':
            return SimpleNamespace(sudo=lambda: SimpleNamespace(search=lambda domain: Recs()))
        raise FakeAccess("You are not allowed to access '%s' records." % name)

    def ref(self, xmlid):
        self.refs.append(xmlid)
        return SimpleNamespace(id=9)


def service(groups):
    s = Svc()
    s.env = Env(groups)
    s._user_department_ids = lambda: set()
    s.open_intake = lambda code: (_ for _ in ()).throw(AssertionError('no funnel must be opened'))
    return s


NO = frozenset({'base.group_user'})
OWN = NO | {'sales_team.group_sale_salesman'}


def view_record():
    root = ET.fromstring(LANDING_XML)
    return next(r for r in root.iter('record') if r.get('id') == NEW_XMLID.split('.')[1])


class BlankPageNeverReadsDeals(unittest.TestCase):
    def test_sales_no_gets_a_page_on_a_model_everybody_can_read(self):
        s = service(NO)
        act = s.landing_action()
        self.assertEqual(act['res_model'], 'res.company')
        self.assertIn(act['res_model'], READABLE_BY_EVERY_INTERNAL_USER)
        self.assertNotEqual(act['res_model'], 'crm.lead')
        self.assertEqual(act['domain'], [('id', '=', 0)])
        self.assertEqual(act['view_mode'], 'kanban')
        self.assertEqual(act['views'], [(9, 'kanban')])
        self.assertIs(act['context']['create'], False)
        self.assertIn('chưa được phân quyền', act['help'])

    def test_landing_for_sales_no_never_touches_crm_lead(self):
        s = service(NO)
        s.landing_action()
        self.assertNotIn('crm.lead', s.env.touched)
        self.assertEqual(s.env.refs, [NEW_XMLID])

    def test_own_documents_without_funnel_gets_the_same_blank_page(self):
        s = service(OWN)
        act = s.landing_action()
        self.assertEqual(act['res_model'], 'res.company')
        self.assertEqual(act['domain'], [('id', '=', 0)])

    def test_the_blank_page_does_not_carry_crm_lead_context_keys(self):
        ctx = service(NO)._no_access_action()['context']
        for key in ('search_default_assigned_to_me', 'show_user_team_stages', 'default_type'):
            self.assertNotIn(key, ctx)


class ViewRecord(unittest.TestCase):
    def test_xml_is_well_formed_and_old_crm_lead_view_is_gone(self):
        ET.fromstring(LANDING_XML)
        ids = [r.get('id') for r in ET.fromstring(LANDING_XML).iter('record')]
        self.assertNotIn(OLD_XMLID, ids)           # Odoo deletes it on upgrade because it is no longer defined
        self.assertIn(NEW_XMLID.split('.')[1], ids)

    def test_view_model_equals_the_action_model(self):
        rec = view_record()
        fields = {f.get('name'): f for f in rec.findall('field')}
        self.assertEqual(fields['model'].text.strip(), 'res.company')
        act = service(NO)._no_access_action()
        self.assertEqual(fields['model'].text.strip(), act['res_model'])

    def test_view_is_a_standalone_kanban_with_the_sidebar_and_no_create(self):
        rec = view_record()
        names = [f.get('name') for f in rec.findall('field')]
        self.assertNotIn('inherit_id', names)       # not an extension of the crm.lead view
        self.assertNotIn('crm.', ET.tostring(rec, encoding='unicode'))
        arch = next(f for f in rec.findall('field') if f.get('name') == 'arch')
        kanban = arch.find('kanban')
        self.assertEqual(kanban.get('js_class'), 'sgt_crm002_intake')
        self.assertEqual(kanban.get('create'), '0')
        self.assertEqual(kanban.get('sample'), 'false')
        card = kanban.find('templates').find('t')
        self.assertEqual(card.get('t-name'), 'card')       # Odoo 19 card template name
        self.assertTrue(any(f.get('name') == 'name' for f in kanban.findall('field')))

    def test_no_other_empty_page_is_built_on_crm_lead(self):
        for name in ('landing.xml',):
            xml = (ROOT / 'views' / name).read_text()
            root = ET.fromstring(xml)
            for rec in root.iter('record'):
                if rec.get('model') != 'ir.ui.view':
                    continue
                fields = {f.get('name'): (f.text or '').strip() for f in rec.findall('field')}
                self.assertNotEqual(fields.get('model'), 'crm.lead', rec.get('id'))


class Wiring(unittest.TestCase):
    def test_landing_xml_is_loaded_and_version_is_bumped(self):
        m = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertIn('views/landing.xml', m['data'])
        self.assertEqual(m['version'], '19.0.1.26.0')

    def test_service_no_longer_names_crm_lead_in_the_empty_action(self):
        tree = ast.parse(SRC)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Crm002Service')
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_no_access_action')
        body = ast.unparse(fn)
        self.assertNotIn("'crm.lead'", body)
        self.assertIn("'res.company'", body)
        self.assertIn(NEW_XMLID, body)


if __name__ == '__main__':
    unittest.main()
