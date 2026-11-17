"""CRM-002 intake state on ONE crm.lead record, never a duplicated Deal.

A Deal can be in up to three places at once, always as the SAME record (so the
Chatter / log notes are inherited by every hand-off):
  * Data Funnel   : sgt_crm002_funnel_id + sgt_crm002_step   (3 fixed columns)
  * Match Making  : the native CRM stage_id
  * Sale funnels  : sgt_crm002_sale_funnel_id + sgt_crm002_sale_stage_id (Update_007)
Hand-offs are driven by sgt.crm002.handoff.rule records.
"""
import logging

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL

from . import timing

_logger = logging.getLogger(__name__)

STEP_KEYS = [('data', '1.Data'), ('verified', '2.Verified'), ('potential', '3.Potential')]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sgt_crm002_funnel_id = fields.Many2one(
        'sgt.crm002.funnel', string='CRM-002 Intake Funnel', copy=False,
        index=True, ondelete='set null')
    sgt_crm002_step = fields.Selection(
        STEP_KEYS, string='CRM-002 Intake Step', copy=False, index=True,
        group_expand='_sgt_crm002_expand_steps')
    # Update_007: membership of the Sale funnels (New / Renew). Separate from the
    # Data Funnel pair so one Deal can be at Data Funnel 3.Potential AND in New 1.Data.
    sgt_crm002_sale_funnel_id = fields.Many2one(
        'sgt.crm002.funnel', string='CRM-002 Sale Funnel', copy=False,
        index=True, ondelete='set null')
    sgt_crm002_sale_stage_id = fields.Many2one(
        'sgt.crm002.funnel.stage', string='CRM-002 Sale Stage', copy=False,
        index=True, ondelete='restrict',
        group_expand='_sgt_crm002_expand_sale_stages')

    # ---- Update_016 -------------------------------------------------------------------------
    # Last time the Deal changed stage in ANY of its funnels (CRM stage, Data step, Sale stage).
    # Stored; empty on old Deals -> falls back to the stock `date_last_stage_update`.
    sgt_crm002_stage_since = fields.Datetime(
        string='CRM-002 In Stage Since', copy=False, readonly=True)
    # Not stored (no database column): derived each time from the date above.
    sgt_crm002_age_days = fields.Integer(
        string='Days in Stage', compute='_compute_sgt_crm002_age', search='_search_sgt_crm002_age_days')
    sgt_crm002_age_bucket = fields.Selection(
        timing.AGE_BUCKETS, string='Stage Age', compute='_compute_sgt_crm002_age',
        search='_search_sgt_crm002_age_bucket')
    sgt_crm002_missing_info = fields.Char(
        string='Missing Data', compute='_compute_sgt_crm002_missing',
        help='Required data still empty (empty = complete).  Shown by the bell; framed in red on Deals in '
             '5.Match Making / 6.Approved Match Making.  It never blocks a stage change (Update_025).')
    # Update_025 (approved 2026-10-31 08:50): not stored.  True while the Deal is in 5.Match Making or
    # 6.Approved Match Making: the form then frames every missing item in red without clicking the bell.
    sgt_crm002_gate = fields.Boolean(
        string='In Match Making Columns', compute='_compute_sgt_crm002_gate')

    def _sgt_crm002_since(self):
        self.ensure_one()
        return self.sgt_crm002_stage_since or self.date_last_stage_update or self.create_date

    @api.depends('sgt_crm002_stage_since', 'date_last_stage_update', 'create_date', 'probability')
    def _compute_sgt_crm002_age(self):
        now = fields.Datetime.now()
        for lead in self:
            days = timing.age_days(lead._sgt_crm002_since(), now)
            lead.sgt_crm002_age_days = days
            lead.sgt_crm002_age_bucket = timing.age_bucket(days, closed=lead.probability >= 100)

    def _sgt_crm002_since_sql(self, alias, query):
        return SQL('COALESCE(%s, %s, %s)',
                   self._field_to_sql(alias, 'sgt_crm002_stage_since', query),
                   self._field_to_sql(alias, 'date_last_stage_update', query),
                   self._field_to_sql(alias, 'create_date', query))

    @api.model
    def _sgt_crm002_bucket_domain(self, bucket, now):
        """Domain of one bucket, written on stored columns (COALESCE(stage_since, date_last_stage_update))."""
        from datetime import timedelta
        t4 = now - timedelta(days=timing.AGE_FRESH_MAX + 1)
        t8 = now - timedelta(days=timing.AGE_WARN_MAX + 1)

        def since(op, limit):
            return ['|', ('sgt_crm002_stage_since', op, limit),
                    '&', ('sgt_crm002_stage_since', '=', False), ('date_last_stage_update', op, limit)]
        if bucket == 'fresh':
            part = since('>', t4)
        elif bucket == 'warn':
            part = ['&'] + since('<=', t4) + since('>', t8)
        else:
            part = since('<=', t8)
        return ['&', ('probability', '<', 100)] + part

    @api.model
    def _search_sgt_crm002_age_bucket(self, operator, value):
        """Domain used when a Kanban progress-bar segment is clicked."""
        if operator not in ('=', '!=', 'in', 'not in'):
            raise UserError('CRM-002: operator not supported on Stage Age.')
        # Odoo 19 rewrites ('=', 'x') as ('in', OrderedSet(['x'])): the value is any iterable, not only list/tuple
        # (Update_023: with the old list/tuple check a click on a bar segment matched nothing).
        raw = [value] if isinstance(value, str) or not hasattr(value, '__iter__') else list(value)
        values = []
        for v in raw:
            if v in ('fresh', 'warn', 'late') and v not in values:
                values.append(v)
        now = fields.Datetime.now()
        domain = []
        for i, bucket in enumerate(values):
            if i:
                domain.insert(0, '|')
            domain += self._sgt_crm002_bucket_domain(bucket, now)
        if not domain:
            domain = [('id', '=', 0)]
        return ['!'] + domain if operator in ('!=', 'not in') else domain

    @api.model
    def _search_sgt_crm002_age_days(self, operator, value):
        raise UserError('CRM-002: Days in Stage cannot be searched.')

    def _read_group_groupby(self, alias, groupby_spec, query):
        """Kanban progress bar by Stage Age: one SQL CASE, no stored bucket, no cron."""
        if groupby_spec != 'sgt_crm002_age_bucket':
            return super()._read_group_groupby(alias, groupby_spec, query)
        from datetime import timedelta
        now = fields.Datetime.now()
        t4 = now - timedelta(days=timing.AGE_FRESH_MAX + 1)
        t8 = now - timedelta(days=timing.AGE_WARN_MAX + 1)
        since = self._sgt_crm002_since_sql(alias, query)
        return SQL(
            "CASE WHEN %s >= 100 THEN NULL WHEN %s > %s THEN 'fresh' WHEN %s > %s THEN 'warn' ELSE 'late' END",
            self._field_to_sql(alias, 'probability', query), since, t4, since, t8)

    # depends only on stock fields: VN Odoo ID (x_getfly_id) comes from another addon and may not exist
    # on a clean database (then it is skipped by `available`).  Update_025: Evidence (CRM-005 field
    # x_yp_evidence_html, checked softly) counts as missing while the box holds no picture.
    @api.depends('partner_id', 'email_from', 'phone', 'source_id', 'street')
    def _compute_sgt_crm002_missing(self):
        available = set(self._fields)
        for lead in self:
            labels = timing.missing_labels(lambda f: lead[f], available=available)
            if timing.EVIDENCE_FIELD in available and timing.evidence_missing(lead[timing.EVIDENCE_FIELD]):
                labels.append(timing.EVIDENCE_LABEL)
            lead.sgt_crm002_missing_info = ', '.join(labels) if labels else False

    @api.depends('stage_id')
    def _compute_sgt_crm002_gate(self):
        for lead in self:
            lead.sgt_crm002_gate = timing.in_gate_stage(lead.stage_id.name)

    # Update_025 (user 2026-10-31 08:38): the stage-change guard of Update_016
    # (_sgt_crm002_check_stage_requirements, UserError "Không thể chuyển sang ...") is REMOVED.
    # A Deal with missing data may enter every column; the bell stays red and the form frames the
    # missing items in red while the Deal is in 5.Match Making / 6.Approved Match Making.

    @api.model
    def _sgt_crm002_expand_steps(self, values, domain):
        return ['data', 'verified', 'potential']

    @api.model
    def _sgt_crm002_expand_sale_stages(self, stages, domain):
        """Show every column of the opened Sale funnel, even when empty."""
        code = self.env.context.get('sgt_crm002_funnel_code')
        if not code:
            return stages
        return self.env['sgt.crm002.funnel.stage'].sudo().search(
            [('funnel_id.code', '=', code), ('funnel_id.group_key', '=', 'sale')], order='sequence, id')

    @api.model
    def _sgt_crm002_matching_funnel(self, lead):
        """Route only upon CREATE, never on historical read or tag edit.

        Only Data Funnel funnels route.  Ambiguous multi-tag matches resolve by
        funnel sequence. An explicitly selected funnel from the New form has
        priority over tag matching.
        """
        funnels = self.env['sgt.crm002.funnel'].sudo().search([
            ('active', '=', True), ('group_key', '=', 'data')], order='sequence, id')
        for funnel in funnels:
            if funnel.filter_mode == 'source':
                if funnel.source_id and lead.source_id.id == funnel.source_id.id:
                    return funnel
            else:
                tag = funnel.tag_id
                if not tag and funnel.initial_tag_name:
                    tag = self.env['crm.tag'].sudo().search([
                        ('name', '=', funnel.initial_tag_name)], limit=1)
                if tag and tag.id in lead.tag_ids.ids:
                    return funnel
        return self.env['sgt.crm002.funnel']

    @api.model
    def _sgt_crm002_is_entry_stage(self, stage):
        """True if the Deal was created in the FIRST stage of the CRM pipeline
        (i.e. raw intake data).  Not name based, so renaming stages is safe."""
        if not stage:
            return True
        first = self.env['crm.stage'].search([], order='sequence, id', limit=1)
        return not first or stage.sequence <= first.sequence

    @api.model_create_multi
    def create(self, vals_list):
        # Do not let a CRM-002 action insert fake step/potential or spoof a
        # department entitlement by choosing a foreign funnel id.
        service = self.env['sgt.crm002.service']
        requested = []
        for vals in vals_list:
            vals = dict(vals)
            explicit_id = vals.get('sgt_crm002_funnel_id') or self.env.context.get('default_sgt_crm002_funnel_id')
            explicit = self.env['sgt.crm002.funnel'].sudo().browse(int(explicit_id)).exists() if explicit_id else False
            if explicit:
                if explicit.is_main or not explicit.active or explicit.group_key != 'data':
                    raise UserError('CRM-002: Phễu tiếp nhận không hợp lệ.')
                service._check_funnel(explicit)
                vals['sgt_crm002_funnel_id'] = explicit.id
                vals['sgt_crm002_step'] = 'data'
            else:
                vals.pop('sgt_crm002_funnel_id', None)
                vals.pop('sgt_crm002_step', None)
            # Sale membership is only ever set by a hand-off rule.
            vals.pop('sgt_crm002_sale_funnel_id', None)
            vals.pop('sgt_crm002_sale_stage_id', None)
            requested.append(vals)
        leads = super().create(requested)
        for lead, vals in zip(leads, requested):
            funnel = self.env['sgt.crm002.funnel'].sudo().browse(vals['sgt_crm002_funnel_id']) if vals.get('sgt_crm002_funnel_id') else self._sgt_crm002_matching_funnel(lead)
            if not funnel:
                continue
            # Never auto-enroll a deal explicitly created into an advanced
            # CRM stage; it is not raw intake data.
            if not vals.get('sgt_crm002_funnel_id') and not self._sgt_crm002_is_entry_stage(lead.stage_id):
                continue
            if not lead.sgt_crm002_funnel_id:
                lead._sgt_crm002_internal_update({
                    'sgt_crm002_funnel_id': funnel.id, 'sgt_crm002_step': 'data'})
            # Keep the intake source/Tag on newly entered manual Deals.
            if vals.get('sgt_crm002_funnel_id'):
                if funnel.filter_mode == 'source' and funnel.source_id and not lead.source_id:
                    lead.write({'source_id': funnel.source_id.id})
                elif funnel.filter_mode == 'tag':
                    tag = funnel.tag_id
                    if not tag and funnel.initial_tag_name:
                        tag = self.env['crm.tag'].sudo().search([('name', '=', funnel.initial_tag_name)], limit=1)
                    if tag and tag.id not in lead.tag_ids.ids:
                        lead.write({'tag_ids': [(4, tag.id)]})
            self.env['sgt.crm002.service']._activate_progress(funnel, lead)
        return leads

    def _sgt_crm002_internal_update(self, vals):
        """Private server-only update, not accessible by external Odoo RPC.

        Calls standard CRM write chain but bypasses only THIS addon override;
        original CRM ACL, Record Rules and other addon hooks stay intact.
        """
        return super(CrmLead, self).write(vals)

    def write(self, vals):
        vals = dict(vals)
        membership = {'sgt_crm002_funnel_id', 'sgt_crm002_sale_funnel_id'}
        if membership & set(vals):
            raise AccessError('CRM-002: Không thể tự đổi phễu bằng thao tác chỉnh sửa Deal.')
        if 'sgt_crm002_sale_stage_id' in vals:
            return self._sgt_crm002_move_sale_stage(vals)
        if 'sgt_crm002_step' not in vals:
            return self._sgt_crm002_plain_write(vals)
        service = self.env['sgt.crm002.service']
        new_step = vals.get('sgt_crm002_step')
        if new_step not in ('data', 'verified', 'potential'):
            raise AccessError('CRM-002: Không thể xóa trực tiếp trạng thái tiếp nhận.')
        # Odoo native Kanban uses crm.lead.write() when moving a card between
        # grouped columns; this checks CRM access and CRM-002 funnel rights.
        # The handoff rule is enforced server-side, including blocked attempts
        # to move a completed Potential back to Data or Verified.
        for lead in self:
            lead.check_access('write')
            funnel = lead.sgt_crm002_funnel_id.sudo()
            if not funnel:
                raise UserError('CRM-002: Deal không nằm trong hàng đợi tiếp nhận.')
            service._check_funnel(funnel)
            expected_code = self.env.context.get('sgt_crm002_funnel_code')
            if expected_code and expected_code != funnel.code:
                raise AccessError('CRM-002: Deal không thuộc phễu hiện tại.')
            extra = {key: value for key, value in vals.items() if key != 'sgt_crm002_step'}
            if extra:
                super(CrmLead, lead).write(extra)
            service._transition_intake(lead, new_step)
        return True

    def _sgt_crm002_plain_write(self, vals):
        """Normal write; if the CRM stage changes, run the Match Making hand-off rules."""
        if 'stage_id' not in vals:
            return super().write(vals)
        previous = {lead.id: lead.stage_id.id for lead in self}
        result = super().write(vals)
        changed = self.filtered(lambda lead: lead.stage_id.id != previous.get(lead.id))
        if changed:   # Update_016: the "days in stage" clock restarts on every real stage change
            changed._sgt_crm002_internal_update({'sgt_crm002_stage_since': fields.Datetime.now()})
        self._sgt_crm002_after_stage_change(previous)
        return result

    def _sgt_crm002_after_stage_change(self, previous):
        """Deal entered a CRM stage: run the hand-off rules whose source is that stage.

        Only Deals visible in the Match Making pipeline are considered.  A failing
        rule is logged and never blocks the user's own drag/drop; the rule's
        "Áp dụng cho Deal đang có" button can retry it later.
        """
        mm = self.env['sgt.crm002.funnel'].sudo().search([('group_key', '=', 'mm'), ('active', '=', True)], limit=1)
        if not mm:
            return
        Rule = self.env['sgt.crm002.handoff.rule']
        for lead in self:
            if not lead.stage_id or lead.stage_id.id == previous.get(lead.id):
                continue
            if lead.sgt_crm002_funnel_id and lead.sgt_crm002_step != 'potential':
                continue  # still pending inside a Data Funnel
            Rule._run_for_safe(lead, mm, crm_stage=lead.stage_id)

    def _sgt_crm002_log_stage_move(self, funnel_name, old_label, new_label):
        """Update_015: Log note "moved between two columns of a funnel" (nobody is notified).

        The funnel columns are CRM-002's own fields, so Odoo's Chatter does not track them.
        Never blocks the move: a failure here is only logged.
        """
        self._sgt_crm002_internal_update({'sgt_crm002_stage_since': fields.Datetime.now()})
        for lead in self:
            try:
                body = Markup('<p>🔀 <b>Chuyển stage trong phễu %s</b>: %s → %s</p>') % (
                    funnel_name or '?', old_label or '—', new_label or '—')
                with self.env.cr.savepoint():
                    lead.sudo().message_post(
                        body=body, message_type='comment', subtype_xmlid='mail.mt_note',
                        author_id=self.env.user.partner_id.id)
            except Exception:
                _logger.warning('CRM-002: could not log the stage move of lead %s', lead.id, exc_info=True)

    def _sgt_crm002_move_sale_stage(self, vals):
        """Kanban drag between the columns of a Sale funnel (New / Renew)."""
        service = self.env['sgt.crm002.service']
        stage = self.env['sgt.crm002.funnel.stage'].sudo().browse(vals.get('sgt_crm002_sale_stage_id') or 0).exists()
        if not stage:
            raise AccessError('CRM-002: Không thể xóa trực tiếp stage của phễu Sale.')
        extra = {key: value for key, value in vals.items() if key != 'sgt_crm002_sale_stage_id'}
        for lead in self:
            lead.check_access('write')
            funnel = lead.sgt_crm002_sale_funnel_id.sudo()
            if not funnel or stage.funnel_id != funnel:
                raise UserError('CRM-002: Stage không thuộc phễu của Deal.')
            service._check_funnel(funnel)
            expected_code = self.env.context.get('sgt_crm002_funnel_code')
            if expected_code and expected_code != funnel.code:
                raise AccessError('CRM-002: Deal không thuộc phễu hiện tại.')
            if extra:
                super(CrmLead, lead).write(extra)
            if lead.sgt_crm002_sale_stage_id != stage:
                previous_stage = lead.sgt_crm002_sale_stage_id.sudo().name
                lead._sgt_crm002_internal_update({'sgt_crm002_sale_stage_id': stage.id})
                lead._sgt_crm002_log_stage_move(funnel.name, previous_stage, stage.sudo().name)
                self.env['sgt.crm002.handoff.rule']._run_for_safe(lead, funnel, stage=stage)
        return True

    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        """Update_012: server-side gate of the Match Making pipeline.

        The stock CRM pipeline action carries the context flag `sgt_crm002_mm_guard`
        (views/landing.xml).  Every read that comes from that action (Kanban, list,
        pivot, graph, calendar, counts) goes through `_search`; for a user without
        Match Making permission the result is empty, so no Match Making data leaves the
        server whatever menu, link or old tab opened the page.  Without the flag
        nothing changes.
        """
        if self.env.context.get('sgt_crm002_mm_guard') and not self.env['sgt.crm002.service']._mm_allowed():
            domain = [('id', '=', 0)]
        return super()._search(domain, offset=offset, limit=limit, order=order,
                               active_test=active_test, bypass_access=bypass_access)

    @api.model
    def web_search_read(self, *args, **kwargs):
        self._sgt_crm002_check_context()
        return super().web_search_read(*args, **kwargs)

    @api.model
    def web_read_group(self, *args, **kwargs):
        self._sgt_crm002_check_context()
        return super().web_read_group(*args, **kwargs)

    @api.model
    def _sgt_crm002_check_context(self):
        code = self.env.context.get('sgt_crm002_funnel_code')
        if code:
            service = self.env['sgt.crm002.service']
            funnel = service._find_funnel(code)
            service._check_funnel(funnel)
