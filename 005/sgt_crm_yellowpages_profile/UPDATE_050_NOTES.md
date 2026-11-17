# CRM-005 Update_050 — Minimal inline Lat/Lon (11/11/2026)

- Nền: CRM-005 Update_049. Không kế thừa thay đổi không cần thiết của Update_048.
- Chỉ sửa giao diện tọa độ ngay bên dưới Address: **Lat [giá trị] · Lon [giá trị] · Get Coordinates** nằm trên cùng một hàng khi đủ rộng.
- Bỏ khung riêng, viền, nền xanh, padding lớn; thu ngắn các nhãn Latitude → Lat, Longitude → Lon; nút cỡ nhỏ.
- Mobile: tự xuống dòng khi thiếu chiều ngang; giữ chính xác 2 field, một nút, không có ghi chú/trạng thái hiển thị.
- Giữ `x_yp_geo_status` ẩn trong view; không sửa các model, cron, cơ chế tự động từ Extension hoặc thủ công.
- Manifest: `19.0.1.49.0`. ZIP `sgt_crm_yellowpages_profile_CRM-005_V01_Update_050.zip`.
- Cài đặt: backup, chép toàn bộ addon, restart toàn bộ Odoo workers, Upgrade CRM-005, Ctrl+Shift+R.
- Chỉ kiểm thử offline, cần nghiệm thu hiển thị desktop/mobile và hoạt động trên Odoo thật.
