"""Update_012: the stock "Crm: My Pipeline" server action (menu CRM / Sales / My Pipeline,
the top CRM menu and Configuration) calls crm.team.action_your_pipeline().  It now lands by
funnel permission instead of always opening Match Making, so every entry point is covered
without any JS."""
from odoo import api, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    @api.model
    def action_your_pipeline(self):
        return self.env['sgt.crm002.service'].landing_action()

    @api.model
    def _sgt_crm002_native_pipeline(self):
        """The unmodified Odoo "My Pipeline" action (Match Making)."""
        return super().action_your_pipeline()
