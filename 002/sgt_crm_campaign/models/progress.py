"""Progress is per lead+funnel, independent of Odoo's main CRM stage.
Each visit stores a time interval. Re-entry adds a new interval rather than resetting time.
"""
from odoo import fields, models

STAGES = [('data', '1.Data'), ('verified', '2.Verified'), ('potential', '3.Potential')]


class Crm002Progress(models.Model):
    _name = 'sgt.crm002.progress'
    _description = 'CRM-002 Lead Funnel Progress'
    _order = 'id'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade', index=True)
    funnel_id = fields.Many2one('sgt.crm002.funnel', required=True, ondelete='cascade', index=True)
    stage_key = fields.Selection(STAGES, default='data', required=True)
    # True means still being processed in Data/Verified. Upon handoff,
    # completed_at is set and the Deal stays VISIBLE at Potential via crm.lead.
    intake_active = fields.Boolean(default=False, index=True, copy=False, string='CRM-002 pending intake')
    intake_created_at = fields.Datetime(copy=False)
    completed_at = fields.Datetime(copy=False)
    visit_ids = fields.One2many('sgt.crm002.stage.visit', 'progress_id')
    _sql_constraints = [
        ('sgt_crm002_lead_funnel_unique', 'unique(lead_id,funnel_id)', 'Lead progress already exists for this funnel.'),
    ]


class Crm002StageVisit(models.Model):
    _name = 'sgt.crm002.stage.visit'
    _description = 'CRM-002 Stage Visit Interval'
    _order = 'started_at, id'

    progress_id = fields.Many2one('sgt.crm002.progress', required=True, ondelete='cascade', index=True)
    stage_key = fields.Selection(STAGES, required=True)
    started_at = fields.Datetime(required=True)
    ended_at = fields.Datetime()
