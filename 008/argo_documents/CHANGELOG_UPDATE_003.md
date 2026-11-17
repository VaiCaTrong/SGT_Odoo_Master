# Update_003 — Documents permissions hardening

- Thêm chế độ `private/restricted/public/legacy` và quyền `view/edit/full` theo User và phòng ban.
- Quyền hiệu lực tại folder con bị giới hạn bởi quyền folder cha; người tạo Private có Edit, không tự xóa.
- Folder mới có `company_id`, folder cũ không auto gán company; giới hạn multi-company cho User.
- Kiểm soát ORM `create/write/unlink` của folder/document; tăng kiểm tra upload, delete, restore, move, ZIP, text editor.
- Nhóm độc lập: root creator và share manager; Admin/Manager tiếp tục quản trị chung.
- Explorer có UI cấp quyền theo từng User/phòng ban/Public và hiển thị chức năng theo quyền.
- Chuyển menu Documents vào Discuss ngay cạnh Technical, giữ action Explorer cũ; thêm log phân quyền trong Discuss/Technical.
- Folder legacy giữ dữ liệu và quyền xem/sửa cũ có kiểm soát, siết xóa; phải rà soát và chuyển chính sách thủ công.
- Thay truy vấn thống kê SQL xuyên các folder bằng ORM tôn trọng Record Rules.
- Chưa thử với server Odoo 19 thật: xem `docs/UPDATE_003_DEPLOY.md`.
