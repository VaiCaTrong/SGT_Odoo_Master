UI-004 V02 — Update_003 | XINYANG Odoo 19 backend branding

Mục tiêu bản vá
- Viền đỏ thanh Navbar chạy thành MỘT ĐƯỜNG liên tục trên toàn bộ chiều ngang,
  không bị menu ứng dụng / menu con che mất đoạn.
- Dày hơn trước: 3px (từ 2px); nâng lên 1px so với mép dưới.
- Giữ nguyên chiều cao Navbar: giữ một border trong suốt 2px (box model như V02).
- Không cản click: pseudo-element ::after có pointer-events: none.

Phạm vi file thay đổi từ Update_002
- static/src/scss/branding.scss: chỉ chỉnh đường viền đỏ Navbar.
- __manifest__.py: nâng số version 19.0.2.0.0 -> 19.0.2.1.0.
- Bổ sung README này; không đổi logo, company switcher, màu xanh,
  font/Kanban, JS, Python, data model/ACL, CRM-001/002 hoặc Website.

Hướng dẫn nâng cấp Demo2 (không Uninstall)
1. Sao lưu DB Demo2 / code addon hiện tại.
2. Thay nguyên thư mục sgt_xinyang_branding bằng thư mục trong ZIP mới.
3. Khởi động lại Odoo -> Apps -> Update Apps List -> Upgrade module UI-004.
4. Ctrl+Shift+R; nếu asset vẫn cũ, dùng ?debug=assets và kiểm tra assets compile.
5. Thử CRM, Discuss, Employees và menu chuyển công ty.

Bản này chỉ được kiểm tra tĩnh/ZIP offline; chưa được chạy trên server Odoo.
