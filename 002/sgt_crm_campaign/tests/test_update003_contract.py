"""Offline structural regression checks; NOT a substitute for an Odoo server test."""
from pathlib import Path
from lxml import etree
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Update003ContractTest(unittest.TestCase):
    def test_native_kanban_card_is_inherited_not_replaced(self):
        data = (ROOT / 'views/intake_kanban.xml').read_text()
        self.assertIn('crm.crm_case_kanban_view_leads', data)
        self.assertIn('sgt_crm002_step', data)
        self.assertNotIn("<t t-name=\"card\"", data)

    def test_intake_queue_is_not_a_live_tag_search(self):
        code = (ROOT / 'models/service.py').read_text()
        section = code[code.index('def open_intake('):code.index('def _activate_progress(')]
        self.assertIn("('sgt_crm002_funnel_id', '=', funnel.id)", section)
        self.assertNotIn('_tag_or_source_domain', section)

    def test_create_only_routing(self):
        code = (ROOT / 'models/crm_lead.py').read_text()
        self.assertIn('def create(', code)
        self.assertIn('def _sgt_crm002_matching_funnel(', code)
        self.assertNotIn('_sgt_crm002_matching_funnel(lead)', code[code.index('def write('):])

    def test_potential_promotion_preserves_membership_update006(self):
        code = (ROOT / 'models/service.py').read_text()
        section = code[code.index('def _transition_intake('):]
        self.assertIn("'sgt_crm002_step': 'potential'", section)
        self.assertNotIn("'sgt_crm002_step': False", section)
        self.assertNotIn("'sgt_crm002_funnel_id': False", section)
        self.assertIn("'intake_active': False", section)
        self.assertIn("'completed_at': now", section)
        self.assertNotIn('lead.copy(', section)

    def test_parent_collapse_both_groups(self):
        t = (ROOT / 'static/src/xml/native_pipeline.xml').read_text()
        # Update_007: groups are rendered from the server (Data Funnel / Sale / Match Making).
        self.assertIn("crm002ToggleGroup(group.key)", t)
        self.assertIn('t-foreach="crm002State.groups"', t)

    def test_new_intake_records_are_not_legacy_rows(self):
        text = (ROOT / 'models/progress.py').read_text()
        self.assertIn('intake_active = fields.Boolean(default=False', text)
        self.assertIn('completed_at = fields.Datetime(', text)

    def test_admin_only_directory_and_config(self):
        code = (ROOT / 'models/service.py').read_text()
        self.assertIn('self._check_admin()', code)
        self.assertIn("base.group_system", code)

    def test_python_xml_all_parse(self):
        for file in ROOT.rglob('*.py'):
            ast.parse(file.read_text())
        for file in ROOT.rglob('*.xml'):
            etree.parse(str(file))


if __name__ == '__main__':
    unittest.main()
