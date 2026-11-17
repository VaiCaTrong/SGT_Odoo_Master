"""Update_007 source-level contract. Runs without an Odoo server (NOT a substitute for one)."""
import ast
import csv
from pathlib import Path
import re
import unittest

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


class Update007ContractTest(unittest.TestCase):
    # ------------------------------------------------------------ packaging
    def test_version_hooks_and_upgrade_layout(self):
        manifest = ast.literal_eval(read('__manifest__.py'))
        self.assertEqual(manifest['version'], '19.0.1.26.0')
        self.assertEqual(manifest['post_init_hook'], 'post_init_hook')
        self.assertIn('from .hooks import post_init_hook', read('__init__.py'))
        for name in ('pre-10-group-key.py', 'post-10-seed.py'):
            self.assertTrue((ROOT / 'upgrades/19.0.1.6.1' / name).exists(), name)
        self.assertTrue((ROOT / 'upgrades/19.0.1.5.0/post-10-restore-potential.py').exists())
        pre = read('upgrades/19.0.1.6.1/pre-10-group-key.py')
        self.assertIn('ADD COLUMN IF NOT EXISTS group_key', pre)
        # Update_008: stale selection rows of the Selection->Char field must be dropped first.
        self.assertIn("f.model = 'sgt.crm002.funnel' AND f.name = 'code'", pre)
        self.assertIn('DELETE FROM ir_model_fields_selection', pre)
        self.assertLess(pre.index('DELETE FROM ir_model_fields_selection'), pre.index('ADD COLUMN IF NOT EXISTS group_key'))
        self.assertIn("WHEN code = 'mm' THEN 'mm' ELSE 'data'", pre)
        self.assertEqual(sorted(re.findall(r'DELETE FROM (\w+)', pre)), ['ir_model_data', 'ir_model_fields_selection'])
        self.assertNotIn('DROP', pre)

    def test_model_import_order(self):
        text = read('models/__init__.py')
        order = [text.index(n) for n in ('funnel', 'funnel_stage', 'handoff_rule', 'progress', 'service', 'crm_lead')]
        self.assertEqual(order, sorted(order))

    def test_acl_covers_new_models(self):
        rows = list(csv.DictReader(read('security/ir.model.access.csv').splitlines()))
        by_id = {r['id']: r for r in rows}
        self.assertEqual(by_id['access_crm002_rule_admin']['group_id:id'], 'base.group_system')
        self.assertEqual(by_id['access_crm002_stage_admin']['group_id:id'], 'base.group_system')
        user = by_id['access_crm002_stage_user']
        self.assertEqual((user['perm_read'], user['perm_write'], user['perm_create'], user['perm_unlink']),
                         ('1', '0', '0', '0'))
        # Rules and funnels are never readable by a normal user.
        for r in rows:
            if r['model_id:id'] in ('model_sgt_crm002_handoff_rule', 'model_sgt_crm002_funnel'):
                self.assertEqual(r['group_id:id'], 'base.group_system')

    # ------------------------------------------------------------ funnels
    def test_fixed_funnels_and_groups(self):
        tree = etree.parse(str(ROOT / 'data/funnel_data.xml'))
        funnels = {}
        for rec in tree.xpath('//record[@model="sgt.crm002.funnel"]'):
            vals = {f.get('name'): (f.text or '').strip() for f in rec.findall('field')}
            funnels[rec.get('id')] = vals
        self.assertEqual({k: v['group_key'] for k, v in funnels.items()}, {
            'funnel_hunter': 'data', 'funnel_pool': 'data', 'funnel_unverified': 'data', 'funnel_face': 'data',
            'funnel_sale_new': 'sale', 'funnel_sale_renew': 'sale', 'funnel_mm': 'mm'})
        self.assertEqual(funnels['funnel_sale_new']['name'], 'New')
        self.assertEqual(funnels['funnel_sale_renew']['name'], 'Renew')
        self.assertEqual(funnels['funnel_mm']['code'], 'mm')
        # Update_010: display name capitalised, tag/code stay lower case (routing by tag).
        self.assertEqual(funnels['funnel_hunter']['name'], 'Outbound Hunter')
        self.assertEqual(funnels['funnel_hunter']['code'], 'hunter')
        self.assertEqual(funnels['funnel_hunter']['initial_tag_name'], 'hunter')
        mig = read('upgrades/19.0.1.6.3/post-10-rename-hunter.py')
        self.assertIn("funnel.name == 'Outbound hunter'", mig)
        self.assertNotIn('initial_tag_name', mig)

    def test_only_data_funnel_can_be_created_by_admin(self):
        code = read('models/funnel.py')
        create = code[code.index('def create('):code.index('def write(')]
        self.assertIn('if not self.env.su:', create)
        self.assertIn("vals.get('group_key', 'data') != 'data'", create)
        self.assertIn('Chỉ được tạo phễu mới trong Data Funnel', create)
        unlink = code[code.index('def unlink('):code.index('# ---------------------------------------------------------- default content')]
        self.assertIn('if not self.env.su:', unlink)
        self.assertIn("group_key = fields.Selection(GROUP_KEYS, required=True", code)
        self.assertEqual(re.findall(r"\('(\w+)', '[^']+'\),", code[code.index('GROUP_KEYS = ['):code.index('STEP_KEYS')]),
                         ['data', 'sale', 'mm'])

    def test_stage_names_are_exact_never_stripped(self):
        code = read('models/funnel.py')
        self.assertIn("DEFAULT_ENTRY_STAGE_NAMES = ('1.Opportunity', '4.Opportunity')", code)
        self.assertIn("DEFAULT_APPROVED_STAGE_NAMES = ('6.Approved Match Making',)", code)
        finder = code[code.index('def _sgt_find_crm_stage('):code.index('def _sgt_ensure_default_rules(')]
        self.assertIn("(s.name or '').strip() == w", finder)
        for banned in ('re.sub', 'lstrip', 'ilike', 'lower()', 'split('):
            self.assertNotIn(banned, finder)
        self.assertNotIn('_potential_stage', read('models/service.py'))
        self.assertNotIn('4.Opportunity', read('models/service.py'))

    # ------------------------------------------------------------ hand-off
    def test_handoff_uses_same_lead_no_copy(self):
        for name in ('models/handoff_rule.py', 'models/service.py', 'models/crm_lead.py'):
            code = read(name)
            self.assertNotIn('.copy(', code, name)
            self.assertNotIn('unlink()', code.replace('def unlink(self)', ''), name)
        rule = read('models/handoff_rule.py')
        self.assertIn('lead._sgt_crm002_internal_update(values)', rule)
        self.assertIn('same crm.lead', rule.lower())

    def test_rule_is_idempotent_and_no_backwards(self):
        rule = read('models/handoff_rule.py')
        self.assertIn('if self._lead_at_target(lead):', rule)
        self.assertIn('lead.stage_id.sequence >= self.target_crm_stage_id.sequence', rule)
        self.assertIn("'|', ('stage_id', '=', False), ('stage_id.sequence', '<', self.target_crm_stage_id.sequence)", rule)

    def test_apply_existing_button_is_admin_only_and_bounded(self):
        rule = read('models/handoff_rule.py')
        body = rule[rule.index('def action_apply_existing('):]
        self.assertIn('_check_admin()', body)
        self.assertIn('savepoint()', body)
        self.assertIn('APPLY_LIMIT', body)
        self.assertIn('soft_reload', body)

    def test_transition_runs_rules_inside_the_same_transaction(self):
        svc = read('models/service.py')
        body = svc[svc.index('def _transition_intake('):]
        self.assertIn("self.env['sgt.crm002.handoff.rule']._run_for(", body)
        self.assertIn('FOR UPDATE', body)
        self.assertIn("'completed_at': now", body)
        self.assertNotIn("'sgt_crm002_funnel_id': False", body)
        self.assertLess(body.index("'completed_at': now"), body.index('._run_for('))

    def test_match_making_hook_never_blocks_the_user(self):
        lead = read('models/crm_lead.py')
        self.assertIn('_run_for_safe(lead, mm, crm_stage=lead.stage_id)', lead)
        self.assertIn('_run_for_safe(lead, funnel, stage=stage)', lead)
        self.assertIn('savepoint()', read('models/handoff_rule.py'))

    def test_membership_cannot_be_edited_from_forms(self):
        lead = read('models/crm_lead.py')
        w = lead[lead.index('    def write('):lead.index('def _sgt_crm002_plain_write(')]
        self.assertIn("'sgt_crm002_funnel_id', 'sgt_crm002_sale_funnel_id'", w)
        self.assertIn('raise AccessError', w)
        c = lead[lead.index('def create('):lead.index('def _sgt_crm002_internal_update(')]
        self.assertIn("vals.pop('sgt_crm002_sale_funnel_id', None)", c)
        self.assertIn("vals.pop('sgt_crm002_sale_stage_id', None)", c)

    def test_data_funnel_target_rejected(self):
        self.assertIn("if target.group_key == 'data':", read('models/handoff_rule.py'))

    def test_service_sudo_for_funnel_reads(self):
        svc = read('models/service.py')
        allowed = svc[svc.index('def _allowed('):svc.index('def _check_funnel(')]
        self.assertIn('funnel = funnel.sudo()', allowed)

    # ------------------------------------------------------------ views / sidebar
    def test_sale_kanban_reuses_native_card(self):
        xml = read('views/intake_kanban.xml')
        self.assertIn('view_crm002_sale_kanban', xml)
        self.assertIn('default_group_by">sgt_crm002_sale_stage_id', xml)
        self.assertNotIn('t-name="card"', xml)

    def test_settings_permissions_and_rules_actions(self):
        xml = read('views/funnel_views.xml')
        for xmlid in ('action_crm002_permissions', 'action_crm002_funnel_config', 'action_crm002_rules',
                      'view_crm002_rule_form', 'view_crm002_funnel_permission_list'):
            self.assertIn('id="%s"' % xmlid, xml)
        self.assertIn('name="action_apply_existing"', xml)
        menu = read('views/menu.xml')
        for xmlid in ('menu_crm002_permissions', 'menu_crm002_rules', 'menu_crm002_funnel_config'):
            self.assertIn(xmlid, menu)
        self.assertEqual(menu.count('groups="base.group_system"'), 3)

    def test_sidebar_has_exactly_two_action_buttons(self):
        xml = read('static/src/xml/native_pipeline.xml')
        self.assertEqual(xml.count('sgt002-native-btn'), 2)
        self.assertIn('Permissions', xml)
        self.assertIn('Settings', xml)
        self.assertNotIn('Phân quyền', xml)
        self.assertNotIn('Cài đặt', xml)
        self.assertNotIn('Cấu hình phễu', xml)
        self.assertIn('crm002ToggleCollapse', xml)

    def test_sidebar_js(self):
        js = read('static/src/js/native_pipeline.js')
        self.assertIn('action_crm002_permissions', js)
        self.assertIn('action_crm002_funnel_config', js)
        self.assertIn('crm002ToggleCollapse', js)
        for fn in ('readCollapsed', 'writeCollapsed'):
            body = js[js.index('function %s' % fn):]
            self.assertIn('try {', body[:300])
            self.assertIn('catch', body[:400])
        self.assertIn('data.groups', js)

    def test_sidebar_logo_is_small_and_css_is_plain(self):
        css = read('static/src/scss/workspace.scss')
        width = int(re.search(r'sgt002-native-brand-logo \{[^}]*width: (\d+)px', css).group(1))
        self.assertLessEqual(width, 48)  # was 122px in Update_006
        self.assertIn('.sgt002-collapsed', css)
        self.assertNotIn('$', css)
        self.assertNotIn('@include', css)
        self.assertNotIn('o_kanban_record', css)
        self.assertEqual(css.count('{'), css.count('}'))
        # Update_009: flat look, no borders on sidebar buttons, bottom buttons never wrap.
        self.assertNotIn('border: 1px', css.split('sgt002-native-top')[1].split('.sgt002-native-dept')[0])
        self.assertIn('white-space: nowrap', css)
        self.assertIn('flex-wrap: wrap', css)  # narrow screens stack the buttons, text never breaks

    def test_no_crm005_fields(self):
        for f in ROOT.rglob('*.py'):
            if 'tests' in f.parts:
                continue
            text = f.read_text()
            self.assertNotIn('yellowpages', text.lower(), f.name)
            # Update_026: yp_utils.py only lists field NAMES (white list for the extension); every name
            # is checked against the real model at run time, so there is still no dependency on CRM-005.
            if f.name != 'yp_utils.py':
                self.assertNotIn('x_image', text, f.name)

    def test_python_xml_all_parse(self):
        for f in ROOT.rglob('*.py'):
            ast.parse(f.read_text())
        for f in ROOT.rglob('*.xml'):
            etree.parse(str(f))


if __name__ == '__main__':
    unittest.main()
