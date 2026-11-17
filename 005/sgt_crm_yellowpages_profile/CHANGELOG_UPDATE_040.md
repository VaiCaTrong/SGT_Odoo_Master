# CRM-005 Update_040 — Sửa lỗi Owl khi mở Deal

## Bối cảnh
Sau CRM-005 Update_039, form Deal có thể báo `OwlError` tại `Field.template` với nguyên nhân `Cannot read properties of undefined (reading 'name')`.
Chưa có log `debug=assets` ở server, nên đây là bản khắc phục phòng ngừa nhắm vào field mới trong Update_039, không khẳng định đã tái hiện đúng lỗi trên Production.

## Thay đổi nhỏ, không đụng quyền Documents
- Không tạo/đọc field computed `x_yp_documents_panel` chỉ nhằm mount widget.
- Widget Documents giờ mount lên field chuẩn `crm.lead.name` bằng `<field name="name" widget="sgt_crm005_documents" readonly="1" nolabel="1"/>` tại đúng vị trí cũ. Widget chỉ dùng `record.resId` và API `argo.document.folder`, không sửa tên Deal.
- Giữ toàn bộ JS/CSS/XML UI và API Documents Update_039, mọi chức năng CRM-005 Update_038 và cơ chế bảo mật của Documents-008 Update_006.
- Field computed cũ không lưu DB (`store=False`); không xóa dữ liệu hình, Deal, folder/file.

## Thứ tự áp dụng
1. Sao lưu DB `xinyang` và phiên bản CRM-005 đang cài.
2. Giữ Documents-008 Update_006 hiện tại.
3. Cài mã CRM-005 Update_040 và Upgrade addon `sgt_crm_yellowpages_profile` (không chỉ chép file), restart Odoo.
4. Refresh assets bằng Ctrl+Shift+R hoặc trang `?debug=assets` để loại cache.
5. Kiểm tra một Deal cũ, một Deal mới, Documents box, Create folder và Upload, rồi kiểm tra Kanban, hình MM, Evidence.
6. Nếu lỗi vẫn tồn tại, gửi stack trace `?debug=assets`, view architecture của Deal và kết quả `fields_get` (chỉ tên/loại field, không xuất dữ liệu khách hàng).

Chưa có điều kiện để test trực tiếp trên Odoo Production trong môi trường đóng gói.
