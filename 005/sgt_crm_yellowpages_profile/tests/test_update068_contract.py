"""Update_068 static contract: MM Approval box + red approve button on the deal form; green success message.

Run: python3 -I tests/test_update068_contract.py
Real-Odoo behaviour (stage 5 / rights / click / upgrade from 067) was run in a scratch Odoo 19 database
with a fake XML-RPC Odoo SGT; see UPDATE_068_NOTES.md.
"""
import ast
import re
import types
import unittest
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ast.literal_eval((ROOT / '__manifest__.py').read_text())
VIEW = etree.parse(str(ROOT / 'views/mm_approve_box.xml'))
SEC = etree.parse(str(ROOT / 'security/mm_admin_implied.xml'))
PY = (ROOT / 'models/mm_approval_button.py').read_text()
CSS = (ROOT / 'static/src/css/mm_approve_box.css').read_text()
CRM_LEAD_PY = (ROOT / 'models/crm_lead.py').read_text()


class Manifest(unittest.TestCase):
    def test_version_depends_data_assets(self):
        self.assertEqual(MANIFEST['version'], '19.0.1.67.0')
        self.assertIn('crm_mm_approval_bridge', MANIFEST['depends'])
        data = MANIFEST['data']
        for f in ('security/mm_admin_implied.xml', 'views/mm_approve_box.xml'):
            self.assertIn(f, data)
        # the box view inherits the 005 form view, so it must load after it
        self.assertLess(data.index('views/crm_yp_lead_form.xml'), data.index('views/mm_approve_box.xml'))
        self.assertIn('sgt_crm_yellowpages_profile/static/src/css/mm_approve_box.css', MANIFEST['assets']['web.assets_backend'])

    def test_models_import_and_crm_lead_untouched(self):
        self.assertIn('from . import mm_approval_button', (ROOT / 'models/__init__.py').read_text())
        self.assertNotIn('action_crm005_approve_mm', CRM_LEAD_PY)   # test_update062 pins the hash of crm_lead.py


class BoxView(unittest.TestCase):
    def setUp(self):
        self.box = VIEW.xpath("//div[contains(@class,'sgt_mm_approve_box')]")[0]

    def test_inherits_005_form_and_sits_above_title(self):
        rec = VIEW.xpath("//record[@model='ir.ui.view']")[0]
        self.assertEqual(rec.xpath("field[@name='inherit_id']/@ref")[0], 'view_crm005_yellowpages_lead_form')
        xp = VIEW.xpath('//xpath')[0]
        self.assertEqual(xp.get('position'), 'before')
        self.assertIn("hasclass('oe_title')", xp.get('expr'))

    def test_only_approvers(self):
        self.assertEqual(self.box.get('groups'), 'crm_mm_approval_bridge.group_mm_approver')

    def test_visibility_rule(self):
        inv = self.box.get('invisible')
        for part in ('not x_mm_stage_allowed', 'x_mm_approved', 'x_mm_remote_id', "type != 'opportunity'", "context.get('mm_approval_mode')"):
            self.assertIn(part, inv)
        names = {f.get('name') for f in VIEW.xpath('//field')}
        self.assertTrue({'x_mm_stage_allowed', 'x_mm_approved', 'x_mm_remote_id'} <= names)

    def test_button_and_no_caption_line(self):
        btn = self.box.xpath('.//button')[0]
        self.assertEqual(btn.get('name'), 'action_crm005_approve_mm')
        self.assertEqual(btn.get('type'), 'object')
        self.assertIn('btn-danger', btn.get('class'))
        self.assertEqual(btn.get('string'), 'Phê Duyệt & Tạo MM')
        text = ''.join(self.box.itertext())
        self.assertIn('MM Approval', text)
        self.assertNotIn('Review CRM', text)            # user 13:58: the caption line is removed
        self.assertFalse(self.box.xpath(".//*[contains(@class,'sgt_mm_approve_sub')]"))
        self.assertNotIn('sgt_mm_approve_sub', CSS)

    def test_css_plain(self):
        self.assertIn('.sgt_mm_approve_box', CSS)
        self.assertIn('display: flex', CSS)
        self.assertIn('justify-content: space-between', CSS)


class AdminGroup(unittest.TestCase):
    def test_system_implies_mm_manager(self):
        rec = SEC.xpath("//record[@id='base.group_system'][@model='res.groups']")[0]
        ev = rec.xpath("field[@name='implied_ids']/@eval")[0]
        self.assertIn('crm_mm_approval_bridge.group_mm_manager', ev)


class Wrapper(unittest.TestCase):
    """Run the real method body with a stand-in self: it must call the bridge's action_approve_mm once,
    and return a green (success) notification followed by soft_reload."""

    def run_method(self, fail=False):
        import sys
        src = PY.replace('from odoo import _, models', '_ = lambda s: s\nclass models:\n    class Model: pass')
        ns = {}
        exec(compile(src, 'mm_approval_button.py', 'exec'), ns)
        cls = ns['CrmLeadMmApprovalButton']
        calls = []

        class Stage:
            display_name = '6.Approved Match Making'
        me = types.SimpleNamespace(x_mm_remote_id=312, stage_id=Stage())
        me.ensure_one = lambda: calls.append('ensure_one')

        def approve():
            calls.append('approve')
            if fail:
                raise ValueError('boom')
        me.action_approve_mm = approve
        return calls, lambda: cls.action_crm005_approve_mm(me)

    def test_success(self):
        calls, run = self.run_method()
        out = run()
        self.assertEqual(calls, ['ensure_one', 'approve'])
        self.assertEqual(out['tag'], 'display_notification')
        p = out['params']
        self.assertEqual(p['type'], 'success')
        self.assertIn('312', p['message'])
        self.assertIn('6.Approved Match Making', p['message'])
        self.assertEqual(p['next'], {'type': 'ir.actions.client', 'tag': 'soft_reload'})
        self.assertFalse(p['sticky'])

    def test_failure_is_not_swallowed(self):
        calls, run = self.run_method(fail=True)
        with self.assertRaises(ValueError):
            run()   # no success message when the approval fails


if __name__ == '__main__':
    unittest.main()
