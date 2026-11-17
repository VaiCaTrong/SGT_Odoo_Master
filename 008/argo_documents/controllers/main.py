import json
import logging

from odoo import _, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)
MAX_ZIP_BYTES = 500 * 1024 * 1024


class ArgoDocumentsController(http.Controller):

    @http.route('/argo_documents/upload', type='http', auth='user', methods=['POST'])
    def upload(self, ufile, folder_id=None, replace_id=None, compress='1', **kwargs):
        """Upload 1 file (gọi lần lượt từng file từ giao diện để có thanh tiến trình)."""
        Doc = request.env['argo.document']
        try:
            data = ufile.read()
            filename = ufile.filename or 'file'
            mimetype = ufile.content_type
            do_compress = compress not in ('0', 'false', 'False')
            folder_id = int(folder_id) if folder_id and folder_id not in ('false', 'null') else False
            if replace_id:
                doc = Doc.browse(int(replace_id)).exists()
                if not doc:
                    raise UserError(_("File cần thay không còn tồn tại."))
                doc.check_access('write')
                doc.argo_replace(data, filename, mimetype, do_compress)
            else:
                doc = Doc.argo_upload(folder_id, filename, data, mimetype, do_compress)
            is_manager = request.env['argo.document.folder']._is_manager()
            result = {'ok': True, 'file': doc._explorer_data(is_manager)}
        except (UserError, ValidationError, AccessError) as e:
            request.env.cr.rollback()
            result = {'ok': False, 'error': str(e.args[0] if e.args else e)}
        except Exception as e:  # noqa: BLE001
            request.env.cr.rollback()
            _logger.exception("Argo documents: upload lỗi")
            result = {'ok': False, 'error': _("Lỗi khi tải lên: %s", e)}
        return request.make_response(json.dumps(result), headers=[('Content-Type', 'application/json')])


    @http.route('/argo_documents/zip', type='http', auth='user', methods=['GET'])
    def download_zip(self, items='[]', name=None, **kwargs):
        """Tải nhiều file / cả thư mục về dưới dạng 1 file .zip (giữ cấu trúc thư mục)."""
        import tempfile
        import zipfile
        from werkzeug.wsgi import wrap_file

        Folder = request.env['argo.document.folder']
        Doc = request.env['argo.document']
        items = json.loads(items or '[]')
        folders, docs = Folder._parse_items(items)
        folders = folders.with_context(active_test=True).exists()
        docs = docs.with_context(active_test=True).exists()
        folders.check_access('read')
        docs.check_access('read')

        entries = []  # (path trong zip, doc)
        for doc in docs:
            entries.append((self._zip_name(doc), doc))

        def walk(folder, prefix):
            sub_prefix = f"{prefix}{folder.name}/"
            for doc in Doc.search([('folder_id', '=', folder.id)]):
                entries.append((sub_prefix + self._zip_name(doc), doc))
            for child in Folder.search([('parent_id', '=', folder.id)]):
                walk(child, sub_prefix)

        for folder in folders:
            walk(folder, '')

        total = sum(d.file_size or 0 for _p, d in entries)
        if total > MAX_ZIP_BYTES:
            return request.make_response(
                _("Tổng dung lượng %s MB vượt giới hạn tải ZIP (%s MB). Hãy chọn ít file hơn.",
                  total // 1024 // 1024, MAX_ZIP_BYTES // 1024 // 1024),
                headers=[('Content-Type', 'text/plain; charset=utf-8')], status=400)

        tmp = tempfile.TemporaryFile()
        used = set()
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path, doc in entries:
                unique, i = path, 2
                while unique.lower() in used:
                    base, dot, ext = path.rpartition('.')
                    unique = f"{base} ({i}).{ext}" if dot else f"{path} ({i})"
                    i += 1
                used.add(unique.lower())
                zf.writestr(unique, doc.sudo().raw or b'')
        size = tmp.tell()
        tmp.seek(0)
        if not name:
            name = folders[0].name if len(folders) == 1 and not docs else 'Kho-tai-lieu'
        filename = f"{name}.zip"
        headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Length', str(size)),
            ('Content-Disposition', http.content_disposition(filename)),
        ]
        return request.make_response(wrap_file(request.httprequest.environ, tmp), headers=headers)

    @staticmethod
    def _zip_name(doc):
        if doc.file_type == 'note' and not doc.name.lower().endswith('.html'):
            return f"{doc.name}.html"
        return doc.name
