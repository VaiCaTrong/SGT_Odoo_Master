from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .document import human_size


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    argo_doc_max_file_mb = fields.Integer(
        'Dung lượng tối đa mỗi file (MB)', config_parameter='argo_documents.max_file_mb', default=25)
    argo_doc_image_mode = fields.Selection(
        [('compress', 'Tự nén ảnh khi tải lên'), ('keep', 'Giữ nguyên ảnh gốc')],
        'Xử lý ảnh', config_parameter='argo_documents.image_mode', default='keep')
    argo_doc_image_max_px = fields.Integer(
        'Cạnh dài tối đa (px)', config_parameter='argo_documents.image_max_px', default=1920)
    argo_doc_image_quality = fields.Integer(
        'Chất lượng JPEG (1-95)', config_parameter='argo_documents.image_quality', default=80)
    argo_doc_trash_days = fields.Integer(
        'Tự xóa vĩnh viễn sau (ngày)', config_parameter='argo_documents.trash_days', default=0,
        help="Số ngày giữ file trong Thùng rác. 0 = không tự xóa.")
    argo_doc_storage_info = fields.Char('Dung lượng kho', compute='_compute_argo_doc_storage_info')
    @api.depends('company_id')
    def _compute_argo_doc_storage_info(self):
        stats = self.env['argo.document.folder'].sudo().explorer_storage()
        saved = max(stats['original_size'] - stats['size'], 0)
        info = _("%(count)s file · %(size)s (thùng rác %(trash)s) · đã tiết kiệm %(saved)s nhờ nén ảnh",
                 count=stats['count'], size=human_size(stats['size']),
                 trash=human_size(stats['trash_size']), saved=human_size(saved))
        for rec in self:
            rec.argo_doc_storage_info = info

    @api.constrains('argo_doc_image_quality', 'argo_doc_image_max_px', 'argo_doc_max_file_mb')
    def _check_argo_doc_values(self):
        from odoo.exceptions import ValidationError
        for rec in self:
            if rec.argo_doc_image_quality and not 1 <= rec.argo_doc_image_quality <= 95:
                raise ValidationError(_("Chất lượng JPEG phải trong khoảng 1-95."))
            if rec.argo_doc_image_max_px and rec.argo_doc_image_max_px < 320:
                raise ValidationError(_("Cạnh dài tối đa phải ≥ 320 px."))
            if rec.argo_doc_max_file_mb and rec.argo_doc_max_file_mb < 1:
                raise ValidationError(_("Dung lượng tối đa phải ≥ 1 MB."))

    def action_argo_doc_compress_existing(self):
        """Disabled until a separate evidence preservation policy is approved."""
        raise UserError(_("Nén lại ảnh cũ đã bị vô hiệu hóa để bảo vệ tài liệu gốc."))
