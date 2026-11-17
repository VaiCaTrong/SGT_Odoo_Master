# CRM-005 Update_039 — Documents box liên kết 008

- Kế thừa Update_038, giữ nguyên logo Kanban, khoảng cách Kanban, Image Gallery, Evidence, ảnh Zalo Group Post và mọi field khác.
- Phụ thuộc `argo_documents` Update_005, không sao chép file hay tạo folder/file model mới.
- `x_yp_documents_panel`: computed Char **không lưu database**, chỉ là chỗ gắn custom Owl field widget ở trên ảnh MM/Zalo.
- Box Documents: đọc link folder của Deal theo `lead_id`, tạo folder bằng `explorer_create_deal_folder`, mặc định CRM Information, chọn thư mục cha qua `explorer_my_crm_folders` (sales chỉ thấy folder do mình tạo; Admin thấy tất cả), tên folder mặc định tên công ty.
- Upload qua endpoint chính thức `/argo_documents/upload` với phiên Odoo hiện tại + CSRF; kéo-thả file hoặc chọn file; danh sách file đọc theo quyền Documents 008, tải xuống bằng Odoo `/web/content`.
- 'Open in Documents' kích hoạt Client Action `argo_documents.explorer` với `context.active_id` là folder ID.
- Tài khoản chưa có quyền Documents sẽ được báo lỗi quyền, không rò dữ liệu. Folder cũ, file cũ giữ nguyên.
- BẮT BUỘC kiểm thử trên Staging trước Production: quyền admin, quyền sales, nhiều phòng ban, upload/xóa, thư mục chuyển quyền, trang mobile, cửa sổ Deal đã lưu/chưa lưu, browser cache/assets.

Cài đặt: xem `argo_documents/docs/UPDATE_005_DEPLOY.md` sau khi nâng cấp 008. Cần cấu hình root CRM Information; root phải cấp Edit cho người tạo folder.
