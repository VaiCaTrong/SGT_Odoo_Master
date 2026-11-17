UI-004 V02 / Update_002 — XINYANG Backend Branding (Odoo 19)

Nội dung:
- Đổi nền từng mục menu cấp cao và menu đang mở sang xanh Xinyang theo biến Navbar Odoo 19; xử lý hover/focus/active. Đóng gói SCSS chỉ trong web.assets_backend, KHÔNG tác động Website.
- Giữ logo đầy đủ Xinyang 新扬 ở công tắc công ty bên phải, không đổi tên công ty, không thay menu chuyển công ty.
- Không đổi font, kích thước Kanban, màu cảnh báo/CRM-001 hay quyền Odoo.

Nâng cấp từ V01:
1. Sao lưu Xinyang Demo2; thay đúng thư mục `sgt_xinyang_branding` trong addons path.
2. Khởi động lại Odoo; Apps > Update Apps List > XINYANG UI-004 > Upgrade.
3. Ctrl+Shift+R hoặc ?debug=assets. Kiểm tra CRM, Discuss, Employees, MM Approval.
4. Thanh menu cấp cao đồng nhất xanh, hover xanh sáng, mở menu xanh đậm; menu xổ xuống nền sáng.

Không Uninstall V01, không Install V02 như module mới. Chưa thử được Odoo runtime; cần nghiệm thu Demo2.
