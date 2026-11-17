# Documents-008 Update_010 — Cập nhật ảnh Documents → CRM Image Gallery

Nền: Update_009 (19.0.1.9.0). Manifest: 19.0.1.10.0. Không thêm field/cột database, không có migration.

## Thay đổi
- Nút **Cập nhật ảnh lên CRM** (màu xanh) ở ngăn chi tiết bên phải:
  - chọn thư mục → mọi ảnh trực tiếp trong thư mục đó;
  - chọn 1 hoặc nhiều ảnh → chỉ các ảnh đang chọn (file không phải ảnh bị bỏ qua);
  - không chọn gì → mọi ảnh trong thư mục đang mở (hiện kèm số ảnh).
- Menu chuột phải (menu trắng) có mục **Cập nhật ảnh lên CRM** cho thư mục và cho ảnh đang chọn.
- Cây thư mục bên trái, nhánh CRM Information, có menu chuột phải riêng (trước đó hiện menu mặc định của Chrome): Mở, Tải xuống (.zip), Cập nhật ảnh lên CRM, Quyền xem…, Thuộc tính.
- Folder dùng chung nhiều Deal (cùng MST) → hộp chọn Deal. Folder chỉ gắn 1 Deal → cập nhật thẳng.
- Folder con của folder Deal dùng Deal của folder cha gần nhất.
- Hàm máy chủ mới: `explorer_crm_targets(folder_id)` (chỉ đọc) và `explorer_push_images_to_crm(folder_id, lead_id, document_ids=None)`. Việc ghi Gallery do **CRM-005 Update_064** (`crm.lead.crm005_push_documents_to_gallery`). 008 không phụ thuộc cứng vào 005: thiếu 005 thì các nút ẩn, và nếu gọi RPC trực tiếp sẽ báo lỗi rõ ràng.
- `explorer_config` trả thêm `crm_push_available`.

## Quyền
- Người bấm phải đọc được folder và file, đọc được Deal và có quyền **sửa Deal** (kiểm tra trên máy chủ, không `sudo`).
- Chỉ nhận file nằm trong cây folder đã gắn Deal; tối đa 200 ảnh mỗi lần (thừa thì chỉ lấy 200 ảnh đầu, có báo).

## Thứ tự nâng cấp
1. Backup DB. Thay addon `argo_documents` bằng Update_010, restart Odoo, Upgrade `argo_documents`.
2. Thay addon `sgt_crm_yellowpages_profile` bằng CRM-005 Update_064, Upgrade.
3. Ctrl+Shift+R. Mở Documents → CRM Information → folder của Deal có ảnh.

**Chỉ kiểm thử offline (giả lập ORM, Node, trình duyệt giả lập CSS). Chưa chạy trên Odoo 19 thật.**
