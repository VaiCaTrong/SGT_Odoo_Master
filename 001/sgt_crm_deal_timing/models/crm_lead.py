"""CRM-001 read-only indicators; no override of create(), write(), or CRM workflow."""

from collections import defaultdict

from odoo import api, fields, models

from .timeline import cumulative_stage_seconds, elapsed_full_days, stage_color_from_days


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sgt_crm001_visible = fields.Boolean(
        string='CRM-001 visible in this action',
        compute='_compute_sgt_crm001_visible',
    )
    sgt_crm001_stage_text = fields.Char(
        string='Time in Stage (CRM-001)',
        compute='_compute_sgt_crm001_timing',
    )
    sgt_crm001_total_text = fields.Char(
        string='Total Deal Age (CRM-001)',
        compute='_compute_sgt_crm001_timing',
    )
    sgt_crm001_stage_color = fields.Selection(
        selection=[
            ('green', 'Green (0–3 days)'),
            ('yellow', 'Yellow (4–7 days)'),
            ('red', 'Red (8+ days)'),
        ],
        string='Stage color (CRM-001)',
        compute='_compute_sgt_crm001_timing',
    )

    @api.depends_context('mm_approval_mode')
    def _compute_sgt_crm001_visible(self):
        # MM Approval Pipeline sends mm_approval_mode=True (confirmed in scan).
        # The shared Kanban/Form therefore keep their existing behavior in MM.
        show = not bool(self.env.context.get('mm_approval_mode'))
        for lead in self:
            lead.sgt_crm001_visible = show

    @api.depends_context('mm_approval_mode')
    @api.depends('stage_id', 'create_date', 'date_last_stage_update')
    def _compute_sgt_crm001_timing(self):
        if self.env.context.get('mm_approval_mode'):
            # The shared views still load invisible fields, but MM must not
            # trigger a history query or calculate these CRM-only indicators.
            for lead in self:
                lead.sgt_crm001_stage_text = False
                lead.sgt_crm001_total_text = False
                lead.sgt_crm001_stage_color = False
            return
        now = fields.Datetime.now()
        lead_ids = tuple(lead.id for lead in self if isinstance(lead.id, int))
        changes = defaultdict(list)
        if lead_ids:
            # Use the same two mail models as Odoo's standard duration_tracking.
            # Batch by record rather than querying Chatter once per Kanban card.
            self.env['mail.tracking.value'].flush_model()
            self.env['mail.message'].flush_model()
            self.env.cr.execute('''
                SELECT m.res_id, v.id, v.create_date, f.name,
                       v.old_value_integer, v.new_value_integer
                  FROM mail_tracking_value AS v
                  JOIN mail_message AS m ON m.id = v.mail_message_id
                  JOIN ir_model_fields AS f ON f.id = v.field_id
                 WHERE m.model = %s
                   AND m.res_id IN %s
                   AND f.model = %s
                   AND f.name = 'stage_id'
              ORDER BY m.res_id, v.create_date, v.id
            ''', ('crm.lead', lead_ids, 'crm.lead'))
            for res_id, row_id, timestamp, field, old, new in self.env.cr.fetchall():
                if timestamp:
                    changes[res_id].append({
                        'at': timestamp, 'id': row_id, 'field': field,
                        'old': old, 'new': new,
                    })

        for lead in self:
            if lead.create_date:
                total_seconds = (now - lead.create_date).total_seconds()
                lead.sgt_crm001_total_text = '%sd' % elapsed_full_days(total_seconds)
            else:
                lead.sgt_crm001_total_text = '—'

            # V03: Won / Lost / hand-off do NOT stop the counter.
            if not lead.stage_id:
                lead.sgt_crm001_stage_text = 'Stage: 0d'
                lead.sgt_crm001_stage_color = 'green'
            else:
                seconds = cumulative_stage_seconds(
                    created_at=lead.create_date,
                    now=now,
                    current_stage=lead.stage_id.id,
                    events=changes[lead.id],
                    last_stage_update=lead.date_last_stage_update,
                ).get(lead.stage_id.id, 0)
                stage_days = elapsed_full_days(seconds)
                lead.sgt_crm001_stage_text = 'Stage: %sd' % stage_days
                lead.sgt_crm001_stage_color = stage_color_from_days(stage_days)
