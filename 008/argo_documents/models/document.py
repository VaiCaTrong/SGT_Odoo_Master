import base64
import mimetypes
import os

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, AccessError
from odoo.tools import file_open

from .folder import check_item_name, sanitize_name
from .image_tools import compress_image, make_thumbnail

FILE_TYPES = [
    ('image', 'Hình ảnh'),
    ('pdf', 'PDF'),
    ('word', 'Word'),
    ('excel', 'Excel'),
    ('powerpoint', 'PowerPoint'),
    ('video', 'Video'),
    ('archive', 'File nén'),
    ('text', 'Văn bản'),
    ('note', 'Ghi chú'),
    ('other', 'Khác'),
]

EXT_TYPES = {
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff', '.svg', '.heic', '.ico'},
    'pdf': {'.pdf'},
    'word': {'.doc', '.docx', '.odt', '.rtf'},
    'excel': {'.xls', '.xlsx', '.xlsm', '.ods', '.csv'},
    'powerpoint': {'.ppt', '.pptx', '.odp'},
    'video': {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.mp3', '.wav', '.m4a'},
    'archive': {'.zip', '.rar', '.7z', '.tar', '.gz'},
    'text': {'.txt', '.md', '.log', '.json', '.xml'},
}

NEW_FILE_KINDS = {
    'docx': ('Tài liệu Word mới.docx', 'data/templates/blank.docx',
             'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'word'),
    'xlsx': ('Bảng tính Excel mới.xlsx', 'data/templates/blank.xlsx',
             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'excel'),
    'pptx': ('Bản trình bày PowerPoint mới.pptx', 'data/templates/blank.pptx',
             'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'powerpoint'),
    'txt': ('Tài liệu văn bản mới.txt', None, 'text/plain', 'text'),
    'note': ('Ghi chú mới', None, 'text/html', 'note'),
}

TEXT_EDIT_MAX_BYTES = 2 * 1024 * 1024


def human_size(size):
    size = float(size or 0)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return f"{size:.0f} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class ArgoDocument(models.Model):
    _name = 'argo.document'
    _description = 'Tài liệu'
    _inherits = {'ir.attachment': 'ir_attachment_id'}
    _inherit = ['mail.thread']
    _order = 'name, id'

    ir_attachment_id = fields.Many2one('ir.attachment', 'File đính kèm', required=True, index=True,
                                       ondelete='cascade')
    folder_id = fields.Many2one('argo.document.folder', 'Thư mục', index=True, ondelete='restrict',
                                tracking=True)
    partner_id = fields.Many2one('res.partner', 'Khách hàng', index=True, ondelete='set null')
    lead_id = fields.Many2one('crm.lead', 'Deal / Dự án', index=True, ondelete='set null')
    file_type = fields.Selection(FILE_TYPES, 'Loại file', default='other', index=True)
    active = fields.Boolean(default=True)
    file_size_human = fields.Char('Dung lượng', compute='_compute_file_size_human')
    original_size = fields.Integer('Dung lượng gốc', readonly=True,
                                   help="Dung lượng trước khi nén (0 = không nén).")
    thumbnail = fields.Binary('Ảnh thu nhỏ', attachment=True, readonly=True)
    has_thumbnail = fields.Boolean(readonly=True)
    note_body = fields.Html('Nội dung ghi chú', sanitize_style=True)
    # Thùng rác
    trash_date = fields.Datetime('Ngày xóa', readonly=True, index=True)
    trash_root = fields.Boolean(readonly=True)
    trash_batch = fields.Char(readonly=True, index=True)
    trash_uid = fields.Many2one('res.users', 'Người xóa', readonly=True)

    @api.depends('file_size')
    def _compute_file_size_human(self):
        for doc in self:
            doc.file_size_human = human_size(doc.file_size)

    def _can_level(self, level='view'):
        Folder = self.env['argo.document.folder']
        self.ensure_one()
        if Folder._is_manager() or self.env.is_system():
            return True
        if self.sudo().folder_id:
            return Folder.browse(self.sudo().folder_id.id)._can_level(level)
        if level == 'view':
            return self.env.user.has_group('argo_documents.group_argo_documents_user')
        if level == 'edit':
            return self.env.user.has_group('argo_documents.group_argo_documents_root_creator')
        return False

    def _require_level(self, level='view'):
        Folder = self.env['argo.document.folder']
        for doc in self:
            if doc.sudo().folder_id:
                Folder.browse(doc.sudo().folder_id.id)._require_level(level)
            elif level == 'view':
                if not self.env.user.has_group('argo_documents.group_argo_documents_user') and not Folder._is_manager():
                    raise AccessError(_("Bạn chưa được cấp quyền sử dụng kho tài liệu."))
            elif level == 'edit':
                Folder._require_root_creator()
            elif not Folder._is_manager():
                raise AccessError(_("Chỉ Admin được xóa tài liệu nằm ở thư mục gốc."))

    # ------------------------------------------------------------------
    # Xử lý nội dung
    # ------------------------------------------------------------------
    @api.model
    def _detect_file_type(self, name, mimetype=None):
        ext = os.path.splitext(name or '')[1].lower()
        for ftype, exts in EXT_TYPES.items():
            if ext in exts:
                return ftype
        mimetype = mimetype or ''
        if mimetype.startswith('image/'):
            return 'image'
        if mimetype.startswith(('video/', 'audio/')):
            return 'video'
        if mimetype == 'application/pdf':
            return 'pdf'
        if mimetype.startswith('text/'):
            return 'text'
        return 'other'

    @api.model
    def _get_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'max_bytes': int(ICP.get_param('argo_documents.max_file_mb', 25) or 25) * 1024 * 1024,
            'compress': ICP.get_param('argo_documents.image_mode', 'keep') == 'compress',
            'max_px': int(ICP.get_param('argo_documents.image_max_px', 1920) or 1920),
            'quality': int(ICP.get_param('argo_documents.image_quality', 80) or 80),
        }

    @api.model
    def _prepare_content(self, data, filename, mimetype=None, compress=True):
        """Nén ảnh + kiểm tra dung lượng + tạo thumbnail. Trả về dict vals."""
        cfg = self._get_config()
        filename = check_item_name(sanitize_name(os.path.basename((filename or 'file').replace('\\', '/'))))
        mimetype = mimetype if mimetype and mimetype != 'application/octet-stream' else (
            mimetypes.guess_type(filename)[0] or mimetype)
        original_size = len(data)
        file_type = self._detect_file_type(filename, mimetype)
        vals = {'name': filename, 'original_size': 0}
        if file_type == 'image' and compress and cfg['compress']:
            result = compress_image(data, filename, cfg['max_px'], cfg['quality'])
            if result:
                data, filename, mimetype = result
                vals.update(name=filename, original_size=original_size)
        if len(data) > cfg['max_bytes']:
            raise UserError(_("File \"%(name)s\" nặng %(size)s, vượt giới hạn %(max)s MB. "
                              "Hãy nén lại hoặc chia nhỏ file trước khi tải lên.",
                              name=filename, size=human_size(len(data)), max=cfg['max_bytes'] // 1024 // 1024))
        vals.update(raw=data, file_type=file_type)
        if mimetype:
            vals['mimetype'] = mimetype
        thumb = make_thumbnail(data) if file_type == 'image' else None
        vals['thumbnail'] = base64.b64encode(thumb) if thumb else False
        vals['has_thumbnail'] = bool(thumb)
        return vals

    @api.model
    def argo_upload(self, folder_id, filename, data, mimetype=None, compress=True):
        """Tạo tài liệu từ dữ liệu upload (bytes)."""
        folder = self.env['argo.document.folder']._get_folder(folder_id)
        vals = self._prepare_content(data, filename, mimetype, compress)
        vals['name'] = self.env['argo.document.folder']._unique_name(folder, vals['name'], 'file')
        vals['folder_id'] = folder.id or False
        # Ảnh đã được xử lý ở trên -> tắt bước tự resize mặc định của Odoo (tránh PNG phình to)
        return self.with_context(image_no_postprocess=True).create(vals)

    def argo_replace(self, data, filename, mimetype=None, compress=True):
        """Thay nội dung file (cập nhật phiên bản mới), giữ tên nếu cùng đuôi."""
        self.ensure_one()
        vals = self._prepare_content(data, filename, mimetype, compress)
        old_ext = os.path.splitext(self.name)[1].lower()
        new_ext = os.path.splitext(vals['name'])[1].lower()
        if old_ext == new_ext or not new_ext:
            vals['name'] = self.name
        else:
            vals['name'] = self.env['argo.document.folder']._unique_name(
                self.folder_id, vals['name'], 'file', exclude=self)
        self.with_context(image_no_postprocess=True).write(vals)
        self.message_post(body=_("Đã thay nội dung file bằng \"%s\" (%s).", filename, human_size(len(vals['raw']))))
        return self

    @api.model_create_multi
    def create(self, vals_list):
        Folder = self.env['argo.document.folder']
        is_manager = Folder._is_manager() or self.env.is_system()
        for vals in vals_list:
            if not is_manager and ('create_uid' in vals or 'ir_attachment_id' in vals):
                raise AccessError(_("Không được giả mạo người tải lên hoặc gắn attachment khác."))
            target = Folder._get_folder(vals.get('folder_id')) if vals.get('folder_id') else Folder.browse()
            if not target and not is_manager:
                raise AccessError(_('Chỉ Documents Admin được lưu file trực tiếp ở thư mục gốc. Hãy tạo folder con trước.'))
            # Update_007: quyền tạo folder con trong CRM Infor KHÔNG phải quyền upload
            # trực tiếp vào thư mục cha Public/View.
            if target:
                target._require_level('edit')
            else:
                Folder._require_root_creator()
            if not vals.get('file_type') or vals.get('file_type') == 'other':
                vals['file_type'] = self._detect_file_type(vals.get('name'), vals.get('mimetype'))
        docs = super().create(vals_list)
        docs._link_attachment()
        for doc, vals in zip(docs, vals_list):
            if doc.file_type == 'image' and 'thumbnail' not in vals:
                doc._generate_thumbnail()
        return docs

    def write(self, vals):
        if 'create_uid' in vals or 'create_date' in vals:
            raise AccessError(_('Không được sửa lịch sử người tải lên hoặc ngày tạo file.'))
        Folder = self.env['argo.document.folder']
        if not (Folder._is_manager() or self.env.is_system()) and any(x in vals for x in (
            'create_uid', 'create_date', 'ir_attachment_id', 'trash_uid', 'trash_date',
            'trash_root', 'trash_batch')):
            raise AccessError(_("Không thể sửa thông tin quản trị và lịch sử tài liệu."))
        self._require_level('full' if vals.get('active') is False else 'edit')
        if 'folder_id' in vals:
            dest = Folder._get_folder(vals['folder_id']) if vals['folder_id'] else Folder.browse()
            if dest:
                dest._require_level('edit')
            else:
                Folder._require_root_creator()
        if 'note_body' in vals and 'raw' not in vals and 'datas' not in vals:
            res = super().write(vals)
            for doc in self.filtered(lambda d: d.file_type == 'note'):
                doc._sync_note_file()
            return res
        res = super().write(vals)
        if ('raw' in vals or 'datas' in vals) and 'thumbnail' not in vals:
            self.filtered(lambda d: d.file_type == 'image')._generate_thumbnail()
        return res

    def unlink(self):
        self._require_level('full')
        return super().unlink()

    def _link_attachment(self):
        """File gốc gắn vào chính tài liệu -> quyền xem file = quyền xem tài liệu."""
        for doc in self.sudo():
            att = doc.ir_attachment_id
            if att.res_model != self._name or att.res_id != doc.id:
                att.write({'res_model': self._name, 'res_id': doc.id})

    def _generate_thumbnail(self):
        for doc in self:
            thumb = make_thumbnail(doc.raw) if doc.raw else None
            super(ArgoDocument, doc).write({
                'thumbnail': base64.b64encode(thumb) if thumb else False,
                'has_thumbnail': bool(thumb),
            })

    def _sync_note_file(self):
        for doc in self:
            html = Markup('<!DOCTYPE html><html><head><meta charset="utf-8"/><title>%s</title></head>'
                          '<body>%s</body></html>') % (doc.name, doc.note_body or '')
            super(ArgoDocument, doc).write({'raw': str(html).encode(), 'mimetype': 'text/html'})

    def _explorer_data(self, is_manager=False):
        self.ensure_one()
        uid = self.env.uid
        return {
            'kind': 'file',
            'id': self.id,
            'attachment_id': self.ir_attachment_id.id,
            'name': self.name,
            'mimetype': self.mimetype,
            'file_type': self.file_type,
            'size': self.file_size,
            'original_size': self.original_size,
            'checksum': self.checksum,
            'has_thumbnail': self.has_thumbnail,
            'folder_id': self.folder_id.id,
            'path': self.folder_id.complete_name or '',
            'owner': self.create_uid.name,
            'write_date': fields.Datetime.to_string(self.write_date),
            'create_date': fields.Datetime.to_string(self.create_date),
            'trash_date': fields.Datetime.to_string(self.trash_date) if self.trash_date else False,
            'can_delete': self._can_level('full'),
            'can_edit': self._can_level('edit'),
            'text_editable': self._can_level('edit') and self.file_type in ('text', 'note') and (self.file_size or 0) <= TEXT_EDIT_MAX_BYTES,
        }

    def _explorer_copy_to(self, target):
        self.ensure_one()
        Folder = self.env['argo.document.folder']
        vals = {
            'name': Folder._unique_name(target, self.name, 'file'),
            'folder_id': target.id or False,
            'raw': self.raw,
            'mimetype': self.mimetype,
            'file_type': self.file_type,
            'original_size': self.original_size,
            'thumbnail': self.thumbnail,
            'has_thumbnail': self.has_thumbnail,
            'partner_id': self.partner_id.id,
            'lead_id': self.lead_id.id,
            'description': self.description,
        }
        if self.file_type == 'note':
            vals['note_body'] = self.note_body
        return self.create(vals)

    def _explorer_unlink_with_files(self):
        """Xóa vĩnh viễn: xóa tài liệu + file trong filestore."""
        attachments = self.sudo().ir_attachment_id
        self.unlink()
        attachments.exists().unlink()

    # ------------------------------------------------------------------
    # API cho Explorer
    # ------------------------------------------------------------------
    @api.model
    def explorer_new_file(self, folder_id, kind):
        if kind not in NEW_FILE_KINDS:
            raise UserError(_("Loại file không hợp lệ."))
        name, template, mimetype, file_type = NEW_FILE_KINDS[kind]
        folder = self.env['argo.document.folder']._get_folder(folder_id)
        data = b''
        if template:
            with file_open(f'argo_documents/{template}', 'rb') as f:
                data = f.read()
        vals = {
            'name': self.env['argo.document.folder']._unique_name(folder, name, 'file'),
            'folder_id': folder.id or False,
            'raw': data,
            'mimetype': mimetype,
            'file_type': file_type,
        }
        if kind == 'note':
            vals['note_body'] = Markup('<p><br></p>')
        doc = self.create(vals)
        if kind == 'note':
            doc._sync_note_file()
        return doc._explorer_data(self.env['argo.document.folder']._is_manager())

    def explorer_get_text(self):
        self.ensure_one()
        self._require_level('view')
        if self.file_type == 'note':
            return {'type': 'note', 'content': self.note_body or ''}
        if (self.file_size or 0) > TEXT_EDIT_MAX_BYTES:
            raise UserError(_("File quá lớn để sửa trực tiếp, hãy tải về để sửa."))
        raw = self.raw or b''
        for enc in ('utf-8-sig', 'utf-16', 'cp1258', 'latin-1'):
            try:
                return {'type': 'text', 'content': raw.decode(enc)}
            except UnicodeDecodeError:
                continue
        return {'type': 'text', 'content': raw.decode('utf-8', 'replace')}

    def explorer_save_text(self, content):
        self.ensure_one()
        self._require_level('edit')
        if self.file_type == 'note':
            self.write({'note_body': content})
        else:
            data = (content or '').encode('utf-8')
            if len(data) > TEXT_EDIT_MAX_BYTES:
                raise UserError(_("Nội dung quá lớn (tối đa 2 MB)."))
            self.write({'raw': data, 'mimetype': self.mimetype or 'text/plain'})
        return self._explorer_data(self.env['argo.document.folder']._is_manager())

    def action_regenerate_thumbnails(self):
        self._require_level('edit')
        self.filtered(lambda d: d.file_type == 'image')._generate_thumbnail()

    @api.model
    def action_compress_existing_images(self, limit=200):
        self.env['argo.document.folder']._check_manager()
        """Nén lại ảnh cũ đã upload trước khi có tính năng nén (chạy theo lô)."""
        cfg = self._get_config()
        docs = self.with_context(active_test=False).search(
            [('file_type', '=', 'image'), ('original_size', '=', 0)], limit=limit)
        saved = 0
        for doc in docs:
            data = doc.raw
            result = compress_image(data, doc.name, cfg['max_px'], cfg['quality']) if data else None
            if not result:
                doc.original_size = -1  # đánh dấu đã kiểm tra, không cần nén
                continue
            new_data, new_name, mimetype = result
            new_name = self.env['argo.document.folder']._unique_name(doc.folder_id, new_name, 'file', exclude=doc)
            saved += len(data) - len(new_data)
            doc.write({'raw': new_data, 'name': new_name, 'mimetype': mimetype, 'original_size': len(data)})
        return {'processed': len(docs), 'saved': saved,
                'remaining': self.with_context(active_test=False).search_count(
                    [('file_type', '=', 'image'), ('original_size', '=', 0)])}
