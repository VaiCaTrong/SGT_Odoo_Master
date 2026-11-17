# CRM-005 Update_049 — Compact Geolocation UI (11/11/2026)

## Phạm vi
- Cơ sở trực tiếp: **Update_047 đã cài và hoạt động** sau khi restart Odoo. Không kế thừa phần refactor kỹ thuật Update_048 do user xác nhận không cần thiết.
- **Chỉ thay đổi giao diện** khối tọa độ trên CRM Deal.
- Hiển thị `Latitude`, `Longitude`, và nút **Get Coordinates** trên cùng một hàng ở desktop; tự xuống hàng khi màn hình nhỏ.
- Bỏ tiêu đề `Geolocation · CRM Deal`, dòng trạng thái bằng chữ, và toàn bộ ghi chú bên dưới.
- Giữ `x_yp_geo_status` trong form ở trạng thái invisible để đảm bảo thông tin nội bộ không bị mất, backend Cron/Geo và Extension không thay đổi.
- Không thay đổi model, cron, API, phương thức định vị, quyền và các chức năng khác của CRM-005.

## Phiên bản
- Tên ZIP: `sgt_crm_yellowpages_profile_CRM-005_V01_Update_049.zip`
- Manifest: `19.0.1.48.0` (tách khỏi bản Update_048 version `19.0.1.47.0`).
- Code nền: Update_047 (`19.0.1.46.0`).

## Triển khai
1. Sao lưu database và addon đang chạy (Update_047).
2. Thay toàn bộ thư mục addon bằng Update_049.
3. **Restart các process Odoo** để đồng bộ mã, sau đó Upgrade CRM-005 từ Apps.
4. Refresh browser, xác minh `Latitude`, `Longitude`, nút `Get Coordinates`; các dòng ghi chú/trạng thái/tiêu đề đã biến mất.
5. Thử thủ công trên Deal có địa chỉ và kiểm tra Extension / Cron tiếp tục hoạt động.

**Kiểm tra trong gói là offline, không thay thế nghiệm thu Odoo Production.**
