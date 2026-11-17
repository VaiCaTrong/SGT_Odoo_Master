# CRM-005 V01 — Update_046: Tên công ty Kanban không chạy, tự xuống dòng

Nền: `sgt_crm_yellowpages_profile_CRM-005_V01_Update_045.zip`.
Manifest: `19.0.1.45.0`.

## Thay đổi có chủ đích

- Tên công ty trên thẻ Opportunity Kanban **không chạy ngang khi rê chuột**; bỏ class `sgt_marq` chỉ ở tên Kanban. Script `sgt_marquee.js` vẫn được giữ để hỗ trợ những trường form khác vốn đang sử dụng.
- Chữ tên công ty: **16px desktop, 15px mobile**, đậm 700; xuống dòng tự nhiên, kể cả với chuỗi dài không có khoảng trắng (`overflow-wrap: anywhere`).
- Logo **52 × 52px** trên desktop (**44 × 44px** trên mobile) tiếp tục ở BÊN TRÁI; tên nằm trong cột bên phải ở cùng một flex row và có thể cao hơn logo nếu tên dài.
- Không cắt dòng theo số dòng cố định; toàn bộ tên công ty hiển thị.

## Giữ nguyên

- Nút New và kéo Deal giữa các Stage của Update_045; không bật quick-create.
- Khoảng cách dọc 16px giữa các Deal từ Update_038.
- Giao diện/logo, mở Deal, Documents-008, đồng bộ ảnh Gallery, Evidence, ảnh MM, thông tin CRM và phân quyền.
- Không thay đổi trường dữ liệu, CSDL, API hay addon Documents-008.

## Nâng cấp và kiểm thử thực tế

1. Sao lưu DB / addon hiện có. Tốt nhất nâng cấp Staging trước.
2. Thay mã bằng Update_046, restart Odoo, `Upgrade` module `sgt_crm_yellowpages_profile` để cập nhật view/assets.
3. `Ctrl+Shift+R` để xóa cache assets. Vào CRM → Pipeline.
4. Xem tên ngắn, tên dài 2–4 dòng, tên không có dấu cách trên màn hình desktop và mobile: tên không chạy, logo vẫn bên trái.
5. Di chuột trên cả card để xác nhận tên không chạy; thử nút New và kéo thử một Deal; mở Deal để xác nhận Documents/Gallery không đổi.

Chỉ thử offline ở môi trường xây dựng; kết quả Production phải nghiệm thu sau khi Upgrade.
