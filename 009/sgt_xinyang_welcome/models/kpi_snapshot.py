"""Saved versions of the social360 data for the KPI Dashboard (Update_021).

One row = one "Update Data" (see kpi/snapshot.py). The version marked active is what GB and Content show; "Rollback" only moves
that mark, nothing is deleted. Only Settings Administrators can see or change these rows; the Dashboard controller reads the
active one with an elevated environment and never sends the payload to a browser.
"""
import json
import logging
import threading

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..kpi import snapshot as snap_mod
from ..kpi import sgt as sgt_mod
from ..kpi import xinyang as xy_mod

_logger = logging.getLogger(__name__)
KEEP_VERSIONS = 10
_LOCK = threading.Lock()
_PARSED = {}          # (record id, write_date) -> parsed payload; at most 3 entries


class SgtHomeKpiSnapshot(models.Model):
    _name = 'sgt.home.kpi.snapshot'
    _description = 'Saved social360 data (KPI Dashboard)'
    _order = 'taken_at desc, id desc'

    setting_id = fields.Many2one('sgt.home.setting', ondelete='cascade', index=True)
    name = fields.Char(compute='_compute_name')
    taken_at = fields.Datetime(string='Saved at', required=True, default=fields.Datetime.now, readonly=True)
    taken_by_id = fields.Many2one('res.users', string='Saved by', default=lambda self: self.env.user, readonly=True)
    connection = fields.Selection([('main', 'Main'), ('backup', 'Backup')], string='Connection', readonly=True)
    source = fields.Char(string='Read from', readonly=True)
    gb_total = fields.Integer(string='GB posts', readonly=True)
    content_total = fields.Integer(string='Content', readonly=True)
    content_approved = fields.Integer(string='Content approved', readonly=True)
    posts_total = fields.Integer(string='Latest posts', readonly=True)
    is_active = fields.Boolean(string='In use', default=False, readonly=True, index=True)
    payload = fields.Text(readonly=True, prefetch=False, groups='base.group_system')

    @api.depends('taken_at')
    def _compute_name(self):
        for rec in self:
            rec.name = 'Version %s' % (fields.Datetime.context_timestamp(rec, rec.taken_at).strftime('%d/%m/%Y %H:%M') if rec.taken_at else '')

    # ---- what the Dashboard reads ----------------------------------------------------------------------------------
    @api.model
    def _active(self):
        """{'id', 'payload', 'label'} of the version in use, or None (then the Dashboard reads social360 live)."""
        rec = self.sudo().search([('is_active', '=', True)], limit=1)
        if not rec:
            return None
        key = (rec.id, rec.write_date)
        with _LOCK:
            payload = _PARSED.get(key)
        if payload is None:
            payload = snap_mod.check_payload(json.loads(rec.payload or 'null'))
            with _LOCK:
                if len(_PARSED) >= 3:
                    _PARSED.clear()
                _PARSED[key] = payload
        return {'id': rec.id, 'payload': payload, 'label': snap_mod.label(payload)}

    # ---- Rollback / restore ---------------------------------------------------------------------------------------
    def action_use_version(self):
        """The button on each row: this version becomes the one the Dashboard shows (Rollback to an older one, or Restore a newer one)."""
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Only Settings Administrators can change the saved data in use.')
        self.ensure_one()
        if not self.payload:
            raise UserError('This version has no saved data and cannot be used.')
        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(%s)", [7021])
        if not self.env.cr.fetchone()[0]:
            raise UserError('Another update is running. Try again in a moment.')
        self.search([('is_active', '=', True), ('id', '!=', self.id)]).write({'is_active': False})
        self.write({'is_active': True})
        sgt_mod.forget_all()
        xy_mod.forget_all()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Saved data', 'message': 'The Dashboard now shows %s.' % self.name, 'type': 'success',
                           'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}}}

    def unlink(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError('Only Settings Administrators can delete saved data.')
        if any(self.mapped('is_active')):
            raise UserError('The version in use cannot be deleted. Use another version first.')
        return super().unlink()

    @api.model
    def _prune(self):
        """Keep the newest KEEP_VERSIONS versions (and always the one in use)."""
        rows = self.search([], order='taken_at desc, id desc')
        old = rows[KEEP_VERSIONS:].filtered(lambda r: not r.is_active)
        old.unlink()
