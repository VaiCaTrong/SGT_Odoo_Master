"""CRM-005 Update_064: add pictures of the linked Documents-008 folder to the Image Gallery.

Called by Documents-008 Update_010 (Explorer buttons / menus) and by the Documents box of the Deal.
Rules: the caller needs WRITE on the Deal and READ on every file (ordinary Odoo ACLs and record
rules); existing Gallery pictures are kept, pictures already present (same content) are skipped,
nothing is deleted. The caller (Documents-008) has already checked that the files belong to the
folder tree linked to this Deal.
"""
import hashlib

from odoo import _, models
from odoo.exceptions import AccessError, ValidationError

from .gallery_push_utils import (
    PUSH_MAX_HTML_BYTES, PUSH_MAX_IMAGES, PushImageError, existing_hashes, figure_html,
    heal_escaped_figures, merge_gallery_html, prepare_image,
)


class CrmLeadGalleryPush(models.Model):
    _inherit = 'crm.lead'

    def crm005_push_documents_to_gallery(self, document_ids):
        self.ensure_one()
        self.check_access('write')
        if not isinstance(document_ids, (list, tuple)) or not document_ids:
            raise ValidationError(_('Danh sách ảnh không hợp lệ.'))
        if len(document_ids) > PUSH_MAX_IMAGES:
            raise ValidationError(_('Mỗi lần chỉ cập nhật tối đa %s ảnh.') % PUSH_MAX_IMAGES)
        try:
            ids = list(dict.fromkeys(int(i) for i in document_ids))
        except (TypeError, ValueError, OverflowError):
            raise ValidationError(_('Danh sách ảnh không hợp lệ.'))
        if any(i <= 0 for i in ids):
            raise ValidationError(_('Danh sách ảnh không hợp lệ.'))

        original_html = str(self.x_yp_gallery_html or '')
        existing_html = heal_escaped_figures(original_html)
        seen = existing_hashes(existing_html)
        total_bytes = len(existing_html.encode('utf-8'))
        figures, skipped, duplicate = [], [], 0
        for doc in self.env['argo.document'].browse(ids).exists():
            try:
                doc.check_access('read')
            except AccessError:
                skipped.append({'name': '#%s' % doc.id, 'reason': _('Bạn không có quyền đọc file này.')})
                continue
            name = doc.name or ('#%s' % doc.id)
            if doc.file_type != 'image':
                skipped.append({'name': name, 'reason': _('Không phải file ảnh.')})
                continue
            try:
                # Same pattern as the Documents-008 download controller: access is checked above,
                # the bytes are then read with sudo (the attachment ACL is not the folder ACL).
                data, mime = prepare_image(doc.sudo().raw or b'')
            except PushImageError as exc:
                skipped.append({'name': name, 'reason': str(exc)})
                continue
            digest = hashlib.sha1(data).hexdigest()
            if digest in seen:
                duplicate += 1
                continue
            figure = figure_html(name, mime, data)
            size = len(figure.encode('utf-8'))
            if total_bytes + size > PUSH_MAX_HTML_BYTES:
                skipped.append({'name': name, 'reason': _('Image Gallery đã quá lớn, không thêm được nữa.')})
                continue
            seen.add(digest)
            total_bytes += size
            figures.append(figure)
        if figures or existing_html != original_html:
            self.write({'x_yp_gallery_html': merge_gallery_html(existing_html, figures)})
        return {'added': len(figures), 'duplicate': duplicate, 'skipped': skipped}
