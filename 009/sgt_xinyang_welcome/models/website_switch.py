from odoo import api, fields, models

PARAM = 'sgt_xinyang_welcome.website_on'
MENU_XMLID = 'website.menu_website_configuration'
RELOAD = {'type': 'ir.actions.client', 'tag': 'reload'}


class SgtWebsiteSwitch(models.Model):
    """One record: is the Website app switched on?

    Off (default): the Website app is hidden from the app menu and the address root "/" opens the
    login page (or the Home app when signed in). On: the app menu entry is back and "/" is served by
    the website as usual. Nothing is uninstalled or deleted either way.
    """
    _name = 'sgt.website.switch'
    _description = 'Website app switch'

    name = fields.Char(default='Website', readonly=True)
    website_on = fields.Boolean(string='Active', default=False, readonly=True)

    @api.model
    def website_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM) == '1'

    @api.model
    def _get_switch(self):
        rec = self.sudo().search([], limit=1)
        return rec or self.sudo().create({'website_on': False})

    def _apply(self, on):
        """Make the Website app menu and the root-address rule follow `on`."""
        on = bool(on)
        menu = self.env.ref(MENU_XMLID, raise_if_not_found=False)
        if menu:
            menu.sudo().write({'active': on})
        self.env['ir.config_parameter'].sudo().set_param(PARAM, '1' if on else '0')
        self.sudo().write({'website_on': on})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # A freshly created switch applies its state (default: Website hidden).
        records[-1:]._apply(records[-1:].website_on)
        return records

    @api.model
    def action_open(self):
        rec = self._get_switch()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Website',
            'res_model': self._name,
            'res_id': rec.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_turn_on(self):
        self.ensure_one()
        self._apply(True)
        return RELOAD

    def action_turn_off(self):
        self.ensure_one()
        self._apply(False)
        return RELOAD
