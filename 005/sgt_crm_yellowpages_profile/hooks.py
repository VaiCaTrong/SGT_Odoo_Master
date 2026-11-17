"""CRM-005 integration with the pre-existing custom Deal Import view.

The historic Deal Import Fields tab is installed by an independent inherited
View without a stable External ID.  An XPath that targets that tab from a
sibling View fails Odoo 19 install validation, so the hide rule is attached as a
CHILD of the view that creates the tab.

Update_007 root-cause fix: a View created from Python gets an External ID
(ir.model.data).  Odoo's end-of-update cleanup (``ir.model.data._process_end``)
deletes every External ID of an updated module with ``noupdate = False`` that
was not loaded from a data file.  The previous releases created that External
ID with ``noupdate = False``, so the hide View was deleted at the end of every
install/Upgrade (the hard gate passed first, because it runs before cleanup).
The External ID is now ``noupdate = True``.
"""

from lxml import etree
import logging

_logger = logging.getLogger(__name__)

MODULE = 'sgt_crm_yellowpages_profile'
HIDE_VIEW_XMLID_NAME = 'view_crm005_hide_legacy_import'
HIDE_VIEW_NAME = 'crm.lead.form.crm005.hide_legacy_import'


def post_init_hook(env):
    """For fresh installations, hide the legacy Import notebook.

    Update_010: the Contact Sync relocation was removed; the existing Sync /
    Contact Sync blocks stay exactly where their own addons put them.
    """
    ensure_hide_legacy_import(env)


def _find_legacy_import_view(env):
    """Return (view, notebook_elements) of the ONE original Import view, or None."""
    View = env['ir.ui.view'].sudo()
    parent = env.ref('crm.crm_lead_view_form', raise_if_not_found=True)
    candidates = View.search([
        ('model', '=', 'crm.lead'),
        ('type', '=', 'form'),
        ('inherit_id', '=', parent.id),
        ('active', '=', True),
    ])
    matched = []
    for candidate in candidates:
        # The original extension MUST introduce a notebook/page itself; a mere
        # reference to x_deal_id in CRM-005's own Form does NOT qualify.
        try:
            source = etree.fromstring(candidate.arch_db.encode('utf-8'))
        except (etree.XMLSyntaxError, AttributeError, UnicodeError):
            continue
        notebooks = source.xpath("//notebook[page[.//field[@name='x_deal_id']]]")
        if notebooks:
            matched.append((candidate, notebooks))
    return matched


def ensure_hide_legacy_import(env):
    """Remove ONLY the original standalone Import notebook from Deal forms.

    Safe on INSTALL and on UPGRADE and idempotent.  The original source View
    and all imported field definitions/data stay untouched; the 52 legacy
    fields remain reachable in the closed ``Details - Deal Import Fields``
    element of the CRM-005 form.  Never raises for an unexpected View layout:
    the CSS rule shipped with this module keeps the tab hidden, and the
    problem is logged as WARNING/ERROR for inspection.
    """
    View = env['ir.ui.view'].sudo().with_context(lang='en_US', active_test=False)
    Imd = env['ir.model.data'].sudo()

    matched = _find_legacy_import_view(env)
    if len(matched) != 1:
        _logger.warning(
            'CRM-005 Update_007: expected exactly one active original Deal '
            'Import View with a notebook/page holding x_deal_id, found %s. '
            'Hide View NOT created; the CSS fallback still hides the tab. '
            'No CRM data was modified.', len(matched))
        return False

    legacy_view, notebooks = matched[0]
    if len(notebooks) != 1:
        _logger.warning('CRM-005: the original import View has more than one '
                        'notebook with x_deal_id; refusing ambiguous hiding.')
        return False
    notebook = notebooks[0]
    target_pages = notebook.xpath("./page[.//field[@name='x_deal_id']]")
    if len(target_pages) != 1:
        _logger.warning('CRM-005: unable to identify one original import page.')
        return False

    # When that legacy notebook has only the import page, remove its entire
    # wrapper; otherwise remove only the import page so unrelated pages live.
    if len(notebook.xpath('./page')) == 1:
        child_arch = ("<data><xpath expr=\"//notebook[page[.//field[@name='x_deal_id']]]\" "
                      "position=\"replace\"/></data>")
        removal = 'notebook'
    else:
        child_arch = ("<data><xpath expr=\"//page[.//field[@name='x_deal_id']]\" "
                      "position=\"replace\"/></data>")
        removal = 'page'

    values = {
        'name': HIDE_VIEW_NAME,
        'model': 'crm.lead',
        'type': 'form',
        'mode': 'extension',
        'priority': 95,
        'active': True,
        'inherit_id': legacy_view.id,
        'arch_db': child_arch,
    }

    imd = Imd.search([('module', '=', MODULE), ('name', '=', HIDE_VIEW_XMLID_NAME)], limit=1)
    hide_view = View.browse()
    if imd:
        if imd.model == 'ir.ui.view':
            hide_view = View.browse(imd.res_id).exists()
        if not hide_view:
            # Dangling or foreign External ID left by an earlier release.
            _logger.info('CRM-005: dropping stale External ID %s', imd.id)
            imd.unlink()
            imd = Imd.browse()

    if hide_view:
        hide_view.write(values)
        _logger.info('CRM-005 updated owned Import-hide View %s', hide_view.id)
    else:
        # Recover an earlier View that lost its External ID, only if unique.
        orphans = View.search([
            ('name', '=', HIDE_VIEW_NAME), ('model', '=', 'crm.lead'),
            ('inherit_id', '=', legacy_view.id),
        ])
        if len(orphans) > 1:
            _logger.warning('CRM-005: multiple orphan Import-hide Views %s; '
                            'manual inspection required.', orphans.ids)
            return False
        if orphans:
            hide_view = orphans
            hide_view.write(values)
        else:
            hide_view = View.create(values)
        _logger.info('CRM-005 registered Import-hide View %s', hide_view.id)

    # THE FIX: noupdate=True protects the External ID, and so the View, from
    # ir.model.data._process_end(), which would otherwise delete it at the end
    # of this very Upgrade because it is not declared in a data file.
    if imd:
        if not imd.noupdate:
            imd.write({'noupdate': True})
    else:
        Imd.create({
            'module': MODULE,
            'name': HIDE_VIEW_XMLID_NAME,
            'model': 'ir.ui.view',
            'res_id': hide_view.id,
            'noupdate': True,
        })

    # Diagnostic only (never fatal): what Odoo composes right now.
    try:
        parent = env.ref('crm.crm_lead_view_form')
        final = parent.sudo().with_context(
            load_all_views=True, lang='en_US', inherit_branding=False,
        )._get_combined_arch()
        if final.xpath("//page[.//field[@name='x_deal_id']]"):
            _logger.error('CRM-005: legacy Import tab is STILL present in the '
                          'resolved CRM Form (view %s). CSS fallback applies; '
                          'inspect View precedence.', hide_view.id)
        details = final.xpath(
            "//details[contains(concat(' ', normalize-space(@class), ' '), "
            "' sgt_crm005_import_details ')]")
        if len(details) != 1:
            _logger.error('CRM-005: expected one Details control in the '
                          'resolved Form, found %s.', len(details))
        else:
            _logger.info('CRM-005: original Import %s hidden via View %s '
                         '(noupdate External ID); single Details verified.',
                         removal, hide_view.id)
    except Exception:  # pragma: no cover - diagnostics must not abort Upgrade
        _logger.exception('CRM-005: combined-form diagnostic failed')
    return hide_view


def remove_stale_contact_sync_relocation(env):
    """Update_010: delete the View created by earlier CRM-005 releases that
    hid the original Contact Sync block (if it still exists).  Only the View
    owned by this addon (by External ID) is touched; nothing else is changed.
    """
    xmlid = MODULE + '.view_crm005_relocate_contact_sync'
    view = env.ref(xmlid, raise_if_not_found=False)
    if view and view._name == 'ir.ui.view':
        _logger.info('CRM-005 Update_010: removing obsolete Contact Sync '
                     'relocation view %s', view.id)
        view.sudo().unlink()
        return True
    return False
