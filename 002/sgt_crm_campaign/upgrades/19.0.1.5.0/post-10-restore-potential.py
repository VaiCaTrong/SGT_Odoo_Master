"""Restore ONLY previously handed-off CRM-002 Deals to their Potential column.

Update_003 through Update_005 cleared the `crm.lead` intake linkage during
handoff, but they wrote a reliable `completed_at` on the progress record.
This migration restores that linkage only for unambiguous, completed handoffs.
Legacy Update_001/002 mass tag-matched progress has no completed_at and is
EXCLUDED. No crm.lead copy/creation, no core CRM stage changes.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # This runs ONLY on addon Upgrade, after models/columns have been loaded.
    # Ambiguous multi-funnel completions are deliberately left unchanged for
    # manual audit; never guess which intake funnel should own the Deal.
    cr.execute("""
        WITH completed_once AS (
            SELECT p.lead_id, MIN(p.funnel_id) AS funnel_id
              FROM sgt_crm002_progress AS p
              JOIN crm_lead AS l ON l.id = p.lead_id
             WHERE p.stage_key = 'potential'
               AND p.completed_at IS NOT NULL
               AND p.intake_active = FALSE
               AND l.sgt_crm002_funnel_id IS NULL
               AND l.sgt_crm002_step IS NULL
               AND l.type = 'opportunity'
             GROUP BY p.lead_id
            HAVING COUNT(*) = 1
        )
        UPDATE crm_lead AS l
           SET sgt_crm002_funnel_id = c.funnel_id,
               sgt_crm002_step = 'potential'
          FROM completed_once AS c
         WHERE l.id = c.lead_id
     RETURNING l.id
    """)
    restored_ids = [r[0] for r in cr.fetchall()]
    _logger.info('CRM-002 Update_006 restored %s completed handoffs to Potential (same CRM Deal IDs): %s',
                 len(restored_ids), restored_ids[:25])
