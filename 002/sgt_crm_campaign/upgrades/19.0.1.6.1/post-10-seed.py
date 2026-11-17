"""Update_007 POST: default columns and default hand-off rules (idempotent)."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.sgt_crm_campaign.hooks import seed_defaults
    seed_defaults(env)
