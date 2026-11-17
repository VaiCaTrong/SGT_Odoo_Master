"""Update_010 POST: "Outbound hunter" -> "Outbound Hunter" (display name only).

The funnel data records are ``noupdate``, so the rename must be done here.
Only renames if the name is still EXACTLY the old default (an Administrator's
own rename is never overwritten).  The tag ``hunter`` and the code ``hunter``
are NOT touched: deals enter the funnel by that tag.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    funnel = env['sgt.crm002.funnel'].with_context(active_test=False).search([('code', '=', 'hunter')], limit=1)
    if funnel and funnel.name == 'Outbound hunter':
        funnel.write({'name': 'Outbound Hunter'})
        _logger.info('CRM-002 Update_010: funnel hunter renamed to "Outbound Hunter".')
