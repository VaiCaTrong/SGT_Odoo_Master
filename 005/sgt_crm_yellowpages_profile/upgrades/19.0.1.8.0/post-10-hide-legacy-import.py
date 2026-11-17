"""CRM-005 Update_009: re-ensure the Import-hide View survive Upgrade.

Runs on real Upgrade.  The helper stores the View External ID with
noupdate=True so Odoo's end-of-update cleanup does not delete it.  A failure
here is logged and rolled back to a savepoint; it never aborts the Upgrade
because the module also ships a CSS fallback that hides the legacy tab.
"""
import logging

from odoo import api, SUPERUSER_ID
from odoo.addons.sgt_crm_yellowpages_profile.hooks import ensure_hide_legacy_import

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        with cr.savepoint():
            ensure_hide_legacy_import(env)
    except Exception:
        _logger.exception('CRM-005 Update_009: Import-hide View could not be '
                          'installed; CSS fallback remains active. No data changed.')
