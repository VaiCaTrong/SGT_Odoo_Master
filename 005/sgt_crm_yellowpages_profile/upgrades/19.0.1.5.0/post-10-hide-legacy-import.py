"""CRM-005 Update_006: enforce removal of the duplicate legacy Import tab.

A post-init hook only runs on INSTALL; this is required for real upgrades.
The helper reconciles the owned child View and validates combined Form arch.
"""
from odoo import api, SUPERUSER_ID
from odoo.addons.sgt_crm_yellowpages_profile.hooks import ensure_hide_legacy_import


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ensure_hide_legacy_import(env)
