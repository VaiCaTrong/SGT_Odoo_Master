UI-004 V02 — Update_004 | XINYANG Odoo 19 backend branding

Phạm vi chính xác của bản vá (theo yêu cầu người dùng)
- Viền đỏ #E51922 dày chính xác 4px.
- Là MỘT đường liền mạch hết chiều ngang Navbar.
- Nằm SÁT MÉP DƯỚI cùng của Navbar màu xanh #0061BD; KHÔNG có dải xanh ở dưới.
- Không nâng viền lên / chừa khoảng hở phía dưới.
- Không làm thay đổi chiều cao của Navbar, menu, logo hay các chức năng.

Thay đổi so với Update_003
- SCSS: đổi ::after height 3px -> 4px, bottom 1px -> -2px. Giữ border-bottom
  trong suốt 2px để bảo tồn box model; bottom -2px bù đúng chiều dày border.
- Manifest version 19.0.2.1.0 -> 19.0.2.2.0.
- Thêm README Update_004. Không đụng tài nguyên khác.

Tuyệt đối không tác động CRM-001, CRM-002, công ty, quyền, dữ liệu, Website.

Nâng cấp trên Demo2 (không Uninstall)
1. Sao lưu database và thư mục addon đang hoạt động.
2. Thay thư mục sgt_xinyang_branding bằng bản này trong addons path.
3. Restart Odoo; Apps -> Update Apps List; chọn Upgrade UI-004.
4. Ctrl+Shift+R. Nếu asset còn cache, thử ?debug=assets.
5. Kiểm tra CRM / Discuss / Employees, logo công ty và click menu.

Lưu ý: bản này kiểm tra mã nguồn và dựng CSS ngoại tuyến; chưa chạy Odoo thật.
