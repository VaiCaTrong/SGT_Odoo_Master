# CRM-005 Update_064 — Đưa ảnh Documents vào Image Gallery của Deal, ẩn box rỗng

Nền: Update_063 (19.0.1.62.0). Manifest: 19.0.1.63.0. Không thêm field/cột database, không migration.
Làm cặp với **Documents-008 Update_010** (cài 008 trước, rồi 005).

## Thay đổi
1. **Hàm máy chủ** `crm.lead.crm005_push_documents_to_gallery(document_ids)` (`models/gallery_push.py`, tiện ích thuần Python ở `models/gallery_push_utils.py`):
   - Giữ ảnh Gallery hiện có, **nối thêm** ảnh mới (không ghi đè).
   - Bỏ qua ảnh trùng nội dung (SHA1 so với ảnh đã có trong Gallery).
   - Chỉ nhận JPG/PNG/WebP, xác thực bằng Pillow, tự thu nhỏ ảnh lớn; mỗi lần tối đa 200 ảnh.
   - Ghi theo định dạng Gallery hiện tại: `<figure><img src="data:…;base64,…"><figcaption>tên file</figcaption></figure>` (đọc được bởi `gallery_entries` từ U058).
   - Cần quyền sửa Deal (kiểm tra bằng ACL/rule của người dùng, không sudo). Trả `{added, duplicate, skipped}`.
   - Xoá file trong Documents **không** xoá ảnh trong Gallery.
2. **Ẩn box rỗng** (CSS `:has()`): box Gallery và box Partners trống thì ẩn; box Documents (Create Folder, Evidence) luôn hiện. Có dữ liệu → hiện lại.
3. **Giảm khoảng trắng** giữa các box ở form Deal (cách 2 = thu gọn khoảng cách box).
4. **Nút xanh "Đưa ảnh lên Gallery"** trong box Documents của Deal (tuỳ chọn, gọi cùng hàm trên cho ảnh của folder Deal).

## Kiểm thử offline
- `tests/test_update064_documents_to_gallery.py`: 24 test (ORM giả lập + thật hàm bằng ast), mutation 0 survivor.
- Test cũ đã nâng assert version lên 19.0.1.63.0.
- 12 test kanban cũ fail y hệt trên U063 gốc (có từ trước, không do U064).
- Mô phỏng CSS bằng Playwright: box rỗng ẩn, box có dữ liệu hiện.

**Chưa chạy trên Odoo 19 thật.** Rủi ro chưa kiểm: sanitizer của field Html với `figure/figcaption/data:` URI; render OWL của nút mới.
