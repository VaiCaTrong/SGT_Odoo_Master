"""Run the REAL hand-off code (extracted from the source) against fake Odoo records.

No Odoo/Postgres here: this proves the decision logic (which rule fires, once,
never backwards, no copy, errors) but NOT ORM/view/migration behaviour, which
must be checked on Demo 2.
"""
import ast
import markupsafe
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import MethodType, SimpleNamespace
import unittest

MODELS = Path(__file__).resolve().parents[1] / 'models'


class FakeUserError(Exception):
    pass


class FakeValidationError(Exception):
    pass


def extract(path, class_name, names, extra_ns=None):
    tree = ast.parse((MODELS / path).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {
        'UserError': FakeUserError, 'ValidationError': FakeValidationError,
        'api': SimpleNamespace(model=lambda f: f, depends=lambda *a: (lambda f: f),
                               onchange=lambda *a: (lambda f: f), constrains=lambda *a: (lambda f: f)),
        'fields': SimpleNamespace(Datetime=SimpleNamespace(now=lambda: datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc))),
        '_logger': SimpleNamespace(warning=lambda *a, **k: None, info=lambda *a, **k: None),
        'APPLY_LIMIT': 500,
    }
    ns.update(extra_ns or {})
    exec(compile(ast.Module(body=funcs, type_ignores=[]), str(path), 'exec'), ns)
    return {n: ns[n] for n in names}


RULE_FUNCS = extract('handoff_rule.py', 'Crm002HandoffRule',
                     ['_lead_at_target', '_apply_to', '_run_for', '_run_for_safe',
                      '_column_label', '_log_handoff'],
                     extra_ns={'Markup': markupsafe.Markup})


class Funnel(SimpleNamespace):
    def sudo(self):
        return self


class Lead:
    def __init__(self, id, stage_seq=None, team=None, sale_funnel=None, type='opportunity'):
        self.id = id
        self.type = type
        self.team_id = team
        self.stage_id = SimpleNamespace(id=100 + (stage_seq or 0), sequence=stage_seq) if stage_seq is not None else None
        self.sgt_crm002_sale_funnel_id = sale_funnel
        self.sgt_crm002_sale_stage_id = None
        self.updates = []
        self.posted = []

    def sudo(self):
        return self

    def message_post(self, **kw):
        self.posted.append(kw)

    def _sgt_crm002_internal_update(self, vals):
        self.updates.append(dict(vals))
        if 'stage_id' in vals:
            self.stage_id = SimpleNamespace(id=vals['stage_id'], sequence=vals['stage_id'] - 100)
        if 'sgt_crm002_sale_funnel_id' in vals:
            self.sgt_crm002_sale_funnel_id = SALE[vals['sgt_crm002_sale_funnel_id']]
            self.sgt_crm002_sale_stage_id = vals['sgt_crm002_sale_stage_id']


MM = Funnel(id=5, group_key='mm', code='mm')
DATA = Funnel(id=1, group_key='data', code='hunter')
SALE_NEW = Funnel(id=7, group_key='sale', code='sale_new')
SALE_RENEW = Funnel(id=8, group_key='sale', code='sale_renew')
SALE = {7: SALE_NEW, 8: SALE_RENEW}
for _f, _n in ((MM, 'Match Making'), (DATA, 'Data Funnel'), (SALE_NEW, 'New'), (SALE_RENEW, 'Renew')):
    _f.name = _n


class FakeRule:
    def __init__(self, store, **kw):
        self.active = True
        self.target_crm_stage_id = None
        self.target_stage_id = None
        self.source_stage_id = None
        self.source_crm_stage_id = None
        self.summary = 'RULE-SUMMARY'
        self.__dict__.update(kw)
        self.target_group = self.target_funnel_id.group_key
        self.source_group = self.source_funnel_id.group_key
        self.store = store
        self.env = SimpleNamespace(cr=SimpleNamespace(savepoint=self._savepoint),
                                   user=SimpleNamespace(name='Trọng <b>', partner_id=SimpleNamespace(id=9)))
        for name, fn in RULE_FUNCS.items():
            setattr(self, name, MethodType(fn, self))

    @contextmanager
    def _savepoint(self):
        yield

    def ensure_one(self):
        pass

    def sudo(self):
        return self

    def search(self, domain, order=None):
        self.store.last_domain = domain
        src = next(c[2] for c in domain if c[0] == 'source_funnel_id')
        col = {c[0]: c[2] for c in domain if c[0] in ('source_stage_id', 'source_crm_stage_id')}
        return [r for r in self.store.rules if r.active and r.source_funnel_id.id == src
                and all(getattr(r, k).id == v for k, v in col.items())]


class Store:
    def __init__(self):
        self.rules = []

    def add(self, **kw):
        r = FakeRule(self, **kw)
        self.rules.append(r)
        return r


def runner(store):
    """Class-level `_run_for` bound to a dispatcher over the rules in `store`."""
    holder = FakeRule(store, source_funnel_id=DATA, target_funnel_id=MM)
    return holder


class HandoffRuleBehaviourTest(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.p_stage = SimpleNamespace(id=31, name='3.Potential')           # Data Funnel 3.Potential
        self.opp = SimpleNamespace(id=101, sequence=1, team_ids=[], name='1.Opportunity')
        self.approved = SimpleNamespace(id=106, sequence=6, team_ids=[], name='6.Approved Match Making')
        self.new_first = SimpleNamespace(id=71, name='1.Data')
        self.r1 = self.store.add(source_funnel_id=DATA, source_stage_id=self.p_stage,
                                 target_funnel_id=MM, target_crm_stage_id=self.opp)
        self.r2 = self.store.add(source_funnel_id=MM, source_crm_stage_id=self.approved,
                                 target_funnel_id=SALE_NEW, target_stage_id=self.new_first)
        self.run = runner(self.store)

    def test_potential_to_match_making_moves_same_lead(self):
        lead = Lead(1, stage_seq=None)
        moved = self.run._run_for(lead, DATA, stage=self.p_stage)
        self.assertEqual(moved, 1)
        self.assertEqual(lead.updates, [{'stage_id': 101}])
        self.assertEqual(lead.id, 1)  # same record: nothing created or copied

    def test_rule_is_idempotent(self):
        lead = Lead(1)
        self.run._run_for(lead, DATA, stage=self.p_stage)
        self.assertEqual(self.run._run_for(lead, DATA, stage=self.p_stage), 0)
        self.assertEqual(len(lead.updates), 1)

    def test_never_moves_a_lead_backwards(self):
        lead = Lead(1, stage_seq=4)  # already at 4, rule target is stage sequence 1
        self.assertEqual(self.run._run_for(lead, DATA, stage=self.p_stage), 0)
        self.assertEqual(lead.updates, [])
        self.assertEqual(lead.stage_id.sequence, 4)

    def test_approved_hands_over_to_sale_new_first_stage(self):
        lead = Lead(2, stage_seq=6)
        self.assertEqual(self.run._run_for(lead, MM, crm_stage=self.approved), 1)
        self.assertEqual(lead.updates, [{'sgt_crm002_sale_funnel_id': 7, 'sgt_crm002_sale_stage_id': 71}])
        self.assertIs(lead.sgt_crm002_sale_funnel_id, SALE_NEW)

    def test_sale_hand_off_runs_once(self):
        lead = Lead(2, stage_seq=6)
        self.run._run_for(lead, MM, crm_stage=self.approved)
        lead.sgt_crm002_sale_stage_id = 72  # the salesperson later moved it to another column
        self.assertEqual(self.run._run_for(lead, MM, crm_stage=self.approved), 0)
        self.assertEqual(lead.sgt_crm002_sale_stage_id, 72)

    def test_only_first_sale_rule_applies(self):
        self.store.add(sequence=30, source_funnel_id=MM, source_crm_stage_id=self.approved,
                       target_funnel_id=SALE_RENEW, target_stage_id=SimpleNamespace(id=81))
        lead = Lead(3, stage_seq=6)
        self.assertEqual(self.run._run_for(lead, MM, crm_stage=self.approved), 1)
        self.assertEqual(lead.sgt_crm002_sale_funnel_id, SALE_NEW)

    def test_inactive_rule_is_ignored(self):
        self.r2.active = False
        self.assertEqual(self.run._run_for(Lead(2, stage_seq=6), MM, crm_stage=self.approved), 0)

    def test_other_column_does_not_fire(self):
        other = SimpleNamespace(id=32)
        self.assertEqual(self.run._run_for(Lead(1), DATA, stage=other), 0)

    def test_no_column_no_run(self):
        self.assertEqual(self.run._run_for(Lead(1), DATA), 0)

    # ---- Update_014: hand-off is written into the Chatter ---------------------------------
    def test_handoff_posts_one_log_note(self):
        lead = Lead(1)
        self.run._run_for(lead, DATA, stage=self.p_stage)
        self.assertEqual(len(lead.posted), 1)
        post = lead.posted[0]
        self.assertEqual(post['message_type'], 'comment')
        self.assertEqual(post['subtype_xmlid'], 'mail.mt_note')      # a note: nobody is notified
        self.assertEqual(post['author_id'], 9)
        body = str(post['body'])
        self.assertIn('Data Funnel › 3.Potential', body)
        self.assertIn('Match Making › 1.Opportunity', body)
        self.assertIn('RULE-SUMMARY', body)
        self.assertIn('tự động', body)
        self.assertNotIn('thủ công', body)

    def test_user_name_is_escaped(self):
        lead = Lead(1)
        self.run._run_for(lead, DATA, stage=self.p_stage)
        body = str(lead.posted[0]['body'])
        self.assertIn('Trọng &lt;b&gt;', body)
        self.assertNotIn('Trọng <b>', body)

    def test_sale_target_names_funnel_and_column(self):
        lead = Lead(2, stage_seq=6)
        self.run._run_for(lead, MM, crm_stage=self.approved)
        body = str(lead.posted[0]['body'])
        self.assertIn('Match Making › 6.Approved Match Making', body)
        self.assertIn('New › 1.Data', body)

    def test_data_funnel_entry_already_at_target_is_still_noted(self):
        # Update_015: the Deal sits at 1.Opportunity already; entering Potential IS the hand-off.
        lead = Lead(1, stage_seq=1)
        self.assertEqual(self.run._run_for(lead, DATA, stage=self.p_stage), 0)     # nothing moved
        self.assertEqual(lead.updates, [])
        self.assertEqual(len(lead.posted), 1)
        body = str(lead.posted[0]['body'])
        self.assertIn('đã đứng sẵn ở cột đích', body)
        self.assertIn('Data Funnel › 3.Potential', body)
        self.assertIn('Match Making › 1.Opportunity', body)

    def test_moved_note_says_moved(self):
        lead = Lead(1)
        self.run._run_for(lead, DATA, stage=self.p_stage)
        self.assertIn('đã chuyển Deal sang cột đích', str(lead.posted[0]['body']))

    def test_other_sources_write_no_note_when_nothing_moves(self):
        lead = Lead(2, stage_seq=6)
        self.run._run_for(lead, MM, crm_stage=self.approved)
        self.assertEqual(len(lead.posted), 1)
        lead.sgt_crm002_sale_funnel_id = SALE_NEW                      # already in Sale: re-entry moves nothing
        self.run._run_for(lead, MM, crm_stage=self.approved)
        self.assertEqual(len(lead.posted), 1)                           # not noted again
        back = Lead(3, stage_seq=4)                                    # a Deal beyond the target stage, MM-sourced
        self.r2.target_funnel_id = MM
        self.r2.target_group = 'mm'
        self.r2.target_crm_stage_id = self.opp
        self.r2.source_crm_stage_id = self.approved
        self.run._run_for(back, MM, crm_stage=self.approved)
        self.assertEqual(back.posted, [])

    def test_manual_apply_is_labelled(self):
        lead = Lead(1)
        self.assertTrue(self.r1._apply_to(lead, manual=True))
        body = str(lead.posted[0]['body'])
        self.assertIn('áp dụng thủ công', body)
        self.assertNotIn('tự động', body)

    def test_chatter_failure_never_blocks_the_hand_off(self):
        lead = Lead(1)

        def boom(**kw):
            raise RuntimeError('chatter down')
        lead.message_post = boom
        self.assertEqual(self.run._run_for(lead, DATA, stage=self.p_stage), 1)
        self.assertEqual(lead.updates, [{'stage_id': 101}])

    def test_sales_team_mismatch_raises(self):
        self.opp.team_ids = [SimpleNamespace(id=9)]
        lead = Lead(1, team=SimpleNamespace(id=3, name='Team B'))
        with self.assertRaises(FakeUserError):
            self.run._run_for(lead, DATA, stage=self.p_stage)
        self.assertEqual(lead.updates, [])

    def test_safe_variant_swallows_and_leaves_lead_untouched(self):
        self.opp.team_ids = [SimpleNamespace(id=9)]
        lead = Lead(1, team=SimpleNamespace(id=3, name='Team B'))
        self.assertEqual(self.run._run_for_safe(lead, DATA, stage=self.p_stage), 0)
        self.assertEqual(lead.updates, [])

    def test_non_opportunity_lead_is_promoted_with_the_move(self):
        lead = Lead(1, type='lead')
        self.run._run_for(lead, DATA, stage=self.p_stage)
        self.assertEqual(lead.updates, [{'stage_id': 101, 'type': 'opportunity'}])


# ---------------------------------------------------------------- _transition_intake
TRANSITION = extract('service.py', 'Crm002Service', ['_transition_intake'])['_transition_intake']


class FakeRecordset:
    def __init__(self, item=None):
        self.item = item
        self.created, self.closed = [], []

    def sudo(self):
        return self

    def search(self, domain, limit=None):
        return self.item if limit else self

    def write(self, vals):
        self.closed.append(dict(vals))

    def create(self, vals):
        self.created.append(dict(vals))


class FakeBase:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def write(self, v):
        self.__dict__.update(v)


class FakeLead(FakeBase):
    _fields = {'sgt_crm002_step': SimpleNamespace(
        selection=[('data', '1.Data'), ('verified', '2.Verified'), ('potential', '3.Potential')])}

    def invalidate_recordset(self, f):
        pass

    def _sgt_crm002_log_stage_move(self, funnel_name, old, new):
        self.__dict__.setdefault('moves', []).append((funnel_name, old, new))

    def _sgt_crm002_internal_update(self, v):
        self.__dict__.update(v)


class FakeRuleModel:
    def __init__(self):
        self.calls = []

    def _run_for(self, lead, funnel, stage=None, crm_stage=None):
        self.calls.append((lead.id, funnel.id, getattr(stage, 'step_key', None)))
        return 1


class FakeEnv:
    def __init__(self, progress, stages):
        self.models = {
            'sgt.crm002.progress': FakeRecordset(progress),
            'sgt.crm002.stage.visit': FakeRecordset(),
            'sgt.crm002.funnel.stage': StageSearch(stages),
            'sgt.crm002.handoff.rule': FakeRuleModel(),
        }
        self.cr = SimpleNamespace(execute=lambda *a: None)

    def __getitem__(self, k):
        return self.models[k]


class StageSearch(FakeRecordset):
    def __init__(self, stages):
        super().__init__()
        self.stages = stages

    def search(self, domain, limit=None):
        key = next(c[2] for c in domain if c[0] == 'step_key')
        return self.stages.get(key)


class TransitionTest(unittest.TestCase):
    def setUp(self):
        class Fn(SimpleNamespace):
            def sudo(self):
                return self
        self.funnel = Fn(id=14, name='Outbound Hunter', stage_ids=[
            SimpleNamespace(step_key='data', name='1.Data'), SimpleNamespace(step_key='verified', name='2.Verified'),
            SimpleNamespace(step_key='potential', name='3.Potential')])
        self.progress = FakeBase(id=34, stage_key='verified', intake_active=True, completed_at=False)
        stages = {k: SimpleNamespace(id=i, step_key=k) for i, k in ((1, 'data'), (2, 'verified'), (3, 'potential'))}
        self.env = FakeEnv(self.progress, stages)
        self.lead = FakeLead(id=101, sgt_crm002_funnel_id=self.funnel, sgt_crm002_step='verified',
                             won_status=False, active=True)
        self.svc = SimpleNamespace(env=self.env, _check_funnel=lambda f: None)

    def go(self, step):
        return TRANSITION(self.svc, self.lead, step)

    def test_potential_marks_complete_and_runs_the_rules_for_that_column(self):
        self.go('potential')
        self.assertEqual(self.lead.sgt_crm002_step, 'potential')
        self.assertTrue(self.progress.completed_at)
        self.assertFalse(self.progress.intake_active)
        self.assertEqual(self.env['sgt.crm002.handoff.rule'].calls, [(101, 14, 'potential')])

    def test_service_never_writes_the_crm_stage_itself(self):
        self.go('potential')
        self.assertFalse(hasattr(self.lead, 'stage_id'))  # only the rule engine may move it

    def test_normal_step_runs_rules_of_that_column_only(self):
        self.lead.sgt_crm002_step = 'data'
        self.progress.stage_key = 'data'
        self.go('verified')
        self.assertEqual(self.env['sgt.crm002.handoff.rule'].calls, [(101, 14, 'verified')])
        self.assertTrue(self.progress.intake_active)

    def test_second_potential_is_idempotent_and_runs_nothing(self):
        self.go('potential')
        self.env['sgt.crm002.handoff.rule'].calls.clear()
        self.assertTrue(self.go('potential')['already_handed_off'])
        self.assertEqual(self.env['sgt.crm002.handoff.rule'].calls, [])

    def test_column_move_is_written_into_the_chatter(self):
        self.lead.sgt_crm002_step = 'data'
        self.progress.stage_key = 'data'
        self.go('verified')
        self.assertEqual(self.lead.moves, [('Outbound Hunter', '1.Data', '2.Verified')])
        self.go('potential')
        self.assertEqual(self.lead.moves[-1], ('Outbound Hunter', '2.Verified', '3.Potential'))

    def test_no_chatter_line_when_nothing_moves(self):
        self.go('potential')
        n = len(self.lead.moves)
        self.go('potential')                          # idempotent second request
        self.assertEqual(len(self.lead.moves), n)
        with self.assertRaises(FakeUserError):
            self.go('data')                           # refused drag back
        self.assertEqual(len(self.lead.moves), n)

    def test_cannot_drag_back_after_potential(self):
        self.go('potential')
        for step in ('data', 'verified'):
            with self.assertRaises(FakeUserError):
                self.go(step)

    def test_closed_deal_is_refused(self):
        self.lead.won_status = 'won'
        with self.assertRaises(FakeUserError):
            self.go('potential')
        self.assertEqual(self.env['sgt.crm002.handoff.rule'].calls, [])

    def test_rule_error_propagates_so_the_drag_is_rolled_back(self):
        def boom(*a, **k):
            raise FakeUserError('Team mismatch')
        self.env['sgt.crm002.handoff.rule']._run_for = boom
        with self.assertRaises(FakeUserError):
            self.go('potential')


if __name__ == '__main__':
    unittest.main()
