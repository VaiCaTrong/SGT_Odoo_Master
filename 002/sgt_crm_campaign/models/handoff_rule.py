"""Configurable hand-off between CRM-002 funnels (Update_007).

A rule says: "when a Deal enters COLUMN X of funnel A, hand it to COLUMN Y of
funnel B".  The hand-off never copies the Deal: it is the SAME crm.lead, so the
Chatter (log notes, e-mails, tracking), attachments, activities, tags and
salesperson are all inherited.

Supported targets: Match Making (a native CRM stage) or a Sale funnel
(New/Renew).  A Data Funnel can not be a target because Deals enter it only at
creation (by Tag/Source).  A rule fires once per Deal and target: it never
moves a Deal back (Match Making: only forward by stage sequence; Sale: only if
the Deal is not already in the target funnel).
"""
import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

APPLY_LIMIT = 500  # Deals handed over per click of "Áp dụng cho Deal đang có"


class Crm002HandoffRule(models.Model):
    _name = 'sgt.crm002.handoff.rule'
    _description = 'CRM-002 Hand-off Rule'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    source_funnel_id = fields.Many2one('sgt.crm002.funnel', required=True, ondelete='cascade', index=True)
    source_group = fields.Selection(related='source_funnel_id.group_key')
    source_stage_id = fields.Many2one('sgt.crm002.funnel.stage', ondelete='cascade',
                                      string='Source column (Data Funnel / Sale)')
    source_crm_stage_id = fields.Many2one('crm.stage', ondelete='cascade',
                                          string='Source column (Match Making = CRM stage)')

    target_funnel_id = fields.Many2one('sgt.crm002.funnel', required=True, ondelete='cascade', index=True)
    target_group = fields.Selection(related='target_funnel_id.group_key')
    target_stage_id = fields.Many2one('sgt.crm002.funnel.stage', ondelete='cascade',
                                      string='Target column (Sale)')
    target_crm_stage_id = fields.Many2one('crm.stage', ondelete='cascade',
                                          string='Target column (Match Making = CRM stage)')

    summary = fields.Char(compute='_compute_summary')
    pending_count = fields.Integer(compute='_compute_pending_count', string='Deals waiting in the source column')

    # ------------------------------------------------------------ computed
    @api.depends('source_funnel_id', 'source_stage_id', 'source_crm_stage_id',
                 'target_funnel_id', 'target_stage_id', 'target_crm_stage_id')
    def _compute_summary(self):
        for rule in self:
            src_col = rule.source_crm_stage_id.name if rule.source_group == 'mm' else rule.source_stage_id.name
            dst_col = rule.target_crm_stage_id.name if rule.target_group == 'mm' else rule.target_stage_id.name
            rule.summary = '%s › %s  →  %s › %s' % (
                rule.source_funnel_id.name or '?', src_col or '?',
                rule.target_funnel_id.name or '?', dst_col or '?')

    @api.depends('source_funnel_id', 'source_stage_id', 'source_crm_stage_id',
                 'target_funnel_id', 'target_stage_id', 'target_crm_stage_id')
    def _compute_pending_count(self):
        for rule in self:
            count = 0
            if isinstance(rule.id, int) and rule._is_configured():
                try:
                    count = self.env['crm.lead'].search_count(rule._pending_domain())
                except Exception:  # an unfinished rule must never break the form
                    count = 0
            rule.pending_count = count

    @api.depends('source_funnel_id', 'source_stage_id', 'source_crm_stage_id',
                 'target_funnel_id', 'target_stage_id', 'target_crm_stage_id')
    def _compute_display_name(self):
        for rule in self:
            rule.display_name = rule.summary or 'Hand-off rule'

    # ------------------------------------------------------------ onchange / constraints
    @api.onchange('source_funnel_id')
    def _onchange_source_funnel(self):
        self.source_stage_id = False
        self.source_crm_stage_id = False

    @api.onchange('target_funnel_id')
    def _onchange_target_funnel(self):
        self.target_stage_id = False
        self.target_crm_stage_id = False

    @api.constrains('source_funnel_id', 'source_stage_id', 'source_crm_stage_id',
                    'target_funnel_id', 'target_stage_id', 'target_crm_stage_id')
    def _check_rule(self):
        for rule in self:
            source, target = rule.source_funnel_id, rule.target_funnel_id
            if source == target:
                raise ValidationError('CRM-002: Phễu nguồn và phễu đích phải khác nhau.')
            if target.group_key == 'data':
                raise ValidationError('CRM-002: Phễu đích không thể thuộc Data Funnel '
                                      '(Deal chỉ vào Data Funnel lúc tạo theo Tag/Source).')
            rule._check_side(source, rule.source_stage_id, rule.source_crm_stage_id, 'nguồn')
            rule._check_side(target, rule.target_stage_id, rule.target_crm_stage_id, 'đích')

    def _check_side(self, funnel, stage, crm_stage, label):
        if funnel.group_key == 'mm':
            if not crm_stage:
                raise ValidationError('CRM-002: Hãy chọn Stage CRM (cột %s) của Match Making.' % label)
            if stage:
                raise ValidationError('CRM-002: Match Making dùng Stage CRM, bỏ cột phễu ở phía %s.' % label)
        else:
            if not stage or stage.funnel_id != funnel:
                raise ValidationError('CRM-002: Hãy chọn cột %s thuộc phễu "%s".' % (label, funnel.name))
            if crm_stage:
                raise ValidationError('CRM-002: Phễu "%s" không dùng Stage CRM, bỏ Stage CRM phía %s.' % (funnel.name, label))

    def _is_configured(self):
        self.ensure_one()
        try:
            self._check_rule()
        except ValidationError:
            return False
        return bool(self.source_funnel_id and self.target_funnel_id)

    # ------------------------------------------------------------ domains
    def _source_domain(self):
        """crm.lead domain: Deals sitting in the source column right now."""
        self.ensure_one()
        funnel = self.source_funnel_id
        if funnel.group_key == 'data':
            step = self.source_stage_id.step_key
            if not step:
                return [('id', '=', 0)]
            return [('sgt_crm002_funnel_id', '=', funnel.id), ('sgt_crm002_step', '=', step)]
        if funnel.group_key == 'sale':
            return [('sgt_crm002_sale_funnel_id', '=', funnel.id),
                    ('sgt_crm002_sale_stage_id', '=', self.source_stage_id.id)]
        # Match Making: the official CRM Pipeline (same visibility as the pipeline action)
        return [('type', '=', 'opportunity'), ('stage_id', '=', self.source_crm_stage_id.id),
                '|', ('sgt_crm002_funnel_id', '=', False), ('sgt_crm002_step', '=', 'potential')]

    def _not_at_target_domain(self):
        self.ensure_one()
        target = self.target_funnel_id
        if target.group_key == 'mm':
            return ['|', ('stage_id', '=', False), ('stage_id.sequence', '<', self.target_crm_stage_id.sequence)]
        return ['|', ('sgt_crm002_sale_funnel_id', '=', False), ('sgt_crm002_sale_funnel_id', '!=', target.id)]

    def _pending_domain(self):
        self.ensure_one()
        return self._source_domain() + self._not_at_target_domain()

    # ------------------------------------------------------------ hand-off
    def _lead_at_target(self, lead):
        self.ensure_one()
        target = self.target_funnel_id
        if target.group_key == 'mm':
            return bool(lead.stage_id) and lead.stage_id.sequence >= self.target_crm_stage_id.sequence
        return lead.sgt_crm002_sale_funnel_id == target

    def _column_label(self, funnel, stage, crm_stage):
        """'Funnel › Column' text of one side of the rule."""
        column = crm_stage.name if funnel.group_key == 'mm' else stage.name
        return '%s › %s' % (funnel.name or '?', column or '?')

    def _log_handoff(self, lead, manual=False, moved=True):
        """Update_014: write the hand-off into the Deal's Chatter (Log note, nobody is notified).

        Never blocks the hand-off: a failure here is only logged.
        """
        self.ensure_one()
        try:
            how = ('áp dụng thủ công (nút "Áp dụng cho Deal đang có")' if manual
                   else 'tự động khi Deal vào cột nguồn')
            body = Markup(
                '<p><b>🔁 Bàn giao Deal (CRM-002)</b></p>'
                '<ul><li>Từ: %s</li><li>Sang: %s</li><li>Luật: %s</li><li>Thực hiện bởi: %s · %s</li>'
                '<li>Kết quả: %s</li></ul>'
            ) % (
                self._column_label(self.source_funnel_id, self.source_stage_id, self.source_crm_stage_id),
                self._column_label(self.target_funnel_id, self.target_stage_id, self.target_crm_stage_id),
                self.summary or '?',
                self.env.user.name or '?',
                how,
                ('đã chuyển Deal sang cột đích' if moved
                 else 'Deal đã đứng sẵn ở cột đích nên không đổi stage; Deal nay hiện trong phễu đích'),
            )
            with self.env.cr.savepoint():
                lead.sudo().message_post(
                    body=body, message_type='comment', subtype_xmlid='mail.mt_note',
                    author_id=self.env.user.partner_id.id)
        except Exception:
            _logger.warning('CRM-002: could not log the hand-off of lead %s', lead.id, exc_info=True)

    def _apply_to(self, lead, manual=False):
        """Hand ONE Deal over (same crm.lead, nothing copied).  Returns True if it moved."""
        self.ensure_one()
        if self._lead_at_target(lead):
            if self.source_group == 'data':
                # Update_015: a Data Funnel Deal already sits at the entry stage of Match Making
                # (1.Opportunity); entering Potential IS the hand-off, so it is still written down.
                self._log_handoff(lead, manual=manual, moved=False)
            return False
        target = self.target_funnel_id
        if target.group_key == 'mm':
            crm_stage = self.target_crm_stage_id
            if crm_stage.team_ids and lead.team_id and lead.team_id not in crm_stage.team_ids:
                raise UserError('CRM-002: Stage "%s" không áp dụng cho Sales Team "%s" của Deal #%s. '
                                'Kiểm tra Stage CRM và Team.' % (crm_stage.name, lead.team_id.name, lead.id))
            values = {'stage_id': crm_stage.id}
            if lead.type != 'opportunity':
                values['type'] = 'opportunity'
        else:
            values = {'sgt_crm002_sale_funnel_id': target.id,
                      'sgt_crm002_sale_stage_id': self.target_stage_id.id}
        lead._sgt_crm002_internal_update(values)
        self._log_handoff(lead, manual=manual)
        return True

    @api.model
    def _run_for(self, lead, funnel, stage=None, crm_stage=None):
        """Run the active rules whose source is the column the Deal just entered.

        Rules run in ``sequence`` order.  For Sale targets only the first rule
        has effect (a Deal sits in one Sale funnel at a time).  No chaining: a
        Deal moved by a rule does not trigger further rules.
        """
        domain = [('active', '=', True), ('source_funnel_id', '=', funnel.id)]
        if crm_stage:
            domain.append(('source_crm_stage_id', '=', crm_stage.id))
        elif stage:
            domain.append(('source_stage_id', '=', stage.id))
        else:
            return 0
        moved = 0
        sale_done = False
        for rule in self.sudo().search(domain, order='sequence, id'):
            if rule.target_group == 'sale':
                if sale_done:
                    continue
                sale_done = True
            if rule._apply_to(lead):
                moved += 1
        return moved

    @api.model
    def _run_for_safe(self, lead, funnel, stage=None, crm_stage=None):
        """Same as _run_for but an error is logged and never blocks the user's own action."""
        try:
            with self.env.cr.savepoint():
                return self._run_for(lead, funnel, stage=stage, crm_stage=crm_stage)
        except Exception:
            _logger.warning('CRM-002: hand-off rule failed for lead %s (funnel %s)', lead.id, funnel.sudo().code, exc_info=True)
            return 0

    # ------------------------------------------------------------ button
    def action_apply_existing(self):
        """Hand over the Deals that are ALREADY in the source column."""
        self.ensure_one()
        self.env['sgt.crm002.service']._check_admin()
        if not self.active:
            raise UserError('CRM-002: Luật đang tắt. Hãy bật luật trước khi áp dụng.')
        if not self._is_configured():
            raise UserError('CRM-002: Luật chưa đầy đủ.')
        domain = self._pending_domain()
        total = self.env['crm.lead'].search_count(domain)
        leads = self.env['crm.lead'].search(domain, order='id', limit=APPLY_LIMIT)
        done, failed = 0, []
        for lead in leads:
            try:
                with self.env.cr.savepoint():
                    if self._apply_to(lead, manual=True):
                        done += 1
            except Exception as error:  # keep going; report at the end
                failed.append('#%s: %s' % (lead.id, getattr(error, 'args', [''])[0] if error.args else error))
        remaining = max(total - done - len(failed), 0)
        message = 'Đã bàn giao %s Deal.' % done
        if failed:
            message += ' Lỗi %s Deal: %s' % (len(failed), '; '.join(failed[:5]) + (' …' if len(failed) > 5 else ''))
        if remaining and total > APPLY_LIMIT:
            message += ' Còn khoảng %s Deal, hãy bấm lại.' % remaining
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': 'CRM-002 · Áp dụng luật bàn giao', 'message': message,
                'type': 'warning' if failed else 'success', 'sticky': bool(failed) or remaining > 0,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
