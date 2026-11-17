# MASTER ODOO — CRM-005 Update_056 (P0 Geolocation data preservation)

**Cơ sở:** CRM-005 Update_055 (`19.0.1.54.0`); phát hành bản sửa mã `19.0.1.55.0`.

## Nguyên nhân đã xác minh trong mã nguồn

`models/geo_lead.py::write()` của bản Update_055 khi `street`, `street2`, `city`, `state_id`, `zip` hoặc `country_id` thay đổi và tọa độ trước đó thuộc nhóm `estimated`, **đã chủ động ghi cả `x_yp_latitude` và `x_yp_longitude` về `0.0`** trước khi xếp lịch định vị lại. Nếu Cron/geocoder thất bại, tọa độ cũ không còn. Người dùng xác nhận có hiện tượng hôm trước lấy được tọa độ, hôm sau quay lại bị mất; mã nguồn xác minh được **cơ chế có thể gây hiện tượng**, nhưng chưa có production write log để chỉ rõ thao tác thực tế trên từng Deal.

## Sửa chữa

1. **Không bao giờ xóa Lat/Lon đã lưu chỉ vì Address thay đổi.** Giữ cặp tọa độ cuối cùng, độ chính xác lần trước, thời điểm lấy và signature của địa chỉ lần trước.
2. Khi địa chỉ thay đổi thực sự: đặt `x_yp_geo_status = pending` (địa chỉ hợp lệ) hoặc `missing` (chưa đủ địa chỉ), không đổi tọa độ cũ. Cron tiếp tục thử lại như cũ. Chỉ khi geocoder trả cặp mới hợp lệ thì mới thay Lat/Lon, cập nhật precision/time/signature, `status=estimated`.
3. Nếu dịch vụ định vị thất bại: status `failed`, giữ tọa độ cuối cùng và signature cũ, không gán chúng là dữ liệu hợp lệ cho địa chỉ mới.
4. Giữ `manual`/`review` như bản trước: tọa độ nhập tay không bị Cron ghi đè.
5. Nếu Extension/Odoo gửi lại hai GPS field không thay đổi cùng địa chỉ cập nhật, không xem việc gửi lại là thao tác nhập tay; vẫn xếp lịch cập nhật nếu Address khác. Nếu Lat/Lon thực sự thay đổi do người dùng/nguồn import, xử lý như nhập tay.
6. Không thêm field, cột, API hoặc Cron mới. Không thay đổi XML/CSS, Documents/CRM Information, Kanban, nút Get Coordinates, chức năng CRM-006/007. Chỉ thay Python logic `write`, bản manifest, kiểm thử và tài liệu.

## Tính tương thích CRM-006 Update_009

CRM-006 đọc `x_yp_geo_status` và kiểm tra `x_yp_geo_address_key` trước khi sao chép sang `res.partner`. Trong khi `status=pending`, `missing` hoặc `failed`, cặp tọa độ giữ lại là **last-known / stale** và không được đồng bộ sang Contact. Sau Cron thành công, `status=estimated` và signature được cập nhật cho địa chỉ hiện tại; CRM-006 mới chấp nhận nguồn.

**Cảnh báo Dashboard/Heat Map:** Nếu ứng dụng chỉ đọc số `x_yp_latitude`, `x_yp_longitude` mà không kiểm tra trạng thái/signature, có thể hiển thị tọa độ cũ sau khi Address đổi. Chỉ coi tọa độ là hiện hành khi `x_yp_geo_status` là `estimated`/`manual` với signature phù hợp; `review`/`pending`/`failed` cần cảnh báo hoặc ẩn pin tùy nhu cầu.

## Hạn chế và phục hồi dữ liệu cũ

- Những Deal đã bị reset thành `(0, 0)` trước khi cài bản sửa **không tự khôi phục được bằng bản vá này**. Khôi phục từ bản sao lưu, lịch sử hoặc dữ liệu Contact nếu được xác minh đúng, hoặc nhấn Get Coordinates trên từng Deal để định vị lại.
- Kiểm thử offline và kiểm tra cú pháp **không thay thế** kiểm thử Cron, Extension và giao dịch ORM trên một bản sao database Xinyang Production.

## Nâng cấp

1. Sao lưu DB và addon trên Production; ưu tiên thử trên clone/staging.
2. Thay **toàn bộ** `sgt_crm_yellowpages_profile` bằng Update_056 trên nền Update_055.
3. Restart toàn bộ Odoo workers + Cron; Upgrade `sgt_crm_yellowpages_profile`. Không Uninstall.
4. Kiểm tra một Deal có tọa độ; dùng Extension cập nhật Street2/City; xác minh trước Cron số cũ vẫn còn nhưng status=pending; sau Cron thành công nhận GPS mới; khi provider lỗi thì số cũ vẫn còn nhưng status=failed.
5. Kiểm tra Create/Update Contact CRM-006 Update_009 không lấy tọa độ khi Deal đang pending/failed; Documents folder và Kanban không thay đổi.
