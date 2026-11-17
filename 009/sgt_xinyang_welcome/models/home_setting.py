"""Xinyang Home settings: one record for the whole Home app.

Add future Home settings as new fields on this model and show them in the form
view of the "Settings" menu (Home > Settings). Every internal user can READ this
record (Home needs the values), so never store secrets here.
"""
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

AUTOPLAY_MIN = 3
AUTOPLAY_MAX = 3600
HEATMAP_GROUP_XMLID = 'sgt_xinyang_welcome.group_home_heatmap'
DASHBOARD_GROUP_XMLID = 'sgt_xinyang_welcome.group_home_dashboard'


class SgtHomeSetting(models.Model):
    _name = 'sgt.home.setting'
    _description = 'Xinyang Home settings'

    name = fields.Char(default='Home settings', readonly=True)
    autoplay_mode = fields.Selection([
        ('off', 'Off (no automatic change)'),
        ('10', 'Every 10 seconds'),
        ('30', 'Every 30 seconds'),
        ('custom', 'Custom (type the seconds)'),
    ], string='Change product images automatically', required=True, default='30',
        help='How often the picture in the product popup changes by itself when a product has several pictures.')
    autoplay_custom_seconds = fields.Integer(
        string='Custom seconds', default=20,
        help='Used when the mode is "Custom". Allowed: %s to %s seconds.' % (AUTOPLAY_MIN, AUTOPLAY_MAX))
    autoplay_seconds = fields.Integer(
        string='Seconds between images (0 = off)', compute='_compute_autoplay_seconds', store=True)

    @api.depends('autoplay_mode', 'autoplay_custom_seconds')
    def _compute_autoplay_seconds(self):
        for rec in self:
            if rec.autoplay_mode == 'off':
                rec.autoplay_seconds = 0
            elif rec.autoplay_mode == 'custom':
                rec.autoplay_seconds = rec.autoplay_custom_seconds or 0
            else:
                rec.autoplay_seconds = int(rec.autoplay_mode or 30)

    @api.constrains('autoplay_mode', 'autoplay_custom_seconds')
    def _check_autoplay_custom_seconds(self):
        for rec in self:
            if rec.autoplay_mode == 'custom' and not (AUTOPLAY_MIN <= rec.autoplay_custom_seconds <= AUTOPLAY_MAX):
                raise ValidationError(
                    'Custom seconds must be between %s and %s.' % (AUTOPLAY_MIN, AUTOPLAY_MAX))

    # ---- Heat Map access (who may open the XINYANG MAP from Home) -----------------------------------------------------
    # Shown only to Settings Administrators. It edits the members of the group "Home > Heat Map Viewer", so it is the same
    # right as ticking the group on the user form (Settings > Users); nothing is read or written with sudo.
    heatmap_user_ids = fields.Many2many(
        'res.users', string='People who can open the Heat Map', compute='_compute_heatmap_users',
        inverse='_inverse_heatmap_users', domain=[('share', '=', False)], groups='base.group_system',
        help='Internal users who may open the Heat Map from the Home menu. Their Deals and Contacts still follow their own CRM rights.')
    heatmap_inherited_user_ids = fields.Many2many(
        'res.users', string='Also allowed automatically', compute='_compute_heatmap_users', groups='base.group_system',
        help='Home Managers get the Heat Map right through their role. Settings Administrators can always open it.')

    heatmap_group_missing = fields.Boolean(
        compute='_compute_heatmap_users', groups='base.group_system',
        help='True when the module was not upgraded yet, so the group "Heat Map Viewer" does not exist in this database.')

    def _heatmap_group(self):
        return self.env.ref(HEATMAP_GROUP_XMLID, raise_if_not_found=False)

    @api.depends_context('uid')
    def _compute_heatmap_users(self):
        is_admin = self.env.user.has_group('base.group_system')
        group = self._heatmap_group() if is_admin else None
        for rec in self:
            rec.heatmap_user_ids = group.user_ids if group else False
            rec.heatmap_inherited_user_ids = (group.all_user_ids - group.user_ids) if group else False
            rec.heatmap_group_missing = bool(is_admin and not group)

    def _inverse_heatmap_users(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Only Settings Administrators can change who may open the Heat Map.')
        group = self._heatmap_group()
        if not group:
            raise UserError('The group "Heat Map Viewer" does not exist yet: upgrade the module "XINYANG | UI-009 Login + Home" first.')
        for rec in self[:1]:
            group.user_ids = rec.heatmap_user_ids


    # ---- KPI Dashboard access (who may open the 4 main KPIs from Home) -----------------------------------------------
    dashboard_user_ids = fields.Many2many(
        'res.users', string='People who can open the KPI Dashboard', compute='_compute_dashboard_users',
        inverse='_inverse_dashboard_users', domain=[('share', '=', False)], groups='base.group_system',
        help='Internal users who may open the Dashboard (GB, Content, Data, Match Making) from the Home menu. '
             'Data and Match Making still follow their own CRM rights.')
    dashboard_inherited_user_ids = fields.Many2many(
        'res.users', string='Also allowed to open the Dashboard', compute='_compute_dashboard_users', groups='base.group_system',
        help='Home Managers get this right through their role. Settings Administrators can always open it.')
    dashboard_group_missing = fields.Boolean(compute='_compute_dashboard_users', groups='base.group_system')

    def _dashboard_group(self):
        return self.env.ref(DASHBOARD_GROUP_XMLID, raise_if_not_found=False)

    @api.depends_context('uid')
    def _compute_dashboard_users(self):
        is_admin = self.env.user.has_group('base.group_system')
        group = self._dashboard_group() if is_admin else None
        for rec in self:
            rec.dashboard_user_ids = group.user_ids if group else False
            rec.dashboard_inherited_user_ids = (group.all_user_ids - group.user_ids) if group else False
            rec.dashboard_group_missing = bool(is_admin and not group)

    def _inverse_dashboard_users(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Only Settings Administrators can change who may open the KPI Dashboard.')
        group = self._dashboard_group()
        if not group:
            raise UserError('The group "Dashboard Viewer" does not exist yet: upgrade the module "XINYANG | UI-009 Login + Home" first.')
        for rec in self[:1]:
            group.user_ids = rec.dashboard_user_ids

    # ---- social360 (SGT) connection for GB and Content ---------------------------------------------------------------
    # One READ-ONLY service account. Only Settings Administrators can see or change these fields (field-level group), the key
    # never goes to the browser; the KPI controller reads them with an elevated environment for exactly these four fields.
    kpi_sgt_url = fields.Char(string='social360 URL', default='https://social360.sge.vn', groups='base.group_system',
                              help='Address of the SGT Odoo, without /odoo at the end.')
    kpi_sgt_db = fields.Char(string='social360 database', default='social360', groups='base.group_system')
    kpi_sgt_login = fields.Char(string='Service account login', groups='base.group_system',
                                help='A read-only user on social360 that can see Project XINYANG, its Content and the GB Logs.')
    kpi_sgt_key = fields.Char(string='API key / password', groups='base.group_system',
                              help='Preferably an API key created for that user on social360 (Preferences > Account Security).')

    @api.model
    def _kpi_sgt_config(self):
        """Connection values for the KPI controller. Reads the admin-only fields with an elevated environment; never returned to a browser."""
        rec = self.sudo().search([], limit=1)
        if not rec:
            return {}
        return {'url': rec.kpi_sgt_url or '', 'db': rec.kpi_sgt_db or '', 'login': rec.kpi_sgt_login or '', 'secret': rec.kpi_sgt_key or ''}
