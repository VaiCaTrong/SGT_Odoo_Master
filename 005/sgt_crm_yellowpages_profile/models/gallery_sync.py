"""CRM-005 Update_044: manually sync Image Gallery into linked Documents-008 folder."""
import hashlib

from odoo import _, models
from odoo.exceptions import AccessError, UserError

from .gallery_sync_utils import (
    GallerySyncError, gallery_entries, gallery_image_filename, read_image_source,
)


class CrmLeadGallerySync(models.Model):
    _inherit = 'crm.lead'

    def _crm005_gallery_snapshot(self):
        self.ensure_one()
        self.check_access('read')
        html = self.x_yp_gallery_html or ''
        return hashlib.sha256(html.encode('utf-8')).hexdigest(), gallery_entries(html)

    def action_crm005_gallery_sync_manifest(self):
        """Read-only manifest to drive visible progress, no remote image fetching."""
        self.ensure_one()
        token, sources = self._crm005_gallery_snapshot()
        info = self.env['argo.document.folder'].explorer_deal_folder_info(self.id)
        folder = info.get('folder')
        if not folder or not info.get('linked'):
            raise UserError(_('Hãy tạo và liên kết Documents folder trước khi đồng bộ Gallery.'))
        if not folder.get('can_upload'):
            raise AccessError(_('Bạn cần quyền Edit trên folder Documents để đồng bộ ảnh.'))
        return {'token': token, 'total': len(sources)}

    def _crm005_attachment_image_bytes(self, attachment_id):
        """Only read an attachment with the *current user's* Odoo read rights."""
        attachment = self.env['ir.attachment'].browse(int(attachment_id)).exists()
        if not attachment:
            raise GallerySyncError('Attachment ảnh không còn tồn tại.')
        try:
            attachment.check_access('read')
            return attachment.raw or b''
        except AccessError as exc:
            raise GallerySyncError('Bạn không có quyền đọc attachment ảnh gốc.') from exc

    def action_crm005_sync_gallery_batch(self, offset, token, batch_size=2):
        """Copy at most 2 images per RPC, respecting CRM, folder, and file ACLs.

        Each file gets the caller's create_uid, stays in Image Gallery, and
        is skipped when identical file bytes already exist in this folder.
        No sudo on file creation and no remote Odoo credentials are exposed.
        """
        self.ensure_one()
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise UserError(_('Vị trí đồng bộ ảnh không hợp lệ.'))
        if batch_size != 2:
            raise UserError(_('Kích thước lô đồng bộ không hợp lệ.'))
        current_token, sources = self._crm005_gallery_snapshot()
        if token != current_token:
            raise UserError(_('Image Gallery đã thay đổi. Vui lòng nhấn đồng bộ lại.'))
        Folder = self.env['argo.document.folder']
        info = Folder.explorer_deal_folder_info(self.id)
        folder_info = info.get('folder')
        if not folder_info or not info.get('linked'):
            raise UserError(_('Deal chưa liên kết folder Documents có thể truy cập.'))
        folder = Folder.browse(int(folder_info['id']))
        folder._require_level('edit')
        Doc = self.env['argo.document']
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        from urllib.parse import urlsplit
        base_host = urlsplit(base_url).hostname or ''
        results = []
        for i in range(offset, min(len(sources), offset + 2)):
            try:
                with self.env.cr.savepoint():
                    image_source, caption = sources[i]
                    data, extension, mime = read_image_source(
                        image_source, attachment_reader=self._crm005_attachment_image_bytes,
                        base_host=base_host)
                    digest = hashlib.sha1(data).hexdigest()
                    if Doc.search_count([('folder_id', '=', folder.id), ('checksum', '=', digest)]):
                        results.append({'index': i + 1, 'status': 'duplicate'})
                        continue
                    name = gallery_image_filename(caption, i + 1, extension)
                    vals = Doc._prepare_content(data, name, mime, compress=False)
                    vals.update({
                        'name': Folder._unique_name(folder, vals['name'], 'file'),
                        'folder_id': folder.id,
                        'lead_id': self.id,
                    })
                    doc = Doc.with_context(image_no_postprocess=True).create(vals)
                    results.append({'index': i + 1, 'status': 'created', 'document_id': doc.id})
            except GallerySyncError as exc:
                results.append({'index': i + 1, 'status': 'failed', 'reason': str(exc)})
            except AccessError:
                # Do not silently turn ACL errors into an image failure.
                raise
            except UserError as exc:
                results.append({'index': i + 1, 'status': 'failed', 'reason': str(exc)})
            except Exception:
                # Remote sources may be broken; don't disclose internal traceback.
                results.append({'index': i + 1, 'status': 'failed',
                                'reason': 'Không lưu được ảnh; kiểm tra nguồn và quyền Documents.'})
        return {'next_offset': min(len(sources), offset + 2), 'total': len(sources),
                'results': results}
