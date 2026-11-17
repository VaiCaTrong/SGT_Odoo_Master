# CRM-005 Update_058 — Thu gọn Documents và đặt tên ảnh theo ghi chú Gallery

**Nền:** `sgt_crm_yellowpages_profile_CRM-005_V01_Update_057.zip`  
**Phiên bản manifest:** `19.0.1.57.0`  
**Phạm vi:** Chỉ addon CRM-005. Giữ nguyên CRM-006 Update_009 và Documents-008 Update_009.

## 1. Danh sách file/Documents mặc định thu gọn

- File list trong Documents widget nay ở trong `<details>` và **không đặt thuộc tính `open`**: khi mở Deal, mặc định danh sách đóng.
- Hiển thị một thanh `Danh sách tài liệu (N)`; nhấn thanh này để xem danh sách file hoặc thu lại.
- Khi mở danh sách, giới hạn chiều cao vùng list ở 420px và cho cuộn bên trong; không kéo dài cả Deal form.
- Giữ thanh thao tác Documents, upload/drag & drop, nút Đồng bộ ảnh Gallery, Làm mới và Open in Documents.
- Nếu có hơn 300 file, Documents-008 vẫn chỉ cấp tối đa 300 file như trước; dấu `+` báo danh sách có thể dài hơn và nhắc mở Documents để xem toàn bộ.

## 2. Gallery → Documents: lấy tên từ ghi chú bên dưới ảnh

- Trong `x_yp_gallery_html`, lấy từng ảnh `<img>` và `figcaption` nằm trong `<figure>` chứa chính ảnh đó.
- Chỉ dùng `figcaption` khi figure có đúng một ảnh, tránh gán chú thích chung cho nhiều ảnh.
- Dùng văn bản ghi chú làm phần tên file; đuôi file dựa trên **định dạng ảnh thực**, được kiểm chứng bởi PIL (không tin URL hoặc ghi chú).
- Giữ dấu tiếng Việt; loại ký tự cấm trong tên file (`\\ / : * ? " < > |`), ký tự ẩn và ký tự điều khiển; rút gọn khoảng trắng, giới hạn 100 ký tự cho phần tên.
- Nếu caption rỗng/không hợp lệ/không thể gắn đúng với ảnh, giữ tên `Image_Gallery_001.jpg` như trước.
- Khi tên file đã có, giữ phương thức `_unique_name(...,'file')` của Documents-008 để thêm hậu tố `(2)`, `(3)`... cho các nội dung khác nhau.
- **Không tạo ảnh trùng nội dung**: vẫn kiểm tra checksum theo folder và bỏ qua nếu ảnh đã lưu, bất kể tên cũ.
- **Không tự đổi tên tài liệu cũ**: ảnh đã đồng bộ dưới tên `Image_Gallery_...` vẫn giữ nguyên; tên theo caption áp dụng khi tạo file mới.
- Giữ nguyên batch 2 ảnh/RPC, tải ảnh an toàn SSRF, phân quyền đọc CRM/attachment, quyền Edit folder, và quyền tạo file Documents.

## 3. Không thay đổi

- Geolocation, Lat/Lon, chống mất tọa độ (Update_056), định vị tự động qua Extension, Copy / Google Maps (Update_057).
- Create Contact, Cập nhật Contact và đồng bộ CRM-006.
- Tự tạo folder theo Company + MST (Update_055) và Documents-008.
- Image Gallery gốc trên Deal; không xóa hoặc sửa trường `x_yp_gallery_html`.
- Logo, Kanban, upload thủ công, chỉnh sửa các file cũ, phân quyền Documents.
- Không thêm field database, cron, API endpoint hoặc dependency mới.

## 4. Kiểm tra đã thực hiện

- Offline unittest: 143 bài; 108 đạt, 35 bỏ qua (thiếu Odoo server hoặc fixture tương ứng), 0 thất bại.
- Thử HTML `figure/img/figcaption`, ảnh không caption, caption có thẻ inline, caption nhiều ảnh, tiếng Việt, ký tự cấm, tên dài, thiếu caption và quá giới hạn 500 ảnh.
- Xác minh XML parse, Python compile, ZIP CRC, asset path.
- Test trình duyệt Chromium mô phỏng: danh sách file mặc định đóng (37px), bấm mở và cuộn (468px tính cả header), bấm lại đóng; kiểm tra desktop 1200px và mobile 390px.
- **Chưa nghiệm thu trên Odoo Production**. Kiểm tra lại hành vi OWL và ACL trên môi trường Odoo thực tế trước khi nâng Production.

## 5. Hướng dẫn cập nhật / nghiệm thu

1. Backup database `xinyang` và thư mục addon CRM-005 hiện tại.
2. Thử trên staging: thay **toàn bộ** addon CRM-005 bằng Update_058; không Uninstall.
3. Restart Odoo, Upgrade `sgt_crm_yellowpages_profile`, hard refresh browser (`Ctrl + Shift + R`).
4. Mở Deal có folder chứa nhiều ảnh: file list phải đóng. Nhấn `Danh sách tài liệu (N)` để mở, bấm lần nữa để thu gọn.
5. Trên một Deal test có Gallery với 2 ảnh kèm hai `figcaption`, bấm `Đồng bộ ảnh Gallery`: file mới có tên theo caption, mở Documents tải file kiểm tra đúng ảnh.
6. Thử ảnh không caption → tên `Image_Gallery_###.ext`; caption trùng nhưng ảnh khác → hậu tố `(2)`; chạy sync lần 2 → không tạo bản sao theo checksum.
7. Kiểm tra nút upload manual, Open in Documents, quyền View/Edit, Get Coordinates, Copy, Google Maps, Create Contact và folder tự tạo.

**Phòng ngừa:** Không chạy lại đồng bộ số lượng lớn trước khi thử với một Deal test; file cũ không bị tự đổi tên.
