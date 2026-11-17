"""Columns (stages) of a CRM-002 funnel.

* Data Funnel: three FIXED columns (1.Data / 2.Verified / 3.Potential); the
  ``step_key`` ties each column to ``crm.lead.sgt_crm002_step``.
* Sale funnels (New, Renew): free columns edited by the Administrator.
* Match Making has no rows here: its columns are the native CRM stages.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError

from .funnel import STEP_KEYS


class Crm002FunnelStage(models.Model):
    _name = 'sgt.crm002.funnel.stage'
    _description = 'CRM-002 Funnel Stage (column)'
    _order = 'funnel_id, sequence, id'

    funnel_id = fields.Many2one('sgt.crm002.funnel', required=True, ondelete='cascade', index=True)
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    step_key = fields.Selection(STEP_KEYS, copy=False,
                                help='Only for the three fixed Data Funnel columns.')
    group_key = fields.Selection(related='funnel_id.group_key', string='Funnel group')

    _sql_constraints = [
        ('sgt_crm002_stage_name_unique', 'unique(funnel_id, name)', 'Stage name must be unique inside a funnel.'),
    ]

    # Only Sale-funnel stages may be edited by a normal Administrator; the Data
    # Funnel columns are fixed because the hand-off at 3.Potential relies on them.
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            funnels = self.env['sgt.crm002.funnel'].sudo().browse(
                [v['funnel_id'] for v in vals_list if v.get('funnel_id')])
            if any(f.group_key != 'sale' for f in funnels) or any(v.get('step_key') for v in vals_list):
                raise UserError('CRM-002: Chỉ thêm được stage cho phễu thuộc nhóm Sale.')
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            if {'funnel_id', 'step_key'} & set(vals):
                raise UserError('CRM-002: Không đổi phễu/loại của stage.')
            if any(s.funnel_id.sudo().group_key != 'sale' for s in self):
                raise UserError('CRM-002: Stage của Data Funnel là cố định.')
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            if any(s.funnel_id.sudo().group_key != 'sale' for s in self):
                raise UserError('CRM-002: Stage của Data Funnel là cố định.')
            used = self.env['crm.lead'].sudo().with_context(active_test=False).search_count(
                [('sgt_crm002_sale_stage_id', 'in', self.ids)])
            if used:
                raise UserError('CRM-002: Còn %s Deal đang ở stage này. Hãy chuyển Deal đi trước khi xoá.' % used)
        return super().unlink()
