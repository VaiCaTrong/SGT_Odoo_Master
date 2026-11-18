"""Xinyang Home settings: one record for the whole Home app.

Add future Home settings as new fields on this model and show them in the form
view of the "Settings" menu (Home > Settings). Every internal user can READ this
record (Home needs the values), so never store secrets here.
"""
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..kpi import sgt as sgt_mod
from ..kpi import xinyang as xy_mod
from ..kpi import snapshot as snap_mod

_logger = logging.getLogger(__name__)

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

    # ---- social360 (SGT) connections for GB and Content --------------------------------------------------------------
    # Two read-only service accounts: Connection 1 (main) and Connection 2 (backup). Both are the same Odoo app with the same
    # structure; the administrator picks which one "Update Data" reads. Only Settings Administrators can see or change these
    # fields (field-level group), the keys never go to the browser; the KPI controller reads them with an elevated environment.
    kpi_sgt_active = fields.Selection(
        [('main', 'Connection 1 · main'), ('backup', 'Connection 2 · backup')], string='Update Data reads from',
        default='main', required=True, groups='base.group_system',
        help='Which connection the Update Data button (and the live reading, before any version is saved) uses. Switch it when the other one is down.')
    kpi_sgt_url = fields.Char(string='Main · URL', default='https://sgt.sge.vn', groups='base.group_system',
                              help='Address of the SGT Odoo, without /odoo at the end.')
    kpi_sgt_db = fields.Char(string='Main · database', groups='base.group_system')
    kpi_sgt_login = fields.Char(string='Main · account login', groups='base.group_system',
                                help='A user on social360 that can see Project XINYANG, its Content and the GB Logs (read only is enough).')
    kpi_sgt_key = fields.Char(string='Main · API key', groups='base.group_system',
                              help='An API key created for that user on social360 (Preferences > Security > Add API Key).')
    kpi_sgt2_url = fields.Char(string='Backup · URL', default='https://social360.sge.vn', groups='base.group_system',
                               help='Address of the second SGT Odoo, without /odoo at the end.')
    kpi_sgt2_db = fields.Char(string='Backup · database', default='social360', groups='base.group_system')
    kpi_sgt2_login = fields.Char(string='Backup · account login', groups='base.group_system')
    kpi_sgt2_key = fields.Char(string='Backup · API key', groups='base.group_system')
    kpi_snapshot_ids = fields.One2many('sgt.home.kpi.snapshot', 'setting_id', string='Saved versions', groups='base.group_system')
    kpi_snapshot_note = fields.Char(string='Data in use', compute='_compute_kpi_snapshot_note', groups='base.group_system')
    kpi_update_target = fields.Char(string='Update Data will read', compute='_compute_kpi_update_target', groups='base.group_system')

    @api.depends('kpi_sgt_active', 'kpi_sgt_url', 'kpi_sgt_db', 'kpi_sgt2_url', 'kpi_sgt2_db')
    def _compute_kpi_update_target(self):
        for rec in self:
            backup = rec.kpi_sgt_active == 'backup'
            rec.kpi_update_target = '%s: %s · database %s' % (
                'Connection 2 · backup' if backup else 'Connection 1 · main',
                (rec.kpi_sgt2_url if backup else rec.kpi_sgt_url) or '(no URL)', (rec.kpi_sgt2_db if backup else rec.kpi_sgt_db) or '(no database)')

    @api.depends('kpi_snapshot_ids.is_active', 'kpi_snapshot_ids.taken_at')
    def _compute_kpi_snapshot_note(self):
        for rec in self:
            active = rec.kpi_snapshot_ids.filtered('is_active')[:1]
            rec.kpi_snapshot_note = (
                'GB and Content show the data saved at %s (%s).' % (
                    fields.Datetime.context_timestamp(rec, active.taken_at).strftime('%d/%m/%Y %H:%M:%S'), active.source or '?')
                if active else 'No saved data yet: GB and Content are read live from the selected connection. Click Update Data to save a version.')

    @api.model
    def _kpi_sgt_config(self, which=None):
        """Connection values for the KPI controller / Update Data. Reads the admin-only fields with an elevated environment; never returned to a browser."""
        rec = self.sudo().search([], limit=1)
        if not rec:
            return {}
        which = which or rec.kpi_sgt_active or 'main'
        if which == 'backup':
            return {'which': 'backup', 'url': rec.kpi_sgt2_url or '', 'db': rec.kpi_sgt2_db or '',
                    'login': rec.kpi_sgt2_login or '', 'secret': rec.kpi_sgt2_key or ''}
        return {'which': 'main', 'url': rec.kpi_sgt_url or '', 'db': rec.kpi_sgt_db or '', 'login': rec.kpi_sgt_login or '',
                'secret': rec.kpi_sgt_key or ''}

    def action_kpi_update_data(self):
        """Read social360 now (selected connection), save it as a new version and make it the one in use. Any error leaves everything as it was."""
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Only Settings Administrators can update the saved data.')
        self.ensure_one()
        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(%s)", [7021])
        if not self.env.cr.fetchone()[0]:
            raise UserError('Another update is running. Try again in a moment.')
        cfg = self._kpi_sgt_config()
        name = 'Connection 2 · backup' if cfg.get('which') == 'backup' else 'Connection 1 · main'
        client = sgt_mod.SgtClient(cfg.get('url'), cfg.get('db'), cfg.get('login'), cfg.get('secret'))
        if not client.configured():
            raise UserError('%s is not filled in (URL, database, account login and API key). Nothing was changed.' % name)
        try:
            payload = snap_mod.take(client)
        except sgt_mod.GbError as exc:
            raise UserError('%s could not be read. Nothing was changed; the data in use stays as it was.\n\n%s' % (name, exc)) from exc
        except Exception as exc:  # noqa: BLE001 - shown to the admin, logged for the server
            _logger.exception('Update Data: unexpected error')
            raise UserError('%s could not be read (%s). Nothing was changed; the data in use stays as it was.' % (name, type(exc).__name__)) from exc
        summary = payload.get('summary') or {}
        Snapshot = self.env['sgt.home.kpi.snapshot']
        Snapshot.search([('is_active', '=', True)]).write({'is_active': False})
        Snapshot.create({
            'setting_id': self.id, 'connection': cfg.get('which'), 'source': payload.get('source'),
            'gb_total': summary.get('gb_total', 0), 'content_total': summary.get('content_total', 0),
            'content_approved': summary.get('content_approved', 0), 'posts_total': summary.get('posts', 0), 'is_active': True,
            'payload': json.dumps(payload, default=str, separators=(',', ':'))})
        Snapshot._prune()
        sgt_mod.forget_all()
        xy_mod.forget_all()
        message = 'Saved from %s: %s GB posts, %s Content, %s latest approved posts (text + image). The previous version can be restored with Rollback.' % (
            name, summary.get('gb_total', 0), summary.get('content_total', 0), summary.get('posts', 0))
        if summary.get('posts_error'):
            message += '\n\nThe latest posts could not be read (numbers were saved): %s' % summary['posts_error']
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Saved data updated', 'type': 'warning' if summary.get('posts_error') else 'success',
                           'sticky': bool(summary.get('posts_error')), 'message': message,
                           'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}}}
