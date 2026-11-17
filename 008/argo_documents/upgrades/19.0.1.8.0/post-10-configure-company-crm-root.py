"""Documents-008 Update_008: atomically select the new immutable root.

IMPORTANT: Do not clear crm_shared_root on older CRM_Infor! Legacy children
use that parent flag to remain PRIVATE; clearing it would silently broaden
visibility by inheriting the public parent in _compute_effective_access.
Old folders/Deal links are never relocated, altered or removed.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    root = env.ref('argo_documents.folder_crm_information_root', raise_if_not_found=False)
    if not root or not root.exists():
        # Safety fallback if the newly introduced noupdate XML record was skipped
        # by an Odoo upgrade loader; create it only once with the stable XML ID.
        Folder = env['argo.document.folder'].sudo()
        root = Folder.create({
            'name': 'CRM Information', 'parent_id': False,
            'access_mode': 'public', 'public_level': 'view',
            'company_id': False, 'crm_shared_root': True,
            'is_locked': True, 'system_root': True,
        })
        env['ir.model.data'].sudo().create({
            'module': 'argo_documents', 'name': 'folder_crm_information_root',
            'model': 'argo.document.folder', 'res_id': root.id, 'noupdate': True,
        })
    env['ir.config_parameter'].sudo().set_param(
        'argo_documents.crm_root_folder_id', str(root.id))  # legacy compatibility only
