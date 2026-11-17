UI-004 V02 — Update_005 | XINYANG Odoo 19 backend branding

Thay đổi duy nhất (theo yêu cầu người dùng 14/11/2026)
- Logo ở GÓC TRÊN PHẢI của thanh menu (cạnh avatar người dùng) đổi từ logo Xinyang
  sang LOGO HỢP TÁC Saigon Trade x Xinyang (hình tròn, nền trong suốt ở 4 góc).
- Ảnh mới: static/src/img/saigontrade_xinyang_logo.png (192 px). Ảnh cũ vẫn nằm trong thư mục, không còn dùng.
- XML: đổi src + alt của logo. SCSS: ô logo vẫn cao 39px (không đổi chiều cao navbar); ảnh 35x35 thay vì 34 rộng.
- Manifest 19.0.2.2.0 -> 19.0.2.3.0. Không đổi màu, viền đỏ 4px, menu, quyền hay dữ liệu.

Nâng cấp (không Uninstall)
1. Sao lưu database và thư mục addon đang hoạt động.
2. Thay thư mục sgt_xinyang_branding bằng bản này, khởi động lại Odoo.
3. Apps -> Update Apps List -> tìm UI-004 -> Upgrade.
4. Ctrl+Shift+R (nếu còn cache: thêm ?debug=assets vào địa chỉ).
5. Kiểm tra: góc trên phải hiện logo tròn Saigon Trade x Xinyang; chiều cao navbar và viền đỏ không đổi.

Lưu ý: kiểm tra mã nguồn và dựng CSS ngoại tuyến; chưa chạy Odoo thật.
