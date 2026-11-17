"""CRM-005 Update_010 upgrade steps (no CRM data is read or written).

1. Re-ensure the Import-hide View (External ID noupdate=True).
2. Remove the obsolete Contact Sync relocation View created by older CRM-005
   releases, if it is still present, so the existing Contact Sync block shows
   where its own addon places it.

Each step is isolated in a savepoint and never aborts the Upgrade.  The old
CRM-005 child models and x_yp_* fields that are no longer defined are removed
by Odoo's standard end-of-update cleanup; see README for the expected log lines.
"""
import logging

from odoo import api, SUPERUSER_ID
from odoo.addons.sgt_crm_yellowpages_profile.hooks import (
    ensure_hide_legacy_import,
    remove_stale_contact_sync_relocation,
)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for step in (ensure_hide_legacy_import, remove_stale_contact_sync_relocation):
        try:
            with cr.savepoint():
                step(env)
        except Exception:
            _logger.exception('CRM-005 Update_010: step %s failed and was '
                              'rolled back; Upgrade continues.', step.__name__)
