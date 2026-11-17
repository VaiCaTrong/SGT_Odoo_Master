# CRM-005 Update_047 — Lat/Lon trên Deal, tự động + thủ công

Bản nền: Update_046. Chỉ thêm `models/geo_lead.py`, helper, cron XML, trường hiển thị tại thẻ địa chỉ và CSS scoped. Không thay CRM-006, CRM-007, Contacts hay Documents-008.

## Cơ chế
- Khi Extension hoặc người dùng tạo/cập nhật `street`, `street2`, `city`, `state_id`, `zip`, `country_id` trên `crm.lead`, `create/write` **chỉ đặt trạng thái chờ**, không gọi API địa lý trong lúc lưu Deal.
- Cron `CRM-005: Định vị Deal chờ xử lý`: tối đa 5 Deal mỗi 5 phút, truy vấn `base.geocoder` chuẩn của `base_geolocalize` (cùng dịch vụ Odoo Contacts). Cấu hình provider/API và Internet do quản trị Odoo phụ trách. Không tạo `res.partner`.
- Nút `Lấy tọa độ`: truy vấn ngay, cần quyền Write Deal. Người dùng có thể sửa tọa độ trực tiếp; khi đã có tọa độ thủ công, địa chỉ thay đổi sẽ được đánh dấu cần kiểm tra và **không tự ghi đè**.
- Chỉ thử tự định vị địa chỉ có đường/phố kèm dữ liệu vùng, hoặc địa chỉ đầy đủ nhiều thành phần. Không giả lập vị trí cho địa chỉ thiếu dữ liệu; không fallback sang tâm thành phố. Tọa độ tự động là ước lượng, cần xác minh trước khi dùng trong Heat Map.
- Khi thay đổi địa chỉ và tọa độ cũ do tự động lấy, 005 sẽ xóa tọa độ cũ (về 0) và xếp hàng lại; nếu địa chỉ không thay đổi sẽ không gọi thêm API.
- Không xử lý hàng loạt các Deal đã tồn tại trong lúc Upgrade, tránh tạo tải API lớn. Để định vị Deal cũ, nhấn nút thủ công hoặc thay đổi địa chỉ; tính năng tự động áp dụng các lần nhập/cập nhật tiếp theo.
- Nếu provider thất bại hoặc không trả kết quả: đánh dấu failed, không lặp vô hạn; bấm `Lấy tọa độ` để thử lại.

## Điều kiện và kiểm thử Production
1. Backup DB + addon, nâng cấp trên staging; cập nhật từ bản Update_046, không uninstall.
2. Odoo 19 cài `base_geolocalize`; khi module CRM-005 Update_047 nâng cấp, phụ thuộc này được cài tự động nếu có trong addons path. Cấu hình địa lý trong General Settings và xác nhận provider hoạt động.
3. Tạo Deal qua Extension với địa chỉ đủ thông tin, lưu; quan sát `pending`; chạy cron/đợi scheduler, xác minh `estimated` và tọa độ hợp lệ.
4. Test chỉnh địa chỉ, viết lại giống cũ, nút thủ công, nhập tọa độ thủ công, đổi địa chỉ sau nhập tay, và provider thất bại.
5. Mở lại Kanban kiểm tra New/drag/drop, logo/tên, Evidence, Documents, Gallery. Đối chiếu Contacts và khẳng định không có Contact mới.
6. Không khẳng định định vị chính xác tuyệt đối, kiểm tra vị trí trên bản đồ trước khi sử dụng ra quyết định.

Không có môi trường Odoo kết nối để thực thi end-to-end. Những test offline chỉ kiểm tra mã và chức năng helper/contract.
