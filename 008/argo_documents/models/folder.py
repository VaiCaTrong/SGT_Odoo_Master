import uuid
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .crm_folder_naming import folder_name_for_company, matches_company_tax_folder, normalize_company_tax

INVALID_NAME_CHARS = set('\\/:*?"<>|')


def check_item_name(name):
    name = (name or '').strip()
    if not name:
        raise UserError(_("Tên không được để trống."))
    if any(c in INVALID_NAME_CHARS for c in name):
        raise UserError(_('Tên không được chứa các ký tự: \\ / : * ? " < > |'))
    if len(name) > 255:
        raise UserError(_("Tên quá dài (tối đa 255 ký tự)."))
    return name


def sanitize_name(name, fallback='file'):
    """Thay ký tự không hợp lệ bằng '_' (dùng cho tên file/thư mục lấy từ máy người dùng)."""
    name = ''.join('_' if c in INVALID_NAME_CHARS or ord(c) < 32 else c for c in (name or '')).strip()
    return (name or fallback)[:255]


class ArgoDocumentFolder(models.Model):
    _name = 'argo.document.folder'
    _description = 'Thư mục tài liệu'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'name, id'

    name = fields.Char('Tên thư mục', required=True)
    complete_name = fields.Char('Đường dẫn', compute='_compute_complete_name', store=True, recursive=True)
    parent_id = fields.Many2one('argo.document.folder', 'Thư mục cha', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('argo.document.folder', 'parent_id', 'Thư mục con')
    child_count = fields.Integer('Số thư mục con', compute='_compute_counts')
    document_ids = fields.One2many('argo.document', 'folder_id', 'Tài liệu')
    document_count = fields.Integer('Số file', compute='_compute_counts')
    active = fields.Boolean(default=True)
    color = fields.Integer('Màu')
    description = fields.Text('Ghi chú')
    partner_id = fields.Many2one('res.partner', 'Khách hàng', index=True, ondelete='set null')
    lead_id = fields.Many2one('crm.lead', 'Deal / Dự án', index=True, ondelete='set null')
    # Update_007: một folder MST có thể gắn nhiều Deal mà không nhân đôi tài liệu.
    # lead_id cũ được giữ để không mất liên kết dữ liệu Update_006 trở về trước.
    crm_lead_ids = fields.Many2many(
        'crm.lead', 'argo_document_folder_crm_lead_rel', 'folder_id', 'lead_id',
        string='Các Deal cùng MST', copy=False)
    system_root = fields.Boolean('Thư mục hệ thống bất biến', default=False, copy=False, index=True,
                                 help='Root được tạo bởi addon; không thể đổi tên, di chuyển, đưa vào thùng rác hoặc xóa, kể cả Admin.')
    is_locked = fields.Boolean('Khóa chống xóa', default=False, copy=False, index=True,
                               help='Chỉ Documents Admin được bật/tắt. Không xóa folder đã khóa, kể cả qua thùng rác.')
    crm_shared_root = fields.Boolean('Thư mục gốc CRM Infor', default=False, copy=False, index=True,
                                     help='Được Admin chọn trong Settings. Public chỉ xem, cho phép tạo folder theo MST qua CRM-005.')
    crm_tree = fields.Boolean('Thuộc cây CRM Infor', compute='_compute_crm_tree',
                              store=True, recursive=True, index=True)

    company_id = fields.Many2one('res.company', 'Công ty sở hữu folder', index=True, ondelete='restrict',
                                 help='Folder mới gắn company; folder legacy có thể để trống để giữ dữ liệu cũ.')
    allowed_user_ids = fields.Many2many(
        'res.users', 'argo_document_folder_allowed_users_rel', 'folder_id', 'user_id',
        string='Chỉ những người này được xem',
        help="Cùng với Phòng ban được xem: nếu cả hai để trống = mọi người dùng nội bộ đều thấy "
             "(hoặc kế thừa giới hạn từ thư mục cha).")
    allowed_department_ids = fields.Many2many(
        'hr.department', 'argo_document_folder_allowed_dept_rel', 'folder_id', 'department_id',
        string='Phòng ban được xem',
        help="Nhân viên thuộc phòng ban này (đúng phòng được chọn, không tính phòng con) và có tài khoản "
             "Odoo sẽ thấy thư mục. Cộng với danh sách người dùng chọn riêng.")
    effective_user_ids = fields.Many2many(
        'res.users', 'argo_document_folder_effective_users_rel', 'folder_id', 'user_id',
        string='Người được xem (thực tế)', compute='_compute_effective_access', store=True, recursive=True)
    effective_restricted = fields.Boolean(
        'Có giới hạn xem (thực tế)', compute='_compute_effective_access', store=True, recursive=True, index=True,
        help="True khi thư mục (hoặc thư mục cha mà nó kế thừa) đã chọn người hoặc phòng ban. "
             "Tách riêng khỏi danh sách người để phòng ban chưa có nhân viên không làm thư mục mở cho mọi người.")
    # Update_003 — chính sách quyền theo thư mục. NULL/legacy giữ dữ liệu phiên bản cũ.
    access_mode = fields.Selection([
        ('legacy', 'Legacy (chưa chuyển quyền)'),
        ('private', 'Riêng tư'),
        ('restricted', 'Theo User / Phòng ban'),
        ('public', 'Public nội bộ'),
    ], string='Chế độ chia sẻ', default='legacy', index=True, required=True)
    public_level = fields.Selection([
        ('view', 'Chỉ xem'), ('edit', 'Được sửa'), ('full', 'Toàn quyền')],
        string='Quyền Public', default='view', required=True)
    # allowed_* có từ Update_002: cấp View mặc định; nhóm edit/full là tập con.
    editable_user_ids = fields.Many2many(
        'res.users', 'argo_folder_edit_user_rel', 'folder_id', 'user_id', string='User được sửa')
    full_user_ids = fields.Many2many(
        'res.users', 'argo_folder_full_user_rel', 'folder_id', 'user_id', string='User toàn quyền')
    editable_department_ids = fields.Many2many(
        'hr.department', 'argo_folder_edit_dept_rel', 'folder_id', 'department_id', string='Phòng ban được sửa')
    full_department_ids = fields.Many2many(
        'hr.department', 'argo_folder_full_dept_rel', 'folder_id', 'department_id', string='Phòng ban toàn quyền')
    effective_edit_user_ids = fields.Many2many(
        'res.users', 'argo_folder_effective_edit_user_rel', 'folder_id', 'user_id',
        compute='_compute_effective_access', store=True, recursive=True, string='User có quyền sửa')
    effective_full_user_ids = fields.Many2many(
        'res.users', 'argo_folder_effective_full_user_rel', 'folder_id', 'user_id',
        compute='_compute_effective_access', store=True, recursive=True, string='User có toàn quyền')
    effective_read_public = fields.Boolean(compute='_compute_effective_access', store=True, recursive=True, index=True)
    effective_edit_public = fields.Boolean(compute='_compute_effective_access', store=True, recursive=True, index=True)
    effective_full_public = fields.Boolean(compute='_compute_effective_access', store=True, recursive=True, index=True)
    # Thùng rác
    trash_date = fields.Datetime('Ngày xóa', readonly=True, index=True)
    trash_root = fields.Boolean('Được chọn xóa', readonly=True)
    trash_batch = fields.Char(readonly=True, index=True)
    trash_uid = fields.Many2one('res.users', 'Người xóa', readonly=True)

    @api.depends('parent_id.crm_shared_root', 'parent_id.crm_tree')
    def _compute_crm_tree(self):
        for folder in self:
            folder.crm_tree = bool(folder.parent_id and
                                   (folder.parent_id.crm_shared_root or folder.parent_id.crm_tree))

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = f"{folder.parent_id.complete_name} / {folder.name}"
            else:
                folder.complete_name = folder.name

    @api.depends(
        'access_mode', 'public_level', 'create_uid',
        'allowed_user_ids', 'editable_user_ids', 'full_user_ids',
        'allowed_department_ids.member_ids.user_id', 'allowed_department_ids.member_ids.active',
        'editable_department_ids.member_ids.user_id', 'editable_department_ids.member_ids.active',
        'full_department_ids.member_ids.user_id', 'full_department_ids.member_ids.active',
        'parent_id.effective_user_ids', 'parent_id.effective_edit_user_ids',
        'parent_id.effective_full_user_ids', 'parent_id.effective_read_public',
        'parent_id.effective_edit_public', 'parent_id.effective_full_public', 'parent_id.crm_shared_root',
    )
    def _compute_effective_access(self):
        """Tập quyền đã giao cắt với giới hạn của folder cha; Admin đi qua group riêng.

        Quyền 'public' chỉ áp dụng cho Documents User nội bộ (ACL). Folder cũ
        (legacy) giữ cách xem kế thừa từ Update_002, nhưng xóa bị giới hạn.
        """
        levels = {'view': 1, 'edit': 2, 'full': 3}
        for folder in self:
            mode = folder.access_mode or 'legacy'
            read_users = set(folder.allowed_user_ids.ids)
            edit_users = set(folder.editable_user_ids.ids)
            full_users = set(folder.full_user_ids.ids)
            dept_read = folder.allowed_department_ids.sudo().member_ids.filtered('active').user_id.ids
            dept_edit = folder.editable_department_ids.sudo().member_ids.filtered('active').user_id.ids
            dept_full = folder.full_department_ids.sudo().member_ids.filtered('active').user_id.ids
            read_users.update(dept_read)
            edit_users.update(dept_edit)
            full_users.update(dept_full)
            edit_users.update(full_users)
            read_users.update(edit_users)
            owner = folder.create_uid.id
            if mode in ('private', 'restricted', 'public') and owner:
                edit_users.add(owner)
                read_users.add(owner)
            public_level = levels.get(folder.public_level, 1) if mode == 'public' else 0
            parent = folder.parent_id
            if mode == 'legacy':
                # KHÔNG biến folder Legacy riêng thành Public khi Admin chọn CRM root.
                # Folder cũ nằm trực tiếp dưới CRM Infor mặc định vẫn riêng tư.
                if parent and parent.crm_shared_root and not (
                        folder.allowed_user_ids or folder.allowed_department_ids):
                    read_users = {owner} if owner else set()
                    edit_users = {owner} if owner else set()
                    full_users = set()
                    public_level = 0
                elif folder.allowed_user_ids or folder.allowed_department_ids:
                    edit_users = set(read_users)
                    public_level = 0
                elif parent:
                    read_users = set(parent.effective_user_ids.ids)
                    edit_users = set(parent.effective_edit_user_ids.ids)
                    full_users = set(parent.effective_full_user_ids.ids)
                    public_level = (3 if parent.effective_full_public else
                                    2 if parent.effective_edit_public else
                                    1 if parent.effective_read_public else 0)
                else:
                    public_level = 2
                if owner:
                    read_users.add(owner)
                    edit_users.add(owner)
            elif mode == 'private':
                read_users = {owner} if owner else set()
                edit_users = {owner} if owner else set()
                full_users = set()
            elif mode == 'public':
                # Public vẫn có thể kèm cấp riêng user/department, tùy quyền cha.
                pass
            elif mode == 'restricted':
                public_level = 0
            else:
                # Giá trị lạ luôn từ chối thay vì coi là public.
                public_level, read_users, edit_users, full_users = 0, set(), set(), set()
            if parent and mode != 'legacy':
                pp = 3 if parent.effective_full_public else 2 if parent.effective_edit_public else 1 if parent.effective_read_public else 0
                pr = set(parent.effective_user_ids.ids)
                pe = set(parent.effective_edit_user_ids.ids)
                pf = set(parent.effective_full_user_ids.ids)
                # Quyền đối tượng bị chặn ở mức của folder cha, kể cả Public của folder con.
                def parent_level(uid):
                    base = max(pp, 3 if uid in pf else 2 if uid in pe else 1 if uid in pr else 0)
                    # CRM Infor là điểm điều hướng Public/View, KHÔNG phải giới hạn
                    # mức quyền của từng folder công ty độc lập bên trong. Root vẫn
                    # View; quyền cụ thể Edit/Full trên con do Admin chia sẻ riêng.
                    return 3 if parent.crm_shared_root else base
                local_users = read_users | edit_users | full_users | pr | pe | pf
                r2, e2, f2 = set(), set(), set()
                for uid in local_users:
                    local = max(public_level, 3 if uid in full_users else 2 if uid in edit_users else 1 if uid in read_users else 0)
                    granted = min(local, parent_level(uid))
                    if granted >= 1: r2.add(uid)
                    if granted >= 2: e2.add(uid)
                    if granted >= 3: f2.add(uid)
                read_users, edit_users, full_users = r2, e2, f2
                public_level = min(public_level, 3 if parent.crm_shared_root else pp)
            # Tránh user Public không có quyền nội bộ: ACL nhóm documents luôn là cổng chính.
            folder.effective_user_ids = [(6, 0, list(read_users))]
            folder.effective_edit_user_ids = [(6, 0, list(edit_users))]
            folder.effective_full_user_ids = [(6, 0, list(full_users))]
            folder.effective_read_public = public_level >= 1
            folder.effective_edit_public = public_level >= 2
            folder.effective_full_public = public_level >= 3
            folder.effective_restricted = public_level < 1

    def _can_level(self, level='view'):
        """Quyền trên server, không dựa vào flag điều khiển từ browser."""
        self.ensure_one()
        if self._is_manager() or self.env.is_system():
            return True
        folder = self.sudo()
        if not (self.env.user.has_group('argo_documents.group_argo_documents_user') or
                (self.env.user.has_group('base.group_user') and
                 (folder.crm_shared_root or folder.crm_tree))):
            return False
        if folder.company_id and folder.company_id.id not in self.env.companies.ids:
            return False
        if level == 'view':
            return folder.effective_read_public or self.env.uid in folder.effective_user_ids.ids
        if level == 'edit':
            return folder.effective_edit_public or self.env.uid in folder.effective_edit_user_ids.ids
        if level == 'full':
            return folder.effective_full_public or self.env.uid in folder.effective_full_user_ids.ids
        return False

    def _require_level(self, level='view'):
        for folder in self:
            if not folder._can_level(level):
                raise AccessError(_("Không có quyền %(level)s thư mục: %(name)s", level=level, name=folder.sudo().name))

    @api.model
    def _require_root_creator(self):
        if not (self._is_manager() or self.env.is_system() or
                self.env.user.has_group('argo_documents.group_argo_documents_root_creator')):
            raise AccessError(_("Chỉ Admin hoặc người được ủy quyền mới được tạo thư mục cấp gốc."))

    @api.model
    def _require_create_parent(self, parent):
        if not parent:
            self._require_root_creator()
        else:
            # CRM Infor Public View riêng, nhưng cho phép tài khoản Documents nội bộ
            # tạo folder con theo MST; không nâng quyền Edit lên chính CRM Infor.
            if (parent.crm_shared_root and parent.active and
                    parent.id == self._crm_root_folder().id and
                    (self._is_manager() or self.env.user.has_group('base.group_user'))):
                parent._require_level('view')
            else:
                parent._require_level('edit')

    def _require_unlocked_subtree(self):
        """Bất biến chống xóa, kể cả Admin/sudo/cron và xóa thư mục tổ tiên."""
        subtree = self.sudo().with_context(active_test=False)._all_descendants() if self else self
        if subtree and (subtree.filtered('is_locked') or subtree.filtered('system_root')):
            raise UserError(_('Thư mục đã Lock hoặc chứa thư mục Lock. Admin cần Unlock trước khi xóa.'))

    @api.model
    def explorer_toggle_folder_lock(self, folder_id, locked):
        """API riêng cho menu chuột phải; không cho client tự ghi trạng thái."""
        self._check_manager()
        folder = self.browse(int(folder_id)).exists()
        if not folder or not folder.active:
            raise UserError(_('Folder không tồn tại hoặc đang trong thùng rác.'))
        if not isinstance(locked, bool):
            raise UserError(_('Trạng thái Lock không hợp lệ.'))
        if folder.system_root:
            raise UserError(_('CRM Information là thư mục hệ thống, không được Unlock.'))
        if folder.is_locked != locked:
            folder.write({'is_locked': locked})
            folder._log_permission('lock_folder' if locked else 'unlock_folder',
                                   'folder_id=%s' % folder.id)
        return {'id': folder.id, 'is_locked': folder.is_locked}

    def _can_share(self):
        return (self._is_manager() or self.env.is_system() or
                (self.env.user.has_group('argo_documents.group_argo_documents_share_manager')
                 and self._can_level('full')))

    @api.model_create_multi
    def create(self, vals_list):
        protected = {'allowed_user_ids', 'allowed_department_ids', 'editable_user_ids',
                     'editable_department_ids', 'full_user_ids', 'full_department_ids',
                     'public_level', 'effective_user_ids', 'effective_restricted',
                     'effective_edit_user_ids', 'effective_full_user_ids',
                     'effective_read_public', 'effective_edit_public', 'effective_full_public',
                     'create_uid', 'is_locked', 'system_root', 'crm_shared_root', 'crm_tree', 'crm_lead_ids'}
        for vals in vals_list:
            parent = self._get_folder(vals.get('parent_id')) if vals.get('parent_id') else self.browse()
            if vals.get('lead_id'):
                self.env['crm.lead'].browse(int(vals['lead_id'])).check_access('read')
            self._require_create_parent(parent)
            if not (self._is_manager() or self.env.is_system()):
                if any(key in vals for key in protected) or vals.get('access_mode', 'private') != 'private':
                    raise AccessError(_("Folder mới của nhân viên phải ở chế độ Private. Admin mới được cấp quyền chia sẻ."))
            vals.setdefault('access_mode', 'private')
            vals.setdefault('company_id', parent.company_id.id if parent and parent.company_id else self.env.company.id)
            if parent and parent.company_id and vals['company_id'] != parent.company_id.id:
                raise AccessError(_('Thư mục con phải thuộc cùng công ty với thư mục cha.'))
            if not (self._is_manager() or self.env.is_system()) and vals['company_id'] not in self.env.companies.ids:
                raise AccessError(_('Không thể tạo folder ở công ty ngoài quyền truy cập.'))
        return super().create(vals_list)

    def write(self, vals):
        # Không thể phá bỏ root hệ thống kể cả bằng sudo, RPC hay lệnh dọn rác.
        immutable = {'name', 'parent_id', 'active', 'is_locked', 'system_root',
                     'crm_shared_root', 'company_id'}
        if self.filtered('system_root') and immutable.intersection(vals):
            raise UserError(_('Thư mục hệ thống được bảo vệ vĩnh viễn; không thể đổi tên, di chuyển, mở khóa hoặc xóa.'))
        if 'create_uid' in vals or 'create_date' in vals:
            raise AccessError(_('Không được sửa lịch sử người tạo hoặc ngày tạo folder.'))
        protected = {'is_locked', 'system_root', 'crm_shared_root', 'crm_tree', 'crm_lead_ids', 'access_mode', 'public_level', 'allowed_user_ids', 'allowed_department_ids',
                     'editable_user_ids', 'editable_department_ids', 'full_user_ids', 'full_department_ids',
                     'effective_user_ids', 'effective_restricted', 'effective_edit_user_ids',
                     'effective_full_user_ids', 'effective_read_public', 'effective_edit_public',
                     'effective_full_public', 'create_uid', 'create_date', 'parent_path',
                     'trash_uid', 'trash_date', 'trash_batch', 'trash_root', 'company_id'}
        if any(k in vals for k in protected) and not (self._is_manager() or self.env.is_system()):
            raise AccessError(_("Chỉ Admin được thay đổi chính sách phân quyền và dữ liệu quản trị folder."))
        if vals.get('is_locked') is not None and not (self._is_manager() or self.env.is_system()):
            raise AccessError(_('Chỉ Documents Admin được Lock/Unlock.'))
        if vals.get('active') is False:
            self._require_unlocked_subtree()
            self._require_level('full')
        else:
            self._require_level('edit')
        if vals.get('lead_id'):
            self.env['crm.lead'].browse(int(vals['lead_id'])).check_access('read')
        if 'parent_id' in vals and any(f.crm_shared_root for f in self):
            raise UserError(_('Không được di chuyển thư mục gốc CRM Infor đang được cấu hình.'))
        if any(f.crm_shared_root for f in self):
            if vals.get('access_mode', 'public') != 'public' or vals.get('public_level', 'view') != 'view':
                raise UserError(_('CRM Infor phải Public nội bộ với quyền chỉ xem.'))
            if 'company_id' in vals and vals['company_id']:
                raise UserError(_('CRM Infor phải có phạm vi công ty chung (company_id rỗng).'))
        if 'parent_id' in vals:
            target = self._get_folder(vals['parent_id']) if vals['parent_id'] else self.browse()
            self._require_create_parent(target)
            if target and target.company_id and any(f.company_id and f.company_id != target.company_id for f in self):
                raise AccessError(_('Không được di chuyển folder giữa hai công ty.'))
        share_keys = {'access_mode', 'public_level', 'allowed_user_ids', 'allowed_department_ids',
                      'editable_user_ids', 'editable_department_ids', 'full_user_ids', 'full_department_ids'}
        if set(vals).intersection(share_keys):
            before = {f.id: f._access_snapshot() for f in self}
        result = super().write(vals)
        if set(vals).intersection(share_keys):
            for folder in self:
                folder._log_permission('change_access', 'before=%s; after=%s' % (
                    before.get(folder.id), folder._access_snapshot()))
        return result

    def unlink(self):
        self._require_unlocked_subtree()
        self._require_level('full')
        # Chống xóa thư mục chứa dữ liệu không nằm trong quyền của người gọi.
        all_children = self.sudo()._all_descendants()
        if not (self._is_manager() or self.env.is_system()):
            for child in all_children:
                self.env['argo.document.folder'].browse(child.id)._require_level('full')
            docs = self.env['argo.document'].sudo().with_context(active_test=False).search([
                ('folder_id', 'in', all_children.ids)])
            for doc in docs:
                self.env['argo.document'].browse(doc.id)._require_level('full')
        return super().unlink()

    def _access_source(self):
        """Thư mục gần nhất (chính nó hoặc tổ tiên) đang tự chọn người/phòng ban; rỗng nếu không giới hạn."""
        folder = self.sudo()
        while folder:
            if folder.allowed_user_ids or folder.allowed_department_ids:
                return folder
            folder = folder.parent_id
        return self.sudo().browse()

    def _compute_counts(self):
        for folder in self:
            folder.child_count = len(folder.child_ids)
            folder.document_count = len(folder.document_ids)

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if self._has_cycle():
            raise ValidationError(_("Không thể chuyển thư mục vào chính nó hoặc thư mục con của nó."))

    @api.constrains('name')
    def _check_name(self):
        for folder in self:
            check_item_name(folder.name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_manager(self):
        return (self.env.user.has_group('argo_documents.group_argo_documents_manager') or
                self.env.user.has_group('base.group_system'))

    def _check_manager(self):
        if not self._is_manager() and not self.env.is_system():
            raise AccessError(_("Chỉ quản lý kho tài liệu mới thực hiện được thao tác này."))

    @api.model
    def _get_folder(self, folder_id):
        """Trả về recordset thư mục (rỗng = thư mục gốc) và kiểm tra quyền đọc."""
        if not folder_id:
            return self.browse()
        folder = self.browse(int(folder_id)).exists()
        if not folder:
            raise UserError(_("Thư mục không còn tồn tại (có thể đã bị xóa)."))
        folder.check_access('read')
        return folder

    @api.model
    def _unique_name(self, parent, name, kind='folder', exclude=None):
        """Tạo tên không trùng trong cùng thư mục: 'Tên (2)', 'Tên (3)'..."""
        Folder = self.with_context(active_test=True)
        Doc = self.env['argo.document'].with_context(active_test=True)
        if kind == 'folder':
            existing = {(f.name or '').lower() for f in Folder.search([('parent_id', '=', parent.id or False)])
                        if f != exclude}
            base, ext = name, ''
        else:
            existing = {(d.name or '').lower() for d in Doc.search([('folder_id', '=', parent.id or False)])
                        if d != exclude}
            dot = name.rfind('.')
            base, ext = (name[:dot], name[dot:]) if dot > 0 else (name, '')
        candidate, i = name, 2
        while candidate.lower() in existing:
            candidate = f"{base} ({i}){ext}"
            i += 1
        return candidate

    @api.model
    def _parse_items(self, items):
        folders = self.browse([int(i['id']) for i in items if i.get('kind') == 'folder'])
        docs = self.env['argo.document'].browse([int(i['id']) for i in items if i.get('kind') == 'file'])
        return folders.with_context(active_test=False), docs.with_context(active_test=False)

    def _all_descendants(self):
        """Toàn bộ thư mục con cháu (kể cả chính nó, kể cả trong thùng rác)."""
        if not self:
            return self
        domain = ['|'] * (len(self) - 1) + [('parent_path', '=like', f.parent_path + '%') for f in self]
        return self.with_context(active_test=False).search(domain)

    # ------------------------------------------------------------------
    # Hợp đồng kết nối CRM-005 (không thêm field vào crm.lead).
    # ------------------------------------------------------------------
    @api.model
    def _crm_root_folder(self):
        """System-owned CRM Information, not a user-entered ID/config parameter.

        Never silently fall back to the former CRM_Infor folder: it can contain
        records owned by other salespeople. This XML ID is stable across upgrades.
        """
        root = self.env.ref('argo_documents.folder_crm_information_root',
                            raise_if_not_found=False)
        if not root or not root.exists() or not root.active or root.parent_id:
            return self.browse()
        folder = self.browse(root.id)
        return folder if folder.has_access('read') else self.browse()

    @api.model
    def explorer_my_crm_folders(self):
        """Cây chọn vị trí trong CRM-005 chỉ gồm folder do chính user tạo."""
        root = self._crm_root_folder()
        if not root:
            return {'configured': False, 'root': False, 'folders': []}
        domain = [
            ('id', '!=', root.id),
            ('parent_path', '=like', root.parent_path + '%'),
        ]
        # The Deal picker lists own folders; Documents Admin may select every CRM folder.
        if not self._is_manager():
            domain.append(('create_uid', '=', self.env.uid))
        folders = self.search(domain, order='complete_name')
        return {'configured': True, 'root': {'id': root.id, 'name': root.name,
                                            'can_create': root._can_level('edit')},
                'folders': [{'id': f.id, 'name': f.name, 'path': f.complete_name,
                             'parent_id': f.parent_id.id, 'can_create': f._can_level('edit')}
                            for f in folders]}

    @api.model
    def explorer_deal_folder_info(self, lead_id):
        """Return a Deal's Documents folder and immediate files with current-user ACLs.

        No raw file bytes or elevated-privilege document records are returned.
        """
        if not (self._is_manager() or self.env.user.has_group('base.group_user')):
            raise AccessError(_('Chỉ tài khoản Odoo nội bộ được truy cập Documents.'))
        lead = self.env['crm.lead'].browse(int(lead_id)).exists()
        if not lead:
            raise UserError(_('Deal không còn tồn tại. Hãy lưu Deal trước khi mở Documents.'))
        lead.check_access('read')
        root = self._crm_root_folder()
        if not root:
            return {'configured': False, 'linked': False, 'folder': False,
                    'files': [], 'suggested_name': '', 'root_name': ''}
        tax = (lead['x_yp_tax_code'] if 'x_yp_tax_code' in lead._fields else False) or ''
        company_name = (lead.partner_name or '').strip()
        try:
            suggested = folder_name_for_company(company_name, tax) if company_name and tax else ''
        except ValueError:
            suggested = ''
        # Searching with sudo solely to detect an existing Deal link. Never expose data
        # until the user passes the ordinary folder read ACL + record rules.
        linked = self.sudo().with_context(active_test=False).search([
            '|', ('lead_id', '=', lead.id), ('crm_lead_ids', 'in', [lead.id])], limit=1)
        result = {'configured': True, 'linked': bool(linked), 'folder': False,
                  'files': [], 'suggested_name': str(suggested or '').strip(),
                  'root_name': root.name}
        if not linked:
            return result
        if not linked.active:
            result['reason'] = _('Folder liên kết đang nằm trong thùng rác. Liên hệ Admin để khôi phục.')
            return result
        legacy_location = not (linked.id == root.id or linked.parent_path.startswith(root.parent_path))
        # Folder liên kết trước Update_008 vẫn hiển thị và sử dụng theo quyền hiện có.
        # Không sao chép, di chuyển hoặc tiết lộ nếu thiếu quyền đọc.
        folder = self.browse(linked.id)
        if not folder.has_access('read') or not folder._can_level('view'):
            result['reason'] = _('Bạn không có quyền xem folder liên kết với Deal này.')
            return result
        docs = self.env['argo.document'].search([('folder_id', '=', folder.id)], order='name, id', limit=300)
        result['folder'] = {'id': folder.id, 'name': folder.name,
                            'path': folder.complete_name,
                            'can_upload': folder._can_level('edit'),
                            'can_delete': folder._can_level('full')}
        result['files'] = [{'id': doc.id, 'name': doc.name,
                            'attachment_id': doc.ir_attachment_id.id,
                            'file_type': doc.file_type,
                            'size': doc.file_size,
                            'can_edit': doc._can_level('edit'),
                            'can_delete': doc._can_level('full')}
                           for doc in docs]
        result['truncated'] = len(docs) >= 300
        if legacy_location:
            result['reason'] = _('Folder này được liên kết trước Update_008; vẫn giữ nguyên vị trí cũ.')
        return result

    @api.model
    def explorer_create_deal_folder(self, lead_id, parent_id=None, name=None):
        """Find-or-create exactly one folder per tax code under CRM Information.

        Both the manual CRM-005 button and the CRM-006 post-Create Contact
        hook use this method. Existing links are retained (including legacy
        folders outside CRM Information); never move, merge or rename them.
        New names are 'Company name - Tax code', with no database fields added.
        """
        if not (self._is_manager() or self.env.user.has_group('argo_documents.group_argo_documents_user')):
            raise AccessError(_('Tài khoản chưa có quyền Documents-008.'))
        root = self._crm_root_folder()
        if not root or not root.crm_shared_root or root.access_mode != 'public':
            raise UserError(_('Không tìm thấy CRM Information hệ thống. Admin cần Upgrade addon Documents-008.'))
        if parent_id and int(parent_id) != root.id:
            raise UserError(_('CRM-005 chỉ tạo folder trực tiếp trong CRM Information.'))
        lead = self.env['crm.lead'].browse(int(lead_id)).exists()
        if not lead:
            raise UserError(_('Không tìm thấy Deal. Hãy lưu Deal trước.'))
        lead.check_access('read')
        tax = normalize_company_tax(lead['x_yp_tax_code'] if 'x_yp_tax_code' in lead._fields else '')
        if not tax:
            raise UserError(_('Deal chưa có mã số thuế. Hãy nhập MST và lưu Deal trước.'))
        if not re.fullmatch(r'[0-9A-Z._-]{4,50}', tax):
            raise UserError(_('MST chứa ký tự không hợp lệ (chỉ dùng chữ, số, dấu chấm, gạch nối hoặc gạch dưới).'))
        company_name = (lead.partner_name or '').strip()
        if not company_name:
            raise UserError(_('Deal chưa có tên công ty. Hãy bổ sung Company Name trước khi tạo folder.'))
        desired_name = folder_name_for_company(company_name, tax)
        # The old CRM-005 client sent MST alone; accept it for compatibility.
        if name and str(name).strip().casefold() not in (tax.casefold(), desired_name.casefold()):
            raise UserError(_('Tên folder phải dựa trên tên công ty và MST của Deal.'))
        if lead.company_id and root.company_id and lead.company_id != root.company_id:
            raise AccessError(_('Deal và CRM Information thuộc công ty Odoo khác nhau.'))
        # Serialize all CRM root tax-folder operations, including linking.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (8008, root.id))
        old_link = self.sudo().with_context(active_test=False).search([
            '|', ('lead_id', '=', lead.id), ('crm_lead_ids', 'in', [lead.id])], limit=1)
        if old_link:
            if not old_link.active:
                raise UserError(_('Folder liên kết với Deal đang ở Thùng rác. Liên hệ Admin để khôi phục.'))
            if not self.browse(old_link.id)._can_level('view'):
                raise AccessError(_('Bạn chưa có quyền xem folder đã liên kết với Deal.'))
            return {'id': old_link.id, 'name': old_link.name, 'already_exists': True}

        # Search the current display convention AND legacy exact-tax folders.
        # Odoo's ilike is broad, so filter candidates using an exact suffix
        # match: tax 0123456789 must NOT reuse a folder for 00123456789.
        candidates = self.sudo().with_context(active_test=False).search([
            ('parent_id', '=', root.id), ('name', 'ilike', tax)])
        matches = candidates.filtered(lambda folder: matches_company_tax_folder(folder.name, tax))
        if len(matches) > 1:
            raise UserError(_('Có nhiều folder cùng MST trong CRM Information. Admin cần kiểm tra trước khi liên kết.'))
        if matches:
            folder = matches[0]
            if not folder.active:
                raise UserError(_('Folder MST đang nằm trong Thùng rác. Liên hệ Admin để khôi phục.'))
            if folder.company_id and lead.company_id and folder.company_id != lead.company_id:
                raise AccessError(_('MST đã có folder ở công ty Odoo khác. Admin cần xác minh.'))
            if not self.browse(folder.id)._can_level('edit'):
                raise AccessError(_('MST đã có folder riêng của người khác. Admin cần cấp quyền Edit để liên kết.'))
            self.browse(folder.id).check_access('read')
            folder.sudo().write({'crm_lead_ids': [(4, lead.id)]})
            folder._log_permission('link_deal_to_tax_folder', 'lead_id=%s' % lead.id)
            return {'id': folder.id, 'name': folder.name, 'already_exists': True}
        self._require_create_parent(root)
        created = self.create({'name': check_item_name(desired_name), 'parent_id': root.id, 'lead_id': lead.id})
        created.sudo().write({'crm_lead_ids': [(4, lead.id)]})
        return {'id': created.id, 'name': created.name, 'already_exists': False}

    # ------------------------------------------------------------------
    # Update_010 — đẩy ảnh trong folder Documents sang Image Gallery của Deal
    # ------------------------------------------------------------------
    PUSH_IMAGE_LIMIT = 200

    def _crm_link_folder(self):
        """Folder (chính nó hoặc tổ tiên gần nhất) đang gắn với Deal. Rỗng nếu không có.

        sudo chỉ để tìm liên kết; quyền đọc folder được kiểm tra bởi người gọi.
        """
        self.ensure_one()
        ids = [int(x) for x in (self.parent_path or '').split('/') if x] or [self.id]
        for folder_id in reversed(ids):
            folder = self.sudo().with_context(active_test=False).browse(folder_id)
            if folder.lead_id or folder.crm_lead_ids:
                return folder
        return self.sudo().browse()

    @api.model
    def explorer_crm_targets(self, folder_id):
        """Các Deal có thể nhận ảnh từ folder (kèm quyền của người gọi). Không đổi dữ liệu."""
        if not (self._is_manager() or self.env.user.has_group('base.group_user')):
            raise AccessError(_('Chỉ tài khoản Odoo nội bộ được truy cập Documents.'))
        if not folder_id:
            return {'folder_id': False, 'leads': []}
        folder = self._get_folder(folder_id)
        link = folder._crm_link_folder()
        leads = (link.lead_id | link.crm_lead_ids) if link else self.env['crm.lead'].browse()
        result = []
        for lead in leads.sudo().exists():
            visible = self.env['crm.lead'].browse(lead.id)
            if not visible.has_access('read'):
                continue
            result.append({
                'id': lead.id,
                'name': lead.partner_name or lead.name or ('#%s' % lead.id),
                'ref': '#%s' % lead.id,
                'stage': lead.stage_id.name or '',
                'can_write': bool(visible.has_access('write')),
            })
        return {'folder_id': folder.id, 'link_folder_id': link.id or False, 'leads': result}

    @api.model
    def explorer_push_images_to_crm(self, folder_id, lead_id, document_ids=None):
        """Thêm ảnh của folder Documents vào Image Gallery của một Deal.

        - document_ids rỗng/None: mọi ảnh đang nằm TRỰC TIẾP trong folder (tối đa PUSH_IMAGE_LIMIT).
        - Deal phải thật sự gắn với folder (hoặc tổ tiên gần nhất của nó) và người gọi phải có quyền
          đọc Deal, đọc folder và sửa Deal. Việc ghi Gallery do CRM-005 thực hiện (không sudo).
        Không có CRM-005 Update_064 → báo lỗi rõ ràng, không thay đổi dữ liệu.
        """
        if not (self._is_manager() or self.env.user.has_group('base.group_user')):
            raise AccessError(_('Chỉ tài khoản Odoo nội bộ được truy cập Documents.'))
        Lead = self.env['crm.lead']
        if not hasattr(Lead, 'crm005_push_documents_to_gallery'):
            raise UserError(_('CRM-005 (Update_064 trở lên) chưa được cài, không thể cập nhật ảnh lên CRM.'))
        try:
            lead_id = int(lead_id)
        except (TypeError, ValueError):
            raise UserError(_('Deal không hợp lệ.'))
        folder = self._get_folder(folder_id)
        if not folder:
            raise UserError(_('Hãy chọn một thư mục thuộc Deal.'))
        targets = self.explorer_crm_targets(folder.id)
        if lead_id not in [t['id'] for t in targets['leads']]:
            raise UserError(_('Thư mục này không gắn với Deal đã chọn, hoặc bạn không có quyền xem Deal.'))
        link = self.sudo().browse(targets['link_folder_id'])
        Doc = self.env['argo.document']
        if document_ids:
            if not isinstance(document_ids, (list, tuple)) or len(document_ids) > 2000:
                raise UserError(_('Danh sách file không hợp lệ.'))
            try:
                ids = list(dict.fromkeys(int(i) for i in document_ids))
            except (TypeError, ValueError):
                raise UserError(_('Danh sách file không hợp lệ.'))
            # browse() giữ nguyên thứ tự người dùng chọn
            docs = Doc.browse(ids).exists()
            docs.check_access('read')
            # chỉ nhận file nằm trong cây folder đã gắn Deal
            docs = docs.filtered(lambda d: d.folder_id and
                                 (d.folder_id.id == link.id or
                                  (d.folder_id.sudo().parent_path or '').startswith(link.parent_path or '\0')))
        else:
            docs = Doc.search([('folder_id', '=', folder.id), ('file_type', '=', 'image')],
                              order='name, id', limit=self.PUSH_IMAGE_LIMIT + 1)
        images = docs.filtered(lambda d: d.file_type == 'image')
        not_image = len(docs) - len(images)
        if not images:
            raise UserError(_('Không có ảnh nào để cập nhật lên CRM.'))
        truncated = len(images) > self.PUSH_IMAGE_LIMIT
        if truncated:
            images = images[:self.PUSH_IMAGE_LIMIT]
        result = Lead.browse(lead_id).crm005_push_documents_to_gallery(images.ids)
        result = dict(result or {})
        result.update({'not_image': not_image, 'truncated': truncated,
                       'limit': self.PUSH_IMAGE_LIMIT, 'lead_id': lead_id})
        return result

    # ------------------------------------------------------------------
    # API cho giao diện Explorer
    # ------------------------------------------------------------------
    @api.model
    def explorer_config(self):
        if not (self._is_manager() or self.env.user.has_group('base.group_user')):
            raise AccessError(_('Chỉ tài khoản Odoo nội bộ được truy cập Documents.'))
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'max_file_mb': int(ICP.get_param('argo_documents.max_file_mb', 25) or 25),
            'image_compress': ICP.get_param('argo_documents.image_mode', 'keep') == 'compress',
            'image_max_px': int(ICP.get_param('argo_documents.image_max_px', 1920) or 1920),
            'trash_days': int(ICP.get_param('argo_documents.trash_days', 0) or 0),
            'is_manager': self._is_manager(),
            'can_create_root': self._is_manager() or self.env.user.has_group('argo_documents.group_argo_documents_root_creator'),
            'uid': self.env.uid,
            'crm_root_folder_id': self._crm_root_folder().id or False,
            'note_view_id': self.env.ref('argo_documents.argo_document_view_form_note').id,
            # Update_010: nút "Cập nhật ảnh lên CRM" chỉ hiện khi CRM-005 (Update_064+) đã cài.
            'crm_push_available': hasattr(self.env['crm.lead'], 'crm005_push_documents_to_gallery'),
        }

    @api.model
    def explorer_tree(self):
        if not (self._is_manager() or self.env.user.has_group('base.group_user')):
            raise AccessError(_('Chỉ tài khoản Odoo nội bộ được truy cập Documents.'))
        folders = self.search_read([], ['name', 'parent_id', 'effective_restricted'], order='name, id')
        ids = {f['id'] for f in folders}
        return [{
            'id': f['id'],
            'name': f['name'],
            # thư mục cha không xem được -> hiện ở gốc
            'parent_id': f['parent_id'][0] if f['parent_id'] and f['parent_id'][0] in ids else False,
            'restricted': f['effective_restricted'],
        } for f in folders]

    @api.model
    def explorer_list(self, folder_id=False, search=None, trash=False):
        if not (self._is_manager() or self.env.user.has_group('base.group_user')):
            raise AccessError(_('Chỉ tài khoản Odoo nội bộ được truy cập Documents.'))
        Doc = self.env['argo.document']
        uid = self.env.uid
        if trash:
            folder = self.browse()
            fdomain = [('active', '=', False), '|', ('trash_root', '=', True), ('trash_batch', '=', False)]
            ddomain = [('active', '=', False), '|', ('trash_root', '=', True), ('trash_batch', '=', False)]
            if not self._is_manager():
                fdomain = [('trash_uid', 'in', [uid, False])] + fdomain
                ddomain = [('trash_uid', 'in', [uid, False])] + ddomain
            folders = self.with_context(active_test=False).search(fdomain, order='trash_date desc, name')
            docs = Doc.with_context(active_test=False).search(ddomain, order='trash_date desc, id desc')
        else:
            folder = self._get_folder(folder_id)
            if search:
                if folder:
                    fdomain = [('parent_path', '=like', folder.parent_path + '%'), ('id', '!=', folder.id)]
                    ddomain = [('folder_id.parent_path', '=like', folder.parent_path + '%')]
                else:
                    fdomain, ddomain = [], []
                fdomain = fdomain + [('name', 'ilike', search)]
                ddomain = ddomain + [('name', 'ilike', search)]
                folders = self.search(fdomain, limit=500)
                docs = Doc.search(ddomain, limit=2000)
            else:
                folders = self.search([('parent_id', '=', folder.id or False)])
                docs = Doc.search([('folder_id', '=', folder.id or False)])
                if not folder:
                    # thư mục được chia sẻ nhưng không thấy được thư mục cha -> hiện ở gốc
                    orphans = self.search([('parent_id', '!=', False)]).filtered(
                        lambda f: not f.parent_id.has_access('read'))
                    folders |= orphans

        # Hai 'ông cố' tách biệt trong Explorer: Company Information là root ảo,
        # CRM Information được pin ngang hàng, không phải thư mục con hiển thị ở Company.
        crm_root = self._crm_root_folder()
        if not trash and not folder and crm_root:
            # Company Information không hiển thị dữ liệu của root CRM độc lập,
            # kể cả khi người dùng tìm kiếm từ kho Company.
            folders = folders.filtered(
                lambda f: f.id != crm_root.id and not f.parent_path.startswith(crm_root.parent_path))
            if search:
                docs = docs.filtered(
                    lambda d: not d.folder_id or
                    not d.folder_id.parent_path.startswith(crm_root.parent_path))

        # Thống kê CHỈ các file/folder user được phép đọc (không đọc SQL bypass record rules).
        stats, child_counts = {}, {}
        if folders and not trash:
            for f in folders:
                readable_files = Doc.search([('folder_id.parent_path', '=like', f.parent_path + '%')])
                stats[f.id] = (len(readable_files), sum(readable_files.mapped('file_size')))
                child_counts[f.id] = self.search_count([('parent_id', '=', f.id)])

        is_manager = self._is_manager()
        res_folders = [{
            'kind': 'folder',
            'id': f.id,
            'name': f.name,
            'path': f.complete_name,
            'write_date': fields.Datetime.to_string(f.write_date),
            'create_date': fields.Datetime.to_string(f.create_date),
            'owner': f.create_uid.name,
            'file_count': stats.get(f.id, (0, 0))[0],
            'size': stats.get(f.id, (0, 0))[1],
            'child_count': child_counts.get(f.id, 0),
            'restricted': f.effective_restricted,
            'access_mode': f.access_mode or 'legacy',
            'company_id': f.company_id.id or False,
            'can_edit': f._can_level('edit'),
            'can_delete': f._can_level('full') and not bool(f.is_locked),
            'is_locked': bool(f.is_locked),
            'can_toggle_lock': bool(is_manager),
            'can_share': f._can_share(),
            'trash_date': fields.Datetime.to_string(f.trash_date) if f.trash_date else False,
            'color': f.color,
        } for f in folders]
        docs.fetch(['name', 'mimetype', 'file_size', 'checksum', 'file_type', 'original_size',
                    'has_thumbnail', 'folder_id', 'create_uid', 'write_date', 'create_date'])
        res_files = [d._explorer_data(is_manager) for d in docs]

        inherited = {'users': [], 'departments': []}
        if folder and not (folder.allowed_user_ids or folder.allowed_department_ids):
            source = folder._access_source()
            inherited = {
                'users': [{'id': u.id, 'name': u.name} for u in source.allowed_user_ids],
                'departments': [{'id': d.id, 'name': d.complete_name} for d in source.allowed_department_ids],
            }

        breadcrumb = []
        if folder:
            ancestors = self.browse([int(x) for x in folder.parent_path.split('/') if x])
            for a in ancestors:
                if a.has_access('read'):
                    breadcrumb.append({'id': a.id, 'name': a.name})
        return {
            'folder': {
                'id': folder.id or False,
                'name': folder.name if folder else _('Company Information'),
                'restricted': folder.effective_restricted if folder else False,
                'allowed_users': [{'id': u.id, 'name': u.name} for u in folder.allowed_user_ids] if folder else [],
                'allowed_departments': [{'id': d.id, 'name': d.complete_name}
                                        for d in folder.sudo().allowed_department_ids] if folder else [],
                'inherited_users': inherited['users'],
                'inherited_departments': inherited['departments'],
                'can_share': bool(folder) and folder._can_share(),
                'can_edit': folder._can_level('edit') if folder else bool(is_manager or self.env.user.has_group('argo_documents.group_argo_documents_root_creator')),
                'can_delete': folder._can_level('full') if folder else False,
                'can_create_folder': (folder._can_level('edit') or (folder.system_root and folder.crm_shared_root and folder._can_level('view'))) if folder else bool(is_manager or self.env.user.has_group('argo_documents.group_argo_documents_root_creator')),
                'can_upload_file': folder._can_level('edit') if folder else bool(is_manager),
            'is_locked': bool(folder.is_locked) if folder else False,
                'access_mode': (folder.access_mode or 'legacy') if folder else 'private',
                'company_id': folder.company_id.id if folder else self.env.company.id,
                'public_level': folder.public_level if folder else 'view',
                'user_grants': ([{'id': u.id, 'level': 'full' if u in folder.full_user_ids else 'edit' if u in folder.editable_user_ids else 'view'} for u in folder.allowed_user_ids] if folder else []),
                'department_grants': ([{'id': d.id, 'level': 'full' if d in folder.full_department_ids else 'edit' if d in folder.editable_department_ids else 'view'} for d in folder.sudo().allowed_department_ids] if folder else []),
            },
            'breadcrumb': breadcrumb,
            'folders': res_folders,
            'files': res_files,
            'search': bool(search),
            'trash': bool(trash),
        }

    @api.model
    def explorer_create_folder(self, parent_id, name=None):
        parent = self._get_folder(parent_id)
        name = check_item_name(name or _("Thư mục mới"))
        name = self._unique_name(parent, name, 'folder')
        folder = self.create({'name': name, 'parent_id': parent.id or False})
        return {'id': folder.id, 'name': folder.name}

    @api.model
    def explorer_ensure_paths(self, parent_id, paths):
        """Tạo cây thư mục khi upload cả thư mục: ['A', 'A/B', ...] -> {path: folder_id}."""
        parent = self._get_folder(parent_id)
        result = {}
        for path in sorted(set(paths or []), key=lambda p: p.count('/')):
            current = parent
            parts = [p for p in path.split('/') if p.strip()]
            for idx, part in enumerate(parts):
                key = '/'.join(parts[:idx + 1])
                if key in result:
                    current = self.browse(result[key])
                    continue
                part = sanitize_name(part, 'Thư mục')
                existing = self.search([('parent_id', '=', current.id or False), ('name', '=ilike', part)], limit=1)
                if existing:
                    existing._require_level('edit')
                current = existing or self.create({'name': part, 'parent_id': current.id or False})
                result[key] = current.id
        return result

    @api.model
    def explorer_rename(self, kind, rec_id, name):
        name = check_item_name(name)
        if kind == 'folder':
            rec = self.browse(int(rec_id))
            if self.search_count([('parent_id', '=', rec.parent_id.id or False), ('name', '=ilike', name),
                                  ('id', '!=', rec.id)]):
                raise UserError(_("Đã có thư mục tên \"%s\" ở đây.", name))
        else:
            rec = self.env['argo.document'].browse(int(rec_id))
            if self.env['argo.document'].search_count([('folder_id', '=', rec.folder_id.id or False),
                                                         ('name', '=ilike', name), ('id', '!=', rec.id)]):
                raise UserError(_("Đã có file tên \"%s\" ở đây.", name))
        rec.write({'name': name})
        return True

    @api.model
    def explorer_move(self, items, target_id):
        target = self._get_folder(target_id)
        folders, docs = self._parse_items(items)
        if target and target in folders._all_descendants():
            raise UserError(_("Không thể chuyển thư mục vào chính nó hoặc thư mục con của nó."))
        for folder in folders:
            if folder.parent_id == target:
                continue
            folder.write({'parent_id': target.id or False,
                          'name': self._unique_name(target, folder.name, 'folder', exclude=folder)})
        for doc in docs:
            if doc.folder_id == target:
                continue
            doc.write({'folder_id': target.id or False,
                       'name': self._unique_name(target, doc.name, 'file', exclude=doc)})
        return True

    @api.model
    def explorer_copy(self, items, target_id):
        target = self._get_folder(target_id)
        folders, docs = self._parse_items(items)
        if target and target in folders._all_descendants():
            raise UserError(_("Không thể sao chép thư mục vào chính nó."))
        for doc in docs:
            doc._explorer_copy_to(target)
        for folder in folders:
            folder._explorer_copy_tree(target)
        return True

    def _explorer_copy_tree(self, target):
        self.ensure_one()
        new = self.create({
            'name': self._unique_name(target, self.name, 'folder'),
            'parent_id': target.id or False,
            'description': self.description,
            'partner_id': self.partner_id.id,
            'lead_id': False,  # copy folder không được nhân đôi liên kết Deal/MST
            'color': self.color,
        })
        for doc in self.document_ids:
            doc._explorer_copy_to(new)
        for child in self.child_ids:
            child._explorer_copy_tree(new)
        return new

    @api.model
    def explorer_trash(self, items):
        folders, docs = self._parse_items(items)
        folders = folders.filtered('active')
        docs = docs.filtered('active')
        Doc = self.env['argo.document']
        # Full Access bắt buộc cho cả folders con và mọi file trong subtree.
        for root_folder in folders:
            root_folder._require_unlocked_subtree()
            descendants = root_folder.sudo()._all_descendants()
            for child in descendants:
                self.browse(child.id)._require_level('full')
            for doc in Doc.sudo().with_context(active_test=False).search([('folder_id', 'in', descendants.ids)]):
                Doc.browse(doc.id)._require_level('full')
        docs._require_level('full')
        for folder in folders:
            folder._log_permission('trash_folder', 'folder_id=%s' % folder.id)
        for doc in docs:
            if doc.folder_id:
                doc.folder_id._log_permission('trash_file', 'document_id=%s' % doc.id)
        now = fields.Datetime.now()
        batch = uuid.uuid4().hex
        vals = {'active': False, 'trash_date': now, 'trash_batch': batch, 'trash_uid': self.env.uid}
        for folder in folders:
            subtree = folder._all_descendants().filtered('active')
            inner_docs = Doc.search([('folder_id', 'in', subtree.ids)])
            inner_docs.sudo().write(dict(vals, trash_root=False))
            (subtree - folder).sudo().write(dict(vals, trash_root=False))
            folder.sudo().write(dict(vals, trash_root=True))
        docs.sudo().write(dict(vals, trash_root=True))
        return True

    @api.model
    def explorer_restore(self, items):
        folders, docs = self._parse_items(items)
        Doc = self.env['argo.document'].with_context(active_test=False)
        for rec in list(folders) + list(docs):
            if rec.active:
                continue
            if rec._name == self._name:
                self.browse(rec.id)._require_level('full')
            else:
                self.env['argo.document'].browse(rec.id)._require_level('full')
            if rec._name == self._name:
                rec._log_permission('restore_folder', 'folder_id=%s' % rec.id)
            elif rec.folder_id:
                rec.folder_id._log_permission('restore_file', 'document_id=%s' % rec.id)
            batch = rec.trash_batch
            parent_field = 'parent_id' if rec._name == self._name else 'folder_id'
            parent = rec[parent_field]
            dest_vals = {}
            if parent and not parent.active:
                dest_vals[parent_field] = False  # thư mục cha vẫn trong thùng rác -> khôi phục về gốc
                dest_parent = self.browse()
            else:
                dest_parent = parent
            if dest_vals:
                self._require_create_parent(dest_parent)
            reset = {'active': True, 'trash_date': False, 'trash_batch': False, 'trash_root': False,
                     'trash_uid': False}
            if rec._name == self._name and batch:
                subtree = rec.sudo()._all_descendants().filtered(lambda f: f.trash_batch == batch)
                inner = Doc.sudo().search([('folder_id', 'in', subtree.ids), ('trash_batch', '=', batch)])
                for child in subtree:
                    self.browse(child.id)._require_level('full')
                for child_doc in inner:
                    Doc.browse(child_doc.id)._require_level('full')
                (subtree - rec).sudo().write(reset)
                inner.sudo().write(reset)
            name_vals = {'name': self._unique_name(dest_parent, rec.name,
                                                   'folder' if rec._name == self._name else 'file', exclude=rec)}
            rec.sudo().write(dict(reset, **dest_vals, **name_vals))
        return True

    @api.model
    def explorer_delete_forever(self, items):
        folders, docs = self._parse_items(items)
        Doc = self.env['argo.document'].with_context(active_test=False)
        is_manager = self._is_manager()
        folders._require_unlocked_subtree()
        all_folders = folders.sudo()._all_descendants()
        all_docs = docs.sudo() | Doc.sudo().search([('folder_id', 'in', all_folders.ids)])
        for folder in all_folders:
            self.browse(folder.id)._require_level('full')
        for doc in all_docs:
            self.env['argo.document'].browse(doc.id)._require_level('full')
        for folder in folders:
            folder._log_permission('delete_forever_folder', 'folder_id=%s' % folder.id)
        for doc in docs:
            if doc.folder_id:
                doc.folder_id._log_permission('delete_forever_file', 'document_id=%s' % doc.id)
        all_docs._explorer_unlink_with_files()
        if all_folders:
            all_folders.sorted(lambda f: -len(f.parent_path)).unlink()
        return True

    @api.model
    def explorer_empty_trash(self):
        self._check_manager()
        domain = [('active', '=', False)]
        if not self._is_manager():
            domain.append(('trash_uid', '=', self.env.uid))
        Doc = self.env['argo.document'].with_context(active_test=False)
        docs = Doc.search(domain)
        folders = self.with_context(active_test=False).search(domain)
        items = [{'kind': 'file', 'id': i} for i in docs.ids] + [{'kind': 'folder', 'id': i} for i in folders.ids]
        return self.explorer_delete_forever(items)

    @api.model
    def explorer_set_access(self, folder_id, user_ids=None, department_ids=None,
                            mode=None, public_level='view', user_grants=None, department_grants=None):
        """Admin/ủy quyền chia sẻ: mỗi User/Phòng ban có View/Edit/Full.

        API cũ (chỉ danh sách IDs) vẫn nhận được để UI cũ không bị crash,
        nhưng quyền đổi vẫn phải được server cho phép.
        """
        folder = self._get_folder(folder_id)
        if not folder:
            raise UserError(_("Không cấp quyền ở thư mục gốc."))
        if not folder._can_share():
            raise AccessError(_("Chỉ Admin hoặc người được ủy quyền quản lý chia sẻ folder mới đổi được quyền."))
        mode = mode or ('restricted' if user_ids or department_ids else 'public')
        if mode not in ('private', 'restricted', 'public'):
            raise UserError(_("Chế độ chia sẻ không hợp lệ."))
        if public_level not in ('view', 'edit', 'full'):
            raise UserError(_("Cấp quyền Public không hợp lệ."))
        if mode == 'public' and public_level == 'full' and not self._is_manager():
            raise AccessError(_("Chỉ Admin được cấp quyền xóa công khai."))
        def parse_grants(grants, legacy_ids):
            if grants is None:
                grants = [{'id': x, 'level': 'view'} for x in (legacy_ids or [])]
            out = {}
            for g in grants:
                uid = int(g['id'])
                lvl = str(g.get('level', 'view'))
                if lvl not in ('view', 'edit', 'full'):
                    raise UserError(_("Mức quyền không hợp lệ."))
                if uid in out:
                    raise UserError(_("Không được cấp quyền trùng cùng đối tượng."))
                out[uid] = lvl
            if len(out) > 200:
                raise UserError(_("Giới hạn 200 người/phòng ban mỗi folder."))
            return out
        users = parse_grants(user_grants, user_ids) if mode == 'restricted' else {}
        depts = parse_grants(department_grants, department_ids) if mode == 'restricted' else {}
        if mode == 'restricted' and not (users or depts):
            raise UserError(_("Hãy chọn ít nhất một User hoặc Phòng ban, hoặc chọn Riêng tư."))
        if users:
            if set(users).intersection(self._documents_admin_user_ids()):
                raise UserError(_("Tài khoản Admin đã có toàn quyền, không cần cấp quyền trong Documents."))
            valid_users = set(self.env['res.users'].sudo().search([
                ('id', 'in', list(users)), ('share', '=', False), ('active', '=', True)]).ids)
            if set(users) != valid_users:
                raise UserError(_("Có User không tồn tại hoặc không phải tài khoản nội bộ đang hoạt động."))
        if depts:
            matched_departments = self._departments_domain_search([('id', 'in', list(depts))])
            _, hidden_depts = self._share_picker_department_counts(matched_departments)
            valid_depts = set(matched_departments.ids) - hidden_depts
            if set(depts) != valid_depts:
                raise UserError(_("Có phòng ban không hợp lệ, chỉ chứa Admin, hoặc ngoài công ty được phép."))
        if mode == 'public' and folder.parent_id:
            parent = folder.parent_id.sudo()
            parent_public_level = ('full' if parent.effective_full_public else
                                   'edit' if parent.effective_edit_public else
                                   'view' if parent.effective_read_public else None)
            rank_public = {'view': 1, 'edit': 2, 'full': 3, None: 0}
            if parent.crm_shared_root:
                parent_public_level = 'full'  # chỉ áp dụng cho quyền của folder CON
            if rank_public[parent_public_level] < rank_public[public_level]:
                raise UserError(_('Thư mục cha không cấp quyền Public đủ mức đã chọn. Hãy điều chỉnh cha trước.'))
        if mode == 'restricted' and folder.parent_id:
            parent = folder.parent_id.sudo()
            pp = 3 if parent.effective_full_public else 2 if parent.effective_edit_public else 1 if parent.effective_read_public else 0
            pr, pe, pf = set(parent.effective_user_ids.ids), set(parent.effective_edit_user_ids.ids), set(parent.effective_full_user_ids.ids)
            rank = {'view': 1, 'edit': 2, 'full': 3}
            def parent_cap(uid):
                if parent.crm_shared_root:
                    return 3  # quyền tại folder CON độc lập; CRM Infor vẫn Public/View
                return max(pp, 3 if uid in pf else 2 if uid in pe else 1 if uid in pr else 0)
            if any(parent_cap(uid) < rank[level] for uid, level in users.items()):
                raise UserError(_('Một số User chưa có đủ quyền ở thư mục cha.'))
            for dept_id, level in depts.items():
                employee_users = self.env['hr.department'].sudo().browse(dept_id).member_ids.filtered('active').user_id.ids
                if employee_users and any(parent_cap(uid) < rank[level] for uid in employee_users):
                    raise UserError(_('Phòng ban chưa có đủ quyền ở thư mục cha.'))
                if not employee_users and not parent.crm_shared_root and pp < rank[level]:
                    raise UserError(_('Phòng ban trống chưa thể được cấp quyền vượt giới hạn Public của thư mục cha.'))
        if users and folder.company_id:
            permitted = self.env['res.users'].sudo().search([
                ('id', 'in', list(users)), ('company_ids', 'in', [folder.company_id.id])]).ids
            if set(permitted) != set(users):
                raise UserError(_('Có User không thuộc công ty sở hữu folder.'))
        if not self._is_manager():
            # Người được ủy quyền không được cấp cho ai quyền vượt quá chính mình.
            max_level = 'full' if folder._can_level('full') else 'edit' if folder._can_level('edit') else 'view'
            rank = {'view': 1, 'edit': 2, 'full': 3}
            if any(rank[x] > rank[max_level] for x in list(users.values()) + list(depts.values())):
                raise AccessError(_("Bạn không thể cấp quyền cao hơn quyền hiện có."))
        def ids_at(grants, level):
            if level == 'edit': return [x for x, l in grants.items() if l in ('edit', 'full')]
            if level == 'full': return [x for x, l in grants.items() if l == 'full']
            return list(grants)
        values = {
            'access_mode': mode,
            'public_level': public_level if mode == 'public' else 'view',
            'allowed_user_ids': [(6, 0, ids_at(users, 'view'))],
            'editable_user_ids': [(6, 0, ids_at(users, 'edit'))],
            'full_user_ids': [(6, 0, ids_at(users, 'full'))],
            'allowed_department_ids': [(6, 0, ids_at(depts, 'view'))],
            'editable_department_ids': [(6, 0, ids_at(depts, 'edit'))],
            'full_department_ids': [(6, 0, ids_at(depts, 'full'))],
        }
        folder.sudo().write(values)
        return True

    def _access_snapshot(self):
        self.ensure_one()
        return {
            'mode': self.access_mode,
            'public_level': self.public_level,
            'users': [(u.id, 'full' if u in self.full_user_ids else
                       'edit' if u in self.editable_user_ids else 'view')
                      for u in self.allowed_user_ids],
            'departments': [(d.id, 'full' if d in self.full_department_ids else
                             'edit' if d in self.editable_department_ids else 'view')
                            for d in self.allowed_department_ids],
        }

    def _log_permission(self, action, detail):
        for folder in self:
            self.env['argo.document.permission.audit'].sudo().create({
                'folder_id': folder.id,
                'folder_ref_id': folder.id,
                'actor_id': self.env.uid,
                'action': action,
                'details': str(detail)[:3000],
            })

    @api.model
    def _documents_admin_user_ids(self):
        """Các Admin đã có Full Access mặc định, không phải đối tượng cần cấp quyền.

        Phân loại theo group thực tế (không dựa trên tên 'Administrator').
        Trùng với chính sách _is_manager: Documents Manager / Settings Admin.
        """
        User = self.env['res.users'].sudo()
        users = User.search([('share', '=', False), ('active', '=', True)])
        ids = {user.id for user in users if (
            user.has_group('argo_documents.group_argo_documents_manager') or
            user.has_group('base.group_system'))}
        # Odoo superuser cũng không cần xuất hiện trong danh sách cấp quyền.
        root = self.env.ref('base.user_root', raise_if_not_found=False)
        if root:
            ids.add(root.id)
        return ids

    @api.model
    def _departments_domain_search(self, domain=None):
        """Phòng ban thuộc các công ty người dùng đang làm việc (hoặc không gắn công ty)."""
        company_domain = ['|', ('company_id', '=', False), ('company_id', 'in', self.env.companies.ids)]
        # hr.department.complete_name là field không lưu (Odoo 19).
        return self.env['hr.department'].sudo().search((domain or []) + company_domain, order='name, id')

    @api.model
    def _share_picker_department_counts(self, departments=None):
        """Trả số User thường và ID phòng ban chỉ có tài khoản Admin.

        Không loại nhánh con chỉ vì đường dẫn có từ 'Administration'.
        Phòng ban chưa có user vẫn được hiển thị để Admin cấu hình trước.
        """
        departments = departments if departments is not None else self._departments_domain_search()
        admin_ids = self._documents_admin_user_ids()
        employees = self.env['hr.employee'].sudo().search([
            ('department_id', 'in', departments.ids), ('user_id', '!=', False), ('active', '=', True),
        ])
        user_ids = list(set(employees.mapped('user_id').ids))
        ordinary_users = set(self.env['res.users'].sudo().search([
            ('id', 'in', user_ids), ('active', '=', True), ('share', '=', False),
        ]).ids) - admin_ids
        counts, admin_only = {}, set()
        for emp in employees:
            dep_id, user_id = emp.department_id.id, emp.user_id.id
            if user_id in ordinary_users:
                counts.setdefault(dep_id, set()).add(user_id)
            elif user_id in admin_ids:
                admin_only.add(dep_id)
        hidden_dept_ids = {dep_id for dep_id in admin_only if not counts.get(dep_id)}
        return counts, hidden_dept_ids

    @api.model
    def explorer_departments(self):
        if not (self._is_manager() or self.env.user.has_group('argo_documents.group_argo_documents_share_manager')):
            raise AccessError(_('Chỉ người có quyền quản lý chia sẻ mới đọc danh sách phân quyền.'))
        departments = self._departments_domain_search()
        counts, hidden = self._share_picker_department_counts(departments)
        result = [{'id': d.id, 'name': d.complete_name or d.name or '',
                   'user_count': len(counts.get(d.id, ()))}
                  for d in departments if d.id not in hidden]
        return sorted(result, key=lambda item: (item['name'].casefold(), item['id']))

    @api.model
    def explorer_users(self):
        if not (self._is_manager() or self.env.user.has_group('argo_documents.group_argo_documents_share_manager')):
            raise AccessError(_('Chỉ người có quyền quản lý chia sẻ mới đọc danh sách phân quyền.'))
        admin_ids = self._documents_admin_user_ids()
        users = self.env['res.users'].sudo().search([
            ('share', '=', False), ('active', '=', True)], order='name')
        return [{'id': u.id, 'name': u.name} for u in users if u.id not in admin_ids]

    @api.model
    def explorer_storage(self):
        """Global storage inventory: manager-only until team-scoped reporting exists."""
        self._check_manager()
        self.env.cr.execute("""
            SELECT COUNT(d.id), COALESCE(SUM(a.file_size), 0), COALESCE(SUM(CASE WHEN d.original_size > 0 THEN d.original_size ELSE a.file_size END), 0),
                   COALESCE(SUM(a.file_size) FILTER (WHERE NOT d.active), 0)
              FROM argo_document d JOIN ir_attachment a ON a.id = d.ir_attachment_id
        """)
        count, size, original, trash = self.env.cr.fetchone()
        return {'count': count, 'size': size, 'original_size': original, 'trash_size': trash}

    # ------------------------------------------------------------------
    # Cron: dọn thùng rác
    # ------------------------------------------------------------------
    @api.model
    def _cron_purge_trash(self):
        days = int(self.env['ir.config_parameter'].sudo().get_param('argo_documents.trash_days', 0) or 0)
        if days <= 0:
            return
        limit = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        Doc = self.env['argo.document'].sudo().with_context(active_test=False)
        Folder = self.sudo().with_context(active_test=False)
        docs = Doc.search([('active', '=', False), ('trash_date', '!=', False), ('trash_date', '<', limit)])
        folders = Folder.search([('active', '=', False), ('trash_date', '!=', False), ('trash_date', '<', limit)])
        # Fail-closed: không purging một phần cây rồi mới gặp folder đã Lock.
        if folders and folders._all_descendants().filtered('is_locked'):
            return
        docs |= Doc.search([('folder_id', 'in', folders._all_descendants().ids)])
        docs._explorer_unlink_with_files()
        folders._all_descendants().sorted(lambda f: -len(f.parent_path)).unlink()
