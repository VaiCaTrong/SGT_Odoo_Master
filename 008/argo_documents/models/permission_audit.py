from odoo import fields, models


class ArgoDocumentPermissionAudit(models.Model):
    _name = 'argo.document.permission.audit'
    _description = 'Nhật ký phân quyền Documents'
    _order = 'create_date desc, id desc'
    _rec_name = 'action'

    folder_id = fields.Many2one('argo.document.folder', string='Folder', ondelete='set null', index=True, readonly=True)
    folder_ref_id = fields.Integer(string='Folder ID gốc', readonly=True, index=True)
    actor_id = fields.Many2one('res.users', string='Người thực hiện', readonly=True, required=True)
    action = fields.Char(string='Hành động', required=True, readonly=True)
    details = fields.Text(string='Chi tiết thay đổi', readonly=True)
