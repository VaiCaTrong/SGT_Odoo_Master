"""Configuration owned by CRM-002. Never replaces crm.stage or hr.department.

Update_007: funnels belong to one of three FIXED groups (``group_key``):
    data  Data Funnel             - new funnels may be created here by Administrator
    sale  Sale (New, Renew)       - fixed funnels, stages edited in Settings
    mm    Match Making Campaign   - the default CRM pipeline, fixed
Hand-off between funnels is configured by ``sgt.crm002.handoff.rule``.
"""
import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

GROUP_KEYS = [
    ('data', 'Data Funnel'),
    ('sale', 'Sale'),
    ('mm', 'Match Making Campaign'),
]
STEP_KEYS = [('data', '1.Data'), ('verified', '2.Verified'), ('potential', '3.Potential')]

# Exact stage names used ONLY to pre-fill the default hand-off rules once
# (install / upgrade).  Rules afterwards store stage records, not names.
DEFAULT_ENTRY_STAGE_NAMES = ('1.Opportunity', '4.Opportunity')  # 2nd = legacy name
DEFAULT_APPROVED_STAGE_NAMES = ('6.Approved Match Making',)
DEFAULT_SALE_FIRST_STAGE = '1.Data'


class Crm002Funnel(models.Model):
    _name = 'sgt.crm002.funnel'
    _description = 'CRM-002 Campaign Funnel'
    _order = 'sequence, id'

    @api.model
    def _default_code(self):
        return 'f' + uuid.uuid4().hex[:10]

    name = fields.Char(required=True, translate=True)
    # Update_007: Selection -> Char so new funnels can be created.  Generated
    # automatically; fixed funnels keep hunter/pool/unverified/face/mm/sale_*.
    code = fields.Char(required=True, index=True, copy=False, default=_default_code)
    group_key = fields.Selection(GROUP_KEYS, required=True, default='data', index=True, copy=False)
    sequence = fields.Integer(default=10)
    filter_mode = fields.Selection([('tag', 'Tags'), ('source', 'Source')], default='tag', required=True)
    tag_id = fields.Many2one('crm.tag', string='CRM Tag', ondelete='set null')
    source_id = fields.Many2one('utm.source', string='UTM Source', ondelete='set null')
    initial_tag_name = fields.Char(string='Initial tag name', help='Fallback for initial deployment; exact name only.')
    allowed_department_ids = fields.Many2many(
        'hr.department', 'sgt_crm002_funnel_department_rel', 'funnel_id', 'department_id',
        string='Departments allowed to access')
    is_main = fields.Boolean(default=False, readonly=True)
    active = fields.Boolean(default=True)
    stage_ids = fields.One2many('sgt.crm002.funnel.stage', 'funnel_id', string='Stages')
    outgoing_rule_ids = fields.One2many('sgt.crm002.handoff.rule', 'source_funnel_id', string='Hand-off rules (from this funnel)')

    rule_count = fields.Integer(compute='_compute_rule_count', string='Hand-off rules')

    _sql_constraints = [
        ('sgt_crm002_code_unique', 'unique(code)', 'CRM-002 funnel code must be unique.'),
    ]

    @api.depends('outgoing_rule_ids')
    def _compute_rule_count(self):
        counts = {}
        if self.ids:
            data = self.env['sgt.crm002.handoff.rule'].with_context(active_test=False)._read_group(
                [('source_funnel_id', 'in', self.ids)], ['source_funnel_id'], ['__count'])
            counts = {funnel.id: count for funnel, count in data}
        for rec in self:
            rec.rule_count = counts.get(rec.id, 0)

    def action_open_rules(self):
        """Smart button: the hand-off rules whose SOURCE is this funnel."""
        self.ensure_one()
        self.env['sgt.crm002.service']._check_admin()
        return {
            'type': 'ir.actions.act_window', 'name': 'Luật bàn giao · %s' % self.name,
            'res_model': 'sgt.crm002.handoff.rule', 'view_mode': 'list,form',
            'domain': [('source_funnel_id', '=', self.id)],
            'context': {'default_source_funnel_id': self.id, 'active_test': False},
        }

    @api.constrains('is_main', 'code', 'group_key')
    def _validate_main(self):
        for rec in self:
            is_mm = rec.group_key == 'mm'
            if bool(rec.is_main) != is_mm or is_mm != (rec.code == 'mm'):
                raise ValidationError('Match Making is the only main CRM pipeline funnel.')

    # ------------------------------------------------------------------ guards
    # Only the Superuser (install / upgrade / data files) may create or remove
    # fixed funnels.  A normal Administrator can create funnels in Data Funnel only.
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                if vals.get('group_key', 'data') != 'data' or vals.get('is_main'):
                    raise UserError('CRM-002: Chỉ được tạo phễu mới trong Data Funnel.')
        records = super().create(vals_list)
        for rec in records:
            rec._sgt_ensure_default_stages()
            if rec.group_key == 'data':
                try:
                    with self.env.cr.savepoint():
                        rec._sgt_ensure_default_rules()
                except Exception:  # never block funnel creation on a seed rule
                    _logger.warning('CRM-002: could not create default hand-off rule for %s', rec.code, exc_info=True)
        return records

    def write(self, vals):
        if not self.env.su:
            if {'group_key', 'code', 'is_main'} & set(vals):
                raise UserError('CRM-002: Không được đổi nhóm/mã của phễu.')
            fixed = self.filtered(lambda f: f.group_key != 'data')
            if fixed:
                if 'active' in vals and not vals['active']:
                    raise UserError('CRM-002: Phễu cố định (Sale, Match Making) không thể lưu trữ.')
                if 'name' in vals:
                    raise UserError('CRM-002: Phễu cố định (Sale, Match Making) không đổi tên.')
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError('CRM-002: Không xoá phễu. Hãy dùng Lưu trữ (Archive).')
        return super().unlink()

    # ---------------------------------------------------------- default content
    def _sgt_default_stage_vals(self):
        """[(sequence, name, step_key)] a funnel must have."""
        self.ensure_one()
        if self.group_key == 'data':
            return [(10, '1.Data', 'data'), (20, '2.Verified', 'verified'), (30, '3.Potential', 'potential')]
        if self.group_key == 'sale':
            return [(10, DEFAULT_SALE_FIRST_STAGE, False)]
        return []

    def _sgt_ensure_default_stages(self):
        """Idempotent: create the missing default stages (Data Funnel: 3 fixed steps)."""
        Stage = self.env['sgt.crm002.funnel.stage'].sudo()
        for funnel in self:
            existing = Stage.with_context(active_test=False).search([('funnel_id', '=', funnel.id)])
            if funnel.group_key == 'data':
                have = set(existing.mapped('step_key'))
                for seq, name, key in funnel._sgt_default_stage_vals():
                    if key not in have:
                        Stage.create({'funnel_id': funnel.id, 'name': name, 'sequence': seq, 'step_key': key})
            elif funnel.group_key == 'sale' and not existing:
                for seq, name, key in funnel._sgt_default_stage_vals():
                    Stage.create({'funnel_id': funnel.id, 'name': name, 'sequence': seq})

    @api.model
    def _sgt_find_crm_stage(self, names):
        """First CRM stage whose name equals one of ``names`` exactly (checked in order)."""
        stages = self.env['crm.stage'].sudo().search([], order='sequence, id')
        for wanted in names:
            matches = stages.filtered(lambda s, w=wanted: (s.name or '').strip() == w)
            if matches:
                return matches[0]
        return self.env['crm.stage']

    def _sgt_ensure_default_rules(self):
        """Data Funnel default: 3.Potential -> Match Making '1.Opportunity' (the old
        automatic hand-off).  Idempotent; skipped (with a warning) if the CRM stage
        cannot be found by its exact name - the Administrator then creates the rule."""
        Rule = self.env['sgt.crm002.handoff.rule'].sudo()
        mm = self.sudo().search([('group_key', '=', 'mm')], limit=1)
        if not mm:
            return  # fresh install: the post-init hook seeds the rules once Match Making exists
        target = self._sgt_find_crm_stage(DEFAULT_ENTRY_STAGE_NAMES)
        for funnel in self.filtered(lambda f: f.group_key == 'data'):
            potential = self.env['sgt.crm002.funnel.stage'].sudo().search(
                [('funnel_id', '=', funnel.id), ('step_key', '=', 'potential')], limit=1)
            if not (mm and target and potential):
                _logger.warning('CRM-002: default hand-off rule for funnel %s not created (stage %s not found).',
                                funnel.code, DEFAULT_ENTRY_STAGE_NAMES[0])
                continue
            if Rule.with_context(active_test=False).search_count([
                    ('source_funnel_id', '=', funnel.id), ('source_stage_id', '=', potential.id),
                    ('target_funnel_id', '=', mm.id)]):
                continue
            Rule.create({
                'sequence': 10, 'source_funnel_id': funnel.id, 'source_stage_id': potential.id,
                'target_funnel_id': mm.id, 'target_crm_stage_id': target.id,
            })
