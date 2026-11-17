# CRM-005 V01 Update_044 — Đồng bộ Image Gallery sang Documents-008

**Nền:** CRM-005 Update_043; phụ thuộc Documents-008 Update_008. Không sửa mã 008.

## Thay đổi

- Box Documents (giữa Partners và Evidence) thêm nút **Đồng bộ ảnh Gallery** khi Deal đã có folder, tài khoản có quyền Edit.
- Nút đọc toàn bộ `<img>` từ `crm.lead.x_yp_gallery_html` theo thứ tự hiển thị, lưu các file ảnh vào folder Documents đang liên kết với Deal (folder MST do 008 quản lý).
- Sao chép, không xóa/sửa HTML gốc. Giữ quyền Create/Edit của Documents-008, không `sudo()` khi tạo file. Ghi `lead_id` lên `argo.document`, `create_uid` do Odoo tự gắn từ người thao tác.
- Tránh trùng theo SHA1 nội dung ảnh so với `ir.attachment.checksum` của tài liệu đã có trong folder, kể cả khi bấm lại hoặc hai Deal cùng MST có cùng ảnh.
- Đồng bộ theo lô 2 ảnh/RPC để hiển thị tiến độ và hạn chế request lâu. Kết quả báo đã lưu, có sẵn, thất bại kèm lý do tối đa 8 ảnh.
- Hỗ trợ ảnh Base64 inline, URL attachment Odoo `/web/image` hoặc `/web/content` có quyền đọc, và ảnh HTTP/HTTPS công khai. Với URL ngoài, kiểm tra DNS/IP public, ghim kết nối đến IP đã xác minh, kiểm tra TLS, không gửi cookie Odoo, không qua proxy, không theo redirect; giới hạn 12MB/ảnh, tối đa 500 ảnh/Deal/lượt. Ảnh nguồn yêu cầu máy chủ truy cập được; liên kết cần đăng nhập/403, redirect hoặc định dạng ảnh không hỗ trợ được báo thất bại, không làm mất ảnh đã đồng bộ.
- Không đồng bộ Partners hoặc Evidence; chỉ Image Gallery.

## Cài đặt

1. Backup database và CRM-005 Update_043; giữ Documents-008 Update_008.
2. Thay addon `sgt_crm_yellowpages_profile`, restart Odoo, Upgrade module `sgt_crm_yellowpages_profile`.
3. Hard-refresh assets; mở Deal có MST, tạo/link folder Documents nếu chưa có, xác nhận User có Edit.
4. Nhấn **Đồng bộ ảnh Gallery** trong Documents. Đợi hết tiến độ. Mở **Discuss → Documents** tại folder MST để so sánh số file.
5. Nhấn lần hai để kiểm tra kết quả file đã có không tăng, không phát sinh bản sao.

## Kiểm thử quyền / hồi quy

- View-only: không có nút; gọi RPC trực tiếp phải bị từ chối.
- Private Deal/folder: không được đọc/tải khi không có quyền.
- Bấm đồng bộ nhiều lần: file trùng nội dung bị bỏ qua; không xóa file tự tải thủ công, không xóa Image Gallery.
- Dùng ảnh có URL 403 hoặc tài nguyên lỗi: thống kê lỗi riêng, các ảnh khác vẫn đồng bộ.
- Ảnh rất lớn, SVG, HTML giả ảnh, mạng nội bộ/localhost: từ chối.
- Giữ các khu vực Gallery, Partners, Evidence, Image MM, Kanban và các API Documents cũ.

**Chưa thử trên server Odoo 19 thật:** các trường hợp CDN từ chối tải máy chủ, URLs ảnh có redirect, hoặc attachment có quy tắc truy cập riêng cần kiểm tra bằng Deal thực tế.
