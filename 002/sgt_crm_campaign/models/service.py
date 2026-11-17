"""CRM-002 server-side enforcement. All public RPC entry points validate role.
Core crm.lead is NEVER sudo-read or sudo-written here: original Odoo ACLs stand.
Department and progress internal storage are sudo-accessed behind this service.
"""
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from psycopg2 import IntegrityError

from .timing import active_windows, full_days, visit_seconds, stage_color

# Fixed order of the sidebar groups (Update_007).
VIEW_MODES = 'kanban,list,calendar,pivot,graph,activity,form'   # Update_013 (same switcher as the stock Pipeline)
GROUP_ORDER = [('data', 'Data Funnel'), ('sale', 'Sale'), ('mm', 'Match Making Campaign')]   # fallback landing order
# Update_015: order of the sidebar: Sale sits UNDER Match Making
SIDEBAR_ORDER = [('data', 'Data Funnel'), ('mm', 'Match Making Campaign'), ('sale', 'Sale')]


class Crm002Service(models.AbstractModel):
    _name = 'sgt.crm002.service'
    _description = 'CRM-002 Secured Workspace Service'

    def _is_admin(self):
        return self.env.user.has_group('base.group_system')

    def _sees_all(self):
        """Update_027: sees EVERY funnel, whatever the Departments say.

        Role Administrator, or Sales "User: All Documents" (the Sales "Administrator" level includes it).
        The Role Administrator does NOT include the Sales groups; the check below is therefore on both.
        Settings / Permissions / hand-off rules stay with the Role Administrator only (`_is_admin`).
        """
        return self._is_admin() or self.env.user.has_group('sales_team.group_sale_salesman_all_leads')

    def _has_sales(self):
        """Update_027: Sales "User: Own Documents Only" or higher ("No" has no CRM access at all)."""
        return self.env.user.has_group('sales_team.group_sale_salesman')

    def _check_admin(self):
        if not self._is_admin():
            raise AccessError('CRM-002: Chỉ Administrator được sử dụng chức năng này.')

    def _find_funnel(self, code):
        if not code or not isinstance(code, str):
            raise UserError('CRM-002: Mã phễu không hợp lệ.')
        funnel = self.env['sgt.crm002.funnel'].sudo().search([('code', '=', code), ('active', '=', True)], limit=1)
        if not funnel:
            raise UserError('CRM-002: Không tìm thấy phễu.')
        return funnel

    def _user_department_ids(self):
        # Never expose Employee directory to normal users. Company-aware HR links
        # are respected by the model; only department IDs are used for decisions.
        employees = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.uid), ('active', '=', True),
            ('department_id', '!=', False),
            ('company_id', 'in', [False, self.env.company.id]),
        ])
        # Multiple historical Employee records should not silently stack
        # entitlements across different companies.
        return set(employees.mapped('department_id').ids)

    def _allowed(self, funnel):
        # sudo: a normal user may not read the funnel configuration model itself.
        funnel = funnel.sudo()
        if self._sees_all():
            return True
        # Update_027: Sales "No" sees no funnel; the Sale funnels (New / Renew) have no Department rule:
        # only Role Administrator, All Documents and Sales Administrator open them.
        if funnel.group_key == 'sale' or not self._has_sales():
            return False
        return bool(self._user_department_ids() & set(funnel.allowed_department_ids.ids))

    def _check_funnel(self, funnel):
        if not self._allowed(funnel):
            raise AccessError('CRM-002: Bạn không được cấp quyền truy cập phễu này.')

    def _visible_funnels(self):
        all_funnels = self.env['sgt.crm002.funnel'].sudo().search([('active', '=', True)])
        if self._sees_all():
            return all_funnels
        if not self._has_sales():                       # Update_027: Sales "No" sees nothing
            return all_funnels.filtered(lambda f: False)
        dept_ids = self._user_department_ids()
        return all_funnels.filtered(lambda f: f.group_key != 'sale'
                                    and bool(dept_ids & set(f.allowed_department_ids.ids)))

    def _tag_or_source_domain(self, funnel):
        if funnel.is_main:
            return [('type', '=', 'opportunity')], False
        if funnel.filter_mode == 'source':
            if not funnel.source_id:
                return [('id', '=', 0)], 'Chưa chọn Source cho phễu này.'
            return [('source_id', '=', funnel.source_id.id)], False
        tag = funnel.tag_id
        if not tag and funnel.initial_tag_name:
            tag = self.env['crm.tag'].search([('name', '=', funnel.initial_tag_name)], limit=1)
        if not tag:
            return [('id', '=', 0)], 'Không tìm thấy Tag: %s. Administrator cần cấu hình.' % (funnel.initial_tag_name or '—')
        return [('tag_ids', 'in', [tag.id])], False

    def _admin_directory(self):
        self._check_admin()
        departments = self.env['hr.department'].sudo().search([('active', '=', True)], order='name, id')
        employees = self.env['hr.employee'].sudo().search([
            ('active', '=', True), ('department_id', 'in', departments.ids),
            ('user_id', '!=', False),
        ], order='name, id') if departments else self.env['hr.employee'].browse()
        people = defaultdict(list)
        seen = set()
        for emp in employees:
            if not emp.user_id.active:
                continue
            key = (emp.department_id.id, emp.user_id.id)
            if key in seen:
                continue
            seen.add(key)
            people[emp.department_id.id].append({'id': emp.user_id.id, 'name': emp.name})
        return [{'id': dep.id, 'name': dep.name, 'members': people.get(dep.id, [])}
                for dep in departments]

    def _funnel_count_domain(self, funnel):
        """Same Deals the funnel's board shows (see open_intake / _open_sale / the Match Making pipeline)."""
        if funnel.is_main or funnel.group_key == 'mm':
            return [('type', '=', 'opportunity')]
        if funnel.group_key == 'sale':
            return [('sgt_crm002_sale_funnel_id', '=', funnel.id)]
        return [('sgt_crm002_funnel_id', '=', funnel.id),
                ('sgt_crm002_step', 'in', ['data', 'verified', 'potential'])]

    def _funnel_counts(self, funnels):
        """{funnel code: number of Deals} counted with the CURRENT user's own access (no sudo on crm.lead)."""
        lead = self.env['crm.lead']
        counts = {}
        for f in funnels:
            try:
                counts[f.code] = lead.search_count(self._funnel_count_domain(f))
            except AccessError:
                counts[f.code] = 0
        return counts

    def _list_funnel_data(self, funnels, counts=None):
        counts = counts or {}
        return [{'code': f.code, 'name': f.name, 'is_main': f.is_main, 'group': f.group_key,
                 'count': counts.get(f.code, 0)}
                for f in funnels]

    @api.model
    def bootstrap(self):
        """No HR personnel data for normal users; permissions enforced server-side.

        ``groups`` is the sidebar tree in the FIXED order Data Funnel / Match Making
        Campaign / Sale (Update_015); a normal user only gets groups with at least one
        funnel they are allowed to open.  ``funnels`` stays as a flat list for
        the legacy workspace.  Update_024: every funnel and every group carries ``count``
        (Deals in it) shown at the end of its sidebar row; a group counts its funnels
        (Match Making funnels all read the same pipeline: counted once).
        """
        admin = self._is_admin()
        funnels = self._visible_funnels().sorted(lambda f: (f.sequence, f.id))
        counts = self._funnel_counts(funnels)
        groups = []
        for key, label in SIDEBAR_ORDER:
            members = funnels.filtered(lambda f, key=key: f.group_key == key)
            if members or admin:
                values = [counts.get(f.code, 0) for f in members]
                total = (max(values) if values else 0) if key == 'mm' else sum(values)
                groups.append({'key': key, 'name': label, 'count': total,
                               'funnels': self._list_funnel_data(members, counts)})
        return {
            'is_admin': admin,
            'groups': groups,
            'funnels': self._list_funnel_data(funnels, counts),
            'departments': self._admin_directory() if admin else [],
        }

    def _mm_allowed(self):
        """True when the current user may see the Match Making pipeline data."""
        if self._sees_all():
            return True
        return any(f.group_key == 'mm' or f.is_main for f in self._visible_funnels())

    @api.model
    def landing_action(self):
        """Where the CRM app / "My Pipeline" menu lands (Update_011).

        Administrator, or a user whose Department is allowed on Match Making:
        the usual Match Making pipeline.  Otherwise the first funnel the user is
        allowed to open (Data Funnel first, then Sale).  A user with no funnel at
        all gets an empty screen with a short explanation.
        """
        funnels = self._visible_funnels()
        if self._sees_all() or funnels.filtered(lambda f: f.group_key == 'mm' or f.is_main):
            # Update_012: crm.team.action_your_pipeline() itself now calls this method,
            # so the stock behaviour is reached through a separate helper.
            action = self.env['crm.team']._sgt_crm002_native_pipeline()
            if self._is_admin() and isinstance(action.get('context'), dict):
                # Update_015: Administrator does not get "My Pipeline" applied automatically.
                action['context'] = dict(action['context'], search_default_assigned_to_me=0)
            return action
        order = {key: idx for idx, (key, _label) in enumerate(GROUP_ORDER)}
        for funnel in funnels.sorted(lambda f: (order.get(f.group_key, 99), f.sequence, f.id)):
            if funnel.group_key not in ('data', 'sale'):
                continue
            try:
                return self.open_intake(funnel.code)
            except (AccessError, UserError):
                continue
        return self._no_access_action()

    def _no_access_action(self):
        # Update_028: res.company, not crm.lead.  A user whose Sales field is "No" has no access
        # right on crm.lead; Odoo checks it before applying the domain, so an empty crm.lead page
        # ("id = 0") still raised an Access Error.  res.company is readable by every internal user.
        view = self.env.ref('sgt_crm_campaign.view_crm002_noaccess_company_kanban')
        return {
            'type': 'ir.actions.act_window', 'name': 'CRM',
            'res_model': 'res.company', 'view_mode': 'kanban',
            'views': [(view.id, 'kanban')],
            'target': 'current', 'domain': [('id', '=', 0)],
            'context': {'create': False},
            'help': '<p class="o_view_nocontent_smiling_face">Bạn chưa được phân quyền phễu nào</p>'
                    '<p>Liên hệ Administrator để được cấp quyền xem phễu.</p>',
        }

    def _staff_domain(self, department_id=None, user_id=None):
        if not department_id and not user_id:
            return []
        self._check_admin()
        if department_id and user_id:
            raise ValidationError('Chỉ lọc một Department hoặc một nhân viên.')
        if department_id:
            department = self.env['hr.department'].sudo().browse(int(department_id)).exists()
            if not department:
                raise UserError('Department không tồn tại.')
            emps = self.env['hr.employee'].sudo().search([
                ('department_id', '=', department.id), ('active', '=', True),
                ('user_id', '!=', False),
            ])
            user_ids = list(set(emps.mapped('user_id').ids))
            return [('user_id', 'in', user_ids)] if user_ids else [('id', '=', 0)]
        users = self.env['res.users'].sudo().browse(int(user_id)).exists()
        if not users:
            raise UserError('User không tồn tại.')
        # Not an arbitrary-User lookup endpoint; only Employees in directory.
        employees = self.env['hr.employee'].sudo().search_count([
            ('user_id', '=', users.id), ('active', '=', True), ('department_id', '!=', False),
        ])
        if not employees:
            raise AccessError('User không nằm trong danh sách Employees khả dụng.')
        return [('user_id', '=', users.id)]

    def _visit_tracking(self, lead_ids):
        """Read only standard CRM chatter. No lead stage write interception."""
        changes = defaultdict(list)
        if not lead_ids:
            return changes
        self.env['mail.tracking.value'].flush_model()
        self.env['mail.message'].flush_model()
        self.env.cr.execute('''
            SELECT m.res_id, v.id, v.create_date, f.name,
                   v.old_value_integer, v.new_value_integer
              FROM mail_tracking_value v
              JOIN mail_message m ON m.id = v.mail_message_id
              JOIN ir_model_fields f ON f.id = v.field_id
             WHERE m.model = %s AND m.res_id IN %s AND f.model = %s
               AND f.name IN ('stage_id','active')
             ORDER BY m.res_id,v.create_date,v.id
        ''', ('crm.lead', tuple(lead_ids), 'crm.lead'))
        for lead_id, row_id, at, field, old, new in self.env.cr.fetchall():
            if at:
                changes[lead_id].append({'id': row_id, 'at': at, 'field': field,
                                         'old': old, 'new': new})
        return changes

    def _find_or_create_progress(self, funnel, leads):
        """COMPATIBILITY: never create progress from a board read.

        Legacy V01/V02 auto-generated progress must not re-enter any queue.
        """
        recs = self.env['sgt.crm002.progress'].sudo().search([
            ('funnel_id', '=', funnel.id), ('lead_id', 'in', leads.ids),
            '|', ('intake_active', '=', True), ('completed_at', '!=', False),
        ])
        return {p.lead_id.id: p for p in recs}

    @api.model
    def board(self, code, department_id=False, user_id=False, offset=0, limit=100):
        """Single protected entry point for all funnel board data."""
        funnel = self._find_funnel(code)
        self._check_funnel(funnel)
        offset = max(0, int(offset or 0))
        limit = max(1, min(150, int(limit or 100)))
        domain, warning = (
            ([('type', '=', 'opportunity'), '|',
              ('sgt_crm002_funnel_id', '=', False), ('sgt_crm002_step', '=', 'potential')], False)
            if funnel.is_main else
            ([('sgt_crm002_funnel_id', '=', funnel.id),
              ('sgt_crm002_step', 'in', ['data', 'verified', 'potential'])], False)
        )
        domain += self._staff_domain(department_id, user_id)
        # Unlike standard CRM Pipeline, do not secretly apply assigned_to_me.
        lead_model = self.env['crm.lead']
        total = lead_model.search_count(domain)
        leads = lead_model.search(domain, order='write_date desc, id desc', limit=limit, offset=offset)
        now = fields.Datetime.now()
        stage_records = self.env['crm.stage'].search([], order='sequence,id') if funnel.is_main else []
        stages = [{'key': str(s.id), 'name': s.name} for s in stage_records] if funnel.is_main else [
            {'key': 'data', 'name': '1.Data'},
            {'key': 'verified', 'name': '2.Verified'},
            {'key': 'potential', 'name': '3.Potential'},
        ]
        progress = {} if funnel.is_main else self._find_or_create_progress(funnel, leads)
        visits = defaultdict(list)
        if progress:
            for v in self.env['sgt.crm002.stage.visit'].sudo().search([
                ('progress_id', 'in', [p.id for p in progress.values()])
            ]):
                visits[v.progress_id.id].append(v)
        tracking = self._visit_tracking(leads.ids) if progress else {}
        won_stage_ids = set(self.env['crm.stage'].search([('is_won', '=', True)]).ids) if progress else set()
        cards = []
        for lead in leads:
            closed = lead.won_status in ('won', 'lost') or not lead.active
            item = {
                'id': lead.id, 'name': lead.name, 'company': (lead.x_company if 'x_company' in lead._fields else False) or lead.partner_name or '',
                'partner': lead.partner_id.display_name if lead.partner_id else '',
                'phone': lead.phone or '', 'email': lead.email_from or '',
                'user': lead.user_id.name if lead.user_id else '',
                'tags': lead.tag_ids.mapped('name'),
                'stage': str(lead.stage_id.id) if funnel.is_main and lead.stage_id else '',
                'total_days': full_days((now - lead.create_date).total_seconds()) if lead.create_date else 0,
                'closed': bool(closed),
            }
            if not funnel.is_main:
                p = progress.get(lead.id)
                if not p:
                    continue
                item['stage'] = p.stage_key
                windows = active_windows(
                    lead.create_date, now, lead.stage_id.id if lead.stage_id else 0,
                    lead.active, won_stage_ids, tracking[lead.id],
                    date_closed=lead.date_closed, currently_closed=closed)
                spans = [(v.started_at, v.ended_at) for v in visits[p.id]
                         if v.stage_key == p.stage_key]
                days = full_days(visit_seconds(spans, windows, now))
                item['stage_days'] = days
                item['stage_color'] = stage_color(days, closed)
            else:
                item['stage_days'] = None
                item['stage_color'] = 'stopped' if closed else 'neutral'
                # Reuse CRM-001 V02 computed indicators when installed, without
                # making it a hard dependency for older databases.
                if 'sgt_crm001_stage_text' in lead._fields:
                    item['crm001_stage_text'] = lead.sgt_crm001_stage_text or ''
                    item['crm001_total_text'] = lead.sgt_crm001_total_text or ''
                    item['stage_color'] = lead.sgt_crm001_stage_color or item['stage_color']
            cards.append(item)
        # Some data may use an unavailable stage; keep a valid fallback column.
        if funnel.is_main and any(c['stage'] not in {s['key'] for s in stages} for c in cards):
            stages.append({'key': '', 'name': 'Chưa phân loại'})
        return {'code': code, 'name': funnel.name, 'is_main': funnel.is_main,
                'stages': stages, 'cards': cards, 'total': total,
                'offset': offset, 'limit': limit, 'warning': warning}

    @api.model
    def move(self, code, lead_id, new_stage):
        """Compatibility path: no implicit enrollment of matching historical Deals."""
        funnel = self._find_funnel(code)
        self._check_funnel(funnel)
        if funnel.group_key != 'data':
            raise UserError('Chỉ phễu thuộc Data Funnel dùng thao tác này.')
        lead = self.env['crm.lead'].browse(int(lead_id)).exists()
        lead.check_access('write')
        if not lead.sgt_crm002_funnel_id or lead.sgt_crm002_funnel_id.id != funnel.id:
            raise AccessError('CRM-002: Deal không thuộc hàng đợi phễu này.')
        return self._transition_intake(lead, new_stage)

    @api.model
    def settings(self):
        self._check_admin()
        fs = self.env['sgt.crm002.funnel'].sudo().search([('active', '=', True)])
        ds = self.env['hr.department'].sudo().search([('active', '=', True)], order='name')
        tags = self.env['crm.tag'].sudo().search([], order='name', limit=1000)
        sources = self.env['utm.source'].sudo().search([], order='name', limit=1000)
        return {
            'funnels': [{
                'code': f.code, 'name': f.name, 'is_main': f.is_main,
                'filter_mode': f.filter_mode, 'tag_id': f.tag_id.id or False,
                'source_id': f.source_id.id or False,
                'initial_tag_name': f.initial_tag_name or '',
                'department_ids': f.allowed_department_ids.ids,
            } for f in fs],
            'departments': [{'id': d.id, 'name': d.name} for d in ds],
            'tags': [{'id': t.id, 'name': t.name} for t in tags],
            'sources': [{'id': s.id, 'name': s.name} for s in sources],
        }

    @api.model
    def save_permissions(self, department_id, codes):
        self._check_admin()
        department = self.env['hr.department'].sudo().browse(int(department_id)).exists()
        if not department:
            raise UserError('Department không tồn tại.')
        if not isinstance(codes, list) or any(not isinstance(c, str) for c in codes):
            raise ValidationError('Danh sách phễu không hợp lệ.')
        funnels = self.env['sgt.crm002.funnel'].sudo().search([('active', '=', True)])
        known = set(funnels.mapped('code'))
        if not set(codes).issubset(known):
            raise ValidationError('Có phễu không hợp lệ.')
        for f in funnels:
            if f.code in codes:
                f.write({'allowed_department_ids': [(4, department.id)]})
            else:
                f.write({'allowed_department_ids': [(3, department.id)]})
        return {'ok': True}

    @api.model
    def save_filter(self, code, mode, tag_id=False, source_id=False):
        self._check_admin()
        funnel = self._find_funnel(code)
        if funnel.is_main:
            raise UserError('Match Making dùng Pipeline CRM hiện tại, không cấu hình Tag/Source.')
        if mode not in ('tag', 'source'):
            raise ValidationError('Kiểu lọc không hợp lệ.')
        if mode == 'tag':
            tag = self.env['crm.tag'].sudo().browse(int(tag_id or 0)).exists()
            if not tag:
                raise UserError('Phải chọn Tag có thật.')
            values = {'filter_mode': mode, 'tag_id': tag.id, 'source_id': False}
        else:
            source = self.env['utm.source'].sudo().browse(int(source_id or 0)).exists()
            if not source:
                raise UserError('Phải chọn Source có thật.')
            values = {'filter_mode': mode, 'source_id': source.id, 'tag_id': False}
        funnel.sudo().write(values)
        return {'ok': True}

    # Update_003: native Odoo Kanban on crm.lead, with an explicit intake queue.
    @api.model
    def open_intake(self, code, department_id=False, user_id=False):
        funnel = self._find_funnel(code)
        self._check_funnel(funnel)
        if funnel.is_main or funnel.group_key == 'mm':
            raise UserError('Match Making sử dụng CRM Pipeline chuẩn.')
        if department_id or user_id:
            self._staff_domain(department_id, user_id)  # validate admin scope
        if funnel.group_key == 'sale':
            return self._open_sale(funnel)
        domain = [
            ('sgt_crm002_funnel_id', '=', funnel.id),
            ('sgt_crm002_step', 'in', ['data', 'verified', 'potential']),
        ]
        view = self.env.ref('sgt_crm_campaign.view_crm002_intake_kanban')
        # The native action uses the exact Xinyang Odoo Kanban card/template.
        # Update_013: same view switcher as the stock CRM Pipeline (List, Calendar, Pivot, Graph, Activity).
        views, group_ctx = self._funnel_views(view.id, 'sgt_crm002_step', 'sgt_crm_campaign.view_crm002_intake_list')
        return {
            'type': 'ir.actions.act_window', 'name': funnel.name,
            'res_model': 'crm.lead', 'view_mode': VIEW_MODES,
            'views': views,
            'target': 'current', 'domain': domain,
            'context': {
                **group_ctx,
                'default_type': 'opportunity',
                'default_sgt_crm002_funnel_id': funnel.id,
                'default_sgt_crm002_step': 'data',
                'sgt_crm002_funnel_code': funnel.code,
                'sgt_crm002_funnel_group': 'data',
                'crm002_department_id': department_id or False,
                'crm002_user_id': user_id or False,
                'search_default_assigned_to_me': 0,
                'show_user_team_stages': 0,
            },
            'help': 'Tạo Deal mới để bắt đầu tiếp nhận và xử lý.',
        }

    @api.model
    def _funnel_views(self, kanban_view_id, stage_field, list_xmlid='crm.crm_case_tree_view_oppor'):
        """Update_013: the view switcher of the stock CRM Pipeline for a Data / Sale funnel.

        Kanban keeps the funnel's own card; List / Calendar / Pivot / Graph / Activity are the
        stock CRM views (same ids the stock Pipeline action uses; a missing id falls back to
        the model's default view of that type).  Update_014: the List is the stock list with its
        Stage column replaced by the funnel's own stage.  The funnel's own stage field is passed as the
        default grouping of List, Pivot and Graph, so the columns match the Kanban.
        """
        def stock(xmlid):
            view = self.env.ref(xmlid, raise_if_not_found=False)
            return view.id if view else False
        views = [
            (kanban_view_id, 'kanban'),
            (stock(list_xmlid), 'list'),
            (stock('crm.crm_case_calendar_view_leads'), 'calendar'),
            (stock('crm.crm_lead_view_pivot'), 'pivot'),
            (stock('crm.crm_lead_view_graph'), 'graph'),
            (stock('crm.crm_lead_view_activity'), 'activity'),
            (False, 'form'),
        ]
        group_ctx = {
            'group_by': [stage_field],
            'pivot_row_groupby': [stage_field],
            'graph_groupbys': [stage_field],
        }
        return views, group_ctx

    def _open_sale(self, funnel):
        """Kanban of a Sale funnel (New / Renew): columns are the funnel's own stages."""
        view = self.env.ref('sgt_crm_campaign.view_crm002_sale_kanban')
        views, group_ctx = self._funnel_views(view.id, 'sgt_crm002_sale_stage_id', 'sgt_crm_campaign.view_crm002_sale_list')
        return {
            'type': 'ir.actions.act_window', 'name': funnel.name,
            'res_model': 'crm.lead', 'view_mode': VIEW_MODES,
            'views': views,
            'target': 'current',
            'domain': [('sgt_crm002_sale_funnel_id', '=', funnel.id)],
            'context': {
                **group_ctx,
                'sgt_crm002_funnel_code': funnel.code,
                'sgt_crm002_funnel_group': 'sale',
                'search_default_assigned_to_me': 0,
                'show_user_team_stages': 0,
            },
            'help': 'Chưa có Deal trong phễu này. Deal vào phễu qua Luật bàn giao (Cài đặt).',
        }

    def _activate_progress(self, funnel, lead):
        """Only explicit new lead routing activates a queue.

        Update_001/002 auto-generated progress remains INACTIVE on upgrade.
        They are kept for audit and do not appear on the native board.
        """
        model = self.env['sgt.crm002.progress'].sudo()
        p = model.search([('funnel_id', '=', funnel.id), ('lead_id', '=', lead.id)], limit=1)
        now = fields.Datetime.now()
        if not p:
            p = model.create({
                'funnel_id': funnel.id, 'lead_id': lead.id,
                'stage_key': 'data', 'intake_active': True,
                'intake_created_at': now,
            })
        else:
            p.write({'intake_active': True, 'completed_at': False,
                     'stage_key': 'data', 'intake_created_at': now})
        self.env['sgt.crm002.stage.visit'].sudo().create({
            'progress_id': p.id, 'stage_key': 'data', 'started_at': now})
        return p

    def _transition_intake(self, lead, step):
        """Move intake step without duplicating crm.lead.

        Potential is a ONE-TIME HANDOFF, but remains a persistent completed
        column in Data Funnel. Where the Deal goes next is decided by the
        hand-off rules (Settings), never by a hard-coded stage name.
        """
        funnel = lead.sgt_crm002_funnel_id
        if not funnel or step not in ('data', 'verified', 'potential'):
            raise UserError('CRM-002: Trạng thái tiếp nhận không hợp lệ.')
        self._check_funnel(funnel)
        # Serialize concurrent Kanban moves of the same Deal so a double drag
        # can never reset its CRM Pipeline stage or duplicate handoff history.
        self.env.cr.execute('SELECT id FROM crm_lead WHERE id = %s FOR UPDATE', (lead.id,))
        lead.invalidate_recordset(['sgt_crm002_step', 'sgt_crm002_funnel_id'])
        if not lead.sgt_crm002_funnel_id or lead.sgt_crm002_funnel_id.id != funnel.id:
            raise UserError('CRM-002: Deal không còn thuộc phễu tiếp nhận này.')
        model = self.env['sgt.crm002.progress'].sudo()
        p = model.search([('lead_id', '=', lead.id), ('funnel_id', '=', funnel.id)], limit=1)
        if not p:
            raise UserError('CRM-002: Không có tiến trình tiếp nhận hợp lệ cho Deal này.')
        # A completed intake can no longer move backwards. A second Potential
        # request is idempotent and MUST NOT reset a later CRM Stage.
        if p.completed_at or lead.sgt_crm002_step == 'potential':
            if p.completed_at and lead.sgt_crm002_step == 'potential' and step == 'potential':
                return {'ok': True, 'already_handed_off': True}
            raise UserError('CRM-002: Deal đã bàn giao tại 3.Potential, không được kéo ngược về Data/Verified.')
        if not p.intake_active:
            raise UserError('CRM-002: Tiến trình chưa được kích hoạt cho Deal này.')
        if lead.won_status in ('won', 'lost') or not lead.active:
            raise UserError('CRM-002: Deal đã Won/Lost. Hãy mở lại trong CRM.')
        if lead.sgt_crm002_step == step:
            return {'ok': True}
        now = fields.Datetime.now()
        old_step = lead.sgt_crm002_step
        visit_model = self.env['sgt.crm002.stage.visit'].sudo()
        visit_model.search([('progress_id', '=', p.id), ('ended_at', '=', False)]).write({'ended_at': now})
        if step == 'potential':
            # Keep sgt_crm002_funnel_id to retain membership in Potential.
            # The Deal itself is handed over by the active hand-off rules
            # (same crm.lead ID, same Chatter/Tags/Salesperson, no copy/create).
            lead._sgt_crm002_internal_update({'sgt_crm002_step': 'potential'})
            p.write({'stage_key': 'potential', 'intake_active': False, 'completed_at': now})
            # Potential is a completed intake milestone, not an open age timer.
            visit_model.create({'progress_id': p.id, 'stage_key': 'potential',
                                'started_at': now, 'ended_at': now})
        else:
            lead._sgt_crm002_internal_update({'sgt_crm002_step': step})
            p.write({'stage_key': step})
            visit_model.create({'progress_id': p.id, 'stage_key': step, 'started_at': now})
        # Update_015: the move between Data Funnel columns is written into the Chatter.
        names = {st.step_key: st.name for st in funnel.sudo().stage_ids if st.step_key}
        labels = dict(lead._fields['sgt_crm002_step'].selection)
        lead._sgt_crm002_log_stage_move(
            funnel.name, names.get(old_step) or labels.get(old_step), names.get(step) or labels.get(step))
        # Hand-off rules whose source is this Data Funnel column.  Errors are NOT
        # swallowed here: the whole drag is rolled back and the message is shown.
        stage = self.env['sgt.crm002.funnel.stage'].sudo().search(
            [('funnel_id', '=', funnel.id), ('step_key', '=', step)], limit=1)
        if stage:
            self.env['sgt.crm002.handoff.rule']._run_for(lead, funnel.sudo(), stage=stage)
        return {'ok': True}
