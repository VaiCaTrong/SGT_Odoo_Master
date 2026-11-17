"""Update_029: the CRM app icon stays visible to a user whose Sales field is "No"; clicking it opens the empty page.

User, 02/11 15:50: "thay vì ẩn luôn cả CRM khi không có quyền thì tôi muốn vẫn để đó nhưng bấm vào CRM thì không có dữ liệu".

How Odoo 19 decides (odoo/addons/base/models/ir_ui_menu.py `_visible_menu_ids` / `load_menus`, read from GitHub 19.0):
  1. keep the menus with no group, or with a group the user has;
  2. of those, only ACTION menus count, and only if the user may READ the action's model
     (server action -> its model_id, act_window -> res_model);
  3. a menu is visible when it is such an action menu, plus its ancestors that passed step 1;
  4. load_menus drops every menu that is not reachable from a root menu through visible parents.
So a folder is shown only when an action menu below it is openable, and a root menu with no group the user has is hidden.

This test copies that algorithm (not real Odoo) and runs it on the stock Odoo 19 CRM menu tree (addons/crm/views/crm_menu_views.xml)
with the overrides that views/landing.xml really contains (parsed from the XML, so breaking the XML turns it red).
Not covered (check on Demo 2): the real web client, `ir.actions.server` rights at run time.
"""
import ast
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XML = (ROOT / 'views' / 'landing.xml').read_text()

G_USER, G_SYSTEM = 'base.group_user', 'base.group_system'
G_OWN, G_ALL, G_ADMIN = ('sales_team.group_sale_salesman', 'sales_team.group_sale_salesman_all_leads',
                         'sales_team.group_sale_manager')
G_LEAD = 'crm.group_use_lead'

# model -> groups with read access (stock Odoo 19 ACL; crm.team and res.partner: base.group_user)
READ = {
    'crm.team': {G_USER}, 'res.partner': {G_USER}, 'res.company': {G_USER},
    'crm.lead': {G_OWN, G_ADMIN},          # access_crm_lead (salesman) and access_crm_lead_manager; All Documents implies salesman
}
LANDING = ('server', 'crm.team')           # action_crm002_landing: model_id = crm.team


def stock_menus():
    """Odoo 19 crm_menu_views.xml (only the shape that matters: parent, groups, action model)."""
    return {
        'root': dict(parent=None, groups={G_OWN, G_ADMIN}, action=None),
        'sales': dict(parent='root', groups=set(), action=None),
        'pipeline': dict(parent='sales', groups=set(), action=('server', 'crm.team')),       # crm.action_your_pipeline
        'activities': dict(parent='sales', groups={G_OWN}, action=('act', 'crm.lead')),
        'teams': dict(parent='sales', groups=set(), action=('act', 'crm.team')),
        'customers': dict(parent='sales', groups=set(), action=('act', 'res.partner')),
        'leads': dict(parent='root', groups={G_LEAD}, action=('act', 'crm.lead')),
        'report': dict(parent='root', groups={G_OWN}, action=None),
        'forecast': dict(parent='report', groups=set(), action=('act', 'crm.lead')),
        'config': dict(parent='root', groups={G_ADMIN}, action=('server', 'crm.team')),
        'config_settings': dict(parent='config', groups={G_SYSTEM}, action=('act', 'res.config.settings')),
    }


def can_read(model, groups):
    if model not in READ:
        return False
    return bool(READ[model] & groups)


def visible_for(menus, groups):
    """Copy of ir.ui.menu._visible_menu_ids + the 'reachable from a root' filter of load_menus."""
    passing = {k for k, m in menus.items() if not m['groups'] or (m['groups'] & groups)}
    visible = set()
    for key in menus:
        if key not in passing:
            continue
        action = menus[key]['action']
        if not action:
            continue
        if not can_read(action[1], groups):
            continue
        cur = key
        while cur is not None and cur not in visible and cur in passing:
            visible.add(cur)
            cur = menus[cur]['parent']
    reachable = set()
    for key in visible:
        cur, ok = key, True
        while cur is not None:
            if cur not in visible:
                ok = False
                break
            cur = menus[cur]['parent']
        if ok:
            reachable.add(key)
    return reachable


def refs(expr):
    return re.findall(r"ref\('([^']+)'\)", expr)


def record(xmlid):
    root = ET.fromstring(XML)
    return next(r for r in root.iter('record') if r.get('id') == xmlid)


def field(rec, name):
    return next((f for f in rec.findall('field') if f.get('name') == name), None)


def with_overrides(menus):
    """Apply what views/landing.xml says about the CRM menus."""
    root_rec = record('crm.crm_menu_root')
    groups = field(root_rec, 'group_ids').get('eval')
    assert groups.startswith('[(4,'), groups                      # ADD base.group_user, do not replace the stock groups
    menus['root']['groups'] = menus['root']['groups'] | set(refs(groups))
    action = field(root_rec, 'action').get('eval')
    assert 'action_crm002_landing' in action
    menus['root']['action'] = LANDING
    sales_rec = record('crm.crm_menu_sales')
    sales = field(sales_rec, 'group_ids').get('eval')
    menus['sales']['groups'] = set(refs(sales))
    pipe = field(record('crm.menu_crm_opportunities'), 'action').get('eval')
    assert 'action_crm002_landing' in pipe
    menus['pipeline']['action'] = LANDING
    return menus


NO = frozenset({G_USER})
OWN = NO | {G_OWN}
ALL = OWN | {G_ALL}
SALES_ADMIN = ALL | {G_ADMIN}
ROLE_ADMIN = NO | {G_SYSTEM}                # Role Administrator does not carry Sales groups
ROLE_ADMIN_SALES_ADMIN = SALES_ADMIN | {G_SYSTEM}


class StockOdooHidesCrmWhenSalesIsNo(unittest.TestCase):
    def test_the_model_reproduces_the_stock_behaviour(self):
        """Without Update_029 the CRM app is not shown to Sales = No (what the user saw)."""
        stock = stock_menus()
        self.assertEqual(visible_for(stock, NO), set())
        self.assertEqual(visible_for(stock, ROLE_ADMIN), set())
        self.assertIn('root', visible_for(stock, OWN))
        self.assertIn('config', visible_for(stock, SALES_ADMIN))


class AfterUpdate029(unittest.TestCase):
    def setUp(self):
        self.menus = with_overrides(stock_menus())

    def test_sales_no_sees_the_crm_app_and_nothing_below_it(self):
        self.assertEqual(visible_for(self.menus, NO), {'root'})

    def test_leads_setting_on_does_not_open_the_leads_menu_for_sales_no(self):
        """Settings > Leads gives every internal user group_use_lead; the Leads menu is a crm.lead action, so still hidden."""
        self.assertEqual(visible_for(self.menus, NO | {G_LEAD}), {'root'})

    def test_role_administrator_without_sales_gets_the_same_icon_only(self):
        self.assertEqual(visible_for(self.menus, ROLE_ADMIN), {'root'})

    def test_own_documents_keeps_every_menu_it_had_before(self):
        before = visible_for(stock_menus(), OWN)
        after = visible_for(self.menus, OWN)
        self.assertTrue(before <= after)
        self.assertEqual(after - before, set())
        self.assertNotIn('config', after)

    def test_every_sales_level_keeps_exactly_the_menus_it_had_before(self):
        for groups in (OWN, ALL, SALES_ADMIN, ROLE_ADMIN_SALES_ADMIN):
            self.assertEqual(visible_for(stock_menus(), groups), visible_for(self.menus, groups), sorted(groups))

    def test_sales_no_never_sees_teams_customers_or_reports(self):
        seen = visible_for(self.menus, NO)
        for hidden in ('sales', 'pipeline', 'activities', 'teams', 'customers', 'leads', 'report', 'forecast', 'config'):
            self.assertNotIn(hidden, seen)

    def test_the_root_action_is_readable_by_every_internal_user(self):
        action = self.menus['root']['action']
        self.assertEqual(action, ('server', 'crm.team'))
        self.assertTrue(can_read(action[1], NO))

    def test_if_the_root_lost_its_own_action_the_icon_would_disappear(self):
        menus = with_overrides(stock_menus())
        menus['root']['action'] = None
        self.assertEqual(visible_for(menus, NO), set())

    def test_if_the_sales_folder_stayed_open_users_without_sales_would_see_other_menus(self):
        menus = with_overrides(stock_menus())
        menus['sales']['groups'] = set()
        seen = visible_for(menus, NO)
        self.assertIn('customers', seen)      # contacts under CRM: exactly what the folder restriction prevents


class LandingServerAction(unittest.TestCase):
    def test_every_internal_user_may_run_it(self):
        """Odoo 19 `_can_execute_action_on_records`: no group on the action -> WRITE access on its model is needed
        (crm.team: Sales Administrator only).  The stock "Crm: My Pipeline" action carries base.group_user; so must ours."""
        rec = record('action_crm002_landing')
        groups = field(rec, 'group_ids')
        self.assertIsNotNone(groups)
        self.assertEqual(refs(groups.get('eval')), [G_USER])

    def test_its_model_is_crm_team_which_base_group_user_can_read(self):
        rec = record('action_crm002_landing')
        self.assertEqual(refs(field(rec, 'model_id').get('ref') and "ref('%s')" % field(rec, 'model_id').get('ref')),
                         ['sales_team.model_crm_team'])
        self.assertTrue(can_read('crm.team', NO))


class Wiring(unittest.TestCase):
    def test_version(self):
        m = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(m['version'], '19.0.1.26.0')
        self.assertIn('views/landing.xml', m['data'])

    def test_no_other_view_or_menu_of_the_addon_opens_the_sales_folder_again(self):
        for path in (ROOT / 'views').glob('*.xml'):
            text = path.read_text()
            if path.name == 'landing.xml':
                continue
            self.assertNotIn('crm.crm_menu_sales"', text.replace('parent="crm.crm_menu_sales"', ''), path.name)


if __name__ == '__main__':
    unittest.main()
