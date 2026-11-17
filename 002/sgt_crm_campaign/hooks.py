"""Idempotent default content for CRM-002 (install AND upgrade).

Creates, only if missing:
  * the default columns of every funnel (Data Funnel: 3 fixed; Sale: ``1.Data``);
  * Data Funnel ``3.Potential``  -> Match Making ``1.Opportunity``   (old behaviour);
  * Match Making ``6.Approved Match Making`` -> Sale/New ``1.Data``.
CRM stages are found by their EXACT name (no number stripping, no fuzzy match).
If a CRM stage does not exist the rule is skipped (warning in the log) and the
Administrator creates it in Settings.  Existing rules are never touched.
"""
import logging

from .models.funnel import DEFAULT_APPROVED_STAGE_NAMES, DEFAULT_SALE_FIRST_STAGE

_logger = logging.getLogger(__name__)


def _seed_sale_rule(env):
    Funnel = env['sgt.crm002.funnel'].sudo().with_context(active_test=False)
    Rule = env['sgt.crm002.handoff.rule'].sudo().with_context(active_test=False)
    mm = Funnel.search([('group_key', '=', 'mm')], limit=1)
    new = Funnel.search([('code', '=', 'sale_new')], limit=1)
    approved = Funnel._sgt_find_crm_stage(DEFAULT_APPROVED_STAGE_NAMES)
    first = env['sgt.crm002.funnel.stage'].sudo().search(
        [('funnel_id', '=', new.id), ('name', '=', DEFAULT_SALE_FIRST_STAGE)], limit=1) if new else False
    if not (mm and new and approved and first):
        _logger.warning('CRM-002: default rule "%s -> Sale/New %s" not created (missing funnel or CRM stage).',
                        DEFAULT_APPROVED_STAGE_NAMES[0], DEFAULT_SALE_FIRST_STAGE)
        return
    if Rule.search_count([('source_funnel_id', '=', mm.id), ('source_crm_stage_id', '=', approved.id),
                          ('target_funnel_id', '=', new.id)]):
        return
    Rule.create({
        'sequence': 20, 'source_funnel_id': mm.id, 'source_crm_stage_id': approved.id,
        'target_funnel_id': new.id, 'target_stage_id': first.id,
    })


def seed_defaults(env):
    Funnel = env['sgt.crm002.funnel'].sudo().with_context(active_test=False)
    funnels = Funnel.search([])
    funnels._sgt_ensure_default_stages()
    funnels.filtered(lambda f: f.group_key == 'data')._sgt_ensure_default_rules()
    _seed_sale_rule(env)


def post_init_hook(env):
    seed_defaults(env)
