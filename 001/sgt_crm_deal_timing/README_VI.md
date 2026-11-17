# CRM-001 — SGT CRM Deal Timing (Odoo Xinyang 19) — bản 19.0.2.1.0 (V03 giao diện)

## Thay đổi so với 19.0.2.0.0
- **Một dòng mỏng** trên đầu thẻ Kanban (Leads, Opportunities) và trong Form: bên trái `Stage: 5d` (xanh 0–3d, vàng 4–7d, đỏ từ 8d), bên phải **icon đồng hồ + tổng số ngày** `21d`. Chữ nhỏ, không viền, không xuống dòng.
- **Bỏ trạng thái “Đã dừng”**: Won, Lost (archive) và bàn giao sang phễu Sale **không còn dừng bộ đếm**. Stage đếm ngày như mọi Stage thường (cộng dồn khi quay lại Stage cũ); Won vẫn hiện `Stage: Nd` theo màu số ngày.
- Bàn giao sang Sale (CRM-002) là **cùng một Deal** nên **kế thừa nguyên bộ đếm**, không cần dữ liệu thêm.
- Tổng: số khoảng 24 giờ trọn vẹn từ `create_date` (như cũ).
- MM Approval (`mm_approval_mode=True`) vẫn không hiển thị và không truy vấn.
- Không sửa `create`, `write`, `action_set_won`, `action_set_lost`; không thêm field lưu, bảng hay cron.

## Giới hạn mới
- Deal Lost (archive) cũng tiếp tục tính ngày ở Stage đang đứng. Lịch sử `active` không còn được dùng.
- Chưa kiểm thử import/upgrade trên Odoo 19 thật.

## Nguồn dữ liệu

- Chuẩn Odoo: `crm.lead.create_date`, `stage_id`, `active`, `won_status`, `date_last_stage_update`, `date_closed`, `crm.stage.is_won`.
- Lịch sử thay đổi tiêu chuẩn `mail.tracking.value` / `mail.message` cho các field `stage_id`, `active`.
- Lấy số giây ở từng Stage bằng cách cộng các đoạn thời gian được lưu bởi Chatter, loại bỏ các đoạn Stage Won hoặc `active=False`. Tính lúc xem; không chạy cron.
- Không tạo bảng lịch sử mới, không ghi sửa trường CRM gốc, không sửa `create`, `write`, `action_set_won`, `action_set_lost` hay action MM.
- Module cung cấp bốn field giao diện tính toán không lưu: `sgt_crm001_visible`, `sgt_crm001_stage_text`, `sgt_crm001_total_text`, `sgt_crm001_stage_color`. Field `stage_color` chỉ dùng để chọn CSS, không lưu dữ liệu vào CRM.

## Giới hạn của bản Scan

Bản Scan ngày 11/10/2026 xác nhận metadata chứ KHÔNG chứa từng dòng tracking thực tế. Lịch sử cũ bị thiếu (do đồng bộ không qua ORM, bị xóa hoặc xóa tracking) **không thể được tái tạo một cách chính xác**. Khi không tìm thấy stage tracking, addon chỉ dùng `date_last_stage_update` để hạn chế cộng nhầm toàn bộ tuổi Deal vào Stage. Tương tự `date_closed` dùng làm fallback cuối cho Lost hiện tại khi thiếu event active.

Nếu Won/Lost thay đổi ngoài các thao tác Odoo thông thường mà không có lịch sử Stage/active, thời gian cũ không thể bảo đảm tuyệt đối. Việc đổi thuộc tính `crm.stage.is_won` hồi tố cũng làm thay đổi ý nghĩa lịch sử Stage đã tồn tại. Cần kiểm thử dữ liệu thực tế.

## Cài trên staging trước Production

1. Sao lưu database + filestore; chụp màn hình Leads/Opportunities/MM trước thử nghiệm.
2. Giải nén ZIP; đảm bảo thư mục `sgt_crm_deal_timing/` nằm ngay dưới custom addons path. Không tạo thư mục `addons/` lồng.
3. Cấp quyền đọc thư mục cho tiến trình Odoo, khởi động lại Odoo, Apps > Update Apps List.
4. Nếu V01 đã cài: tìm `SGT CRM-001 - Deal Stage & Total Age`, bấm **Upgrade**; nếu chưa cài: bấm **Activate** trên staging.
5. Kiểm tra Lead mới, Stage A->B->A, Won, Lost, mở lại Lost, Form, MM Approval và độ trễ Kanban.
6. Chỉ triển khai Production sau khi nghiệm thu staging. Không thể khẳng định tỷ lệ thành công >99% khi chưa thử trên môi trường tương ứng.

## Gỡ cài đặt

Uninstall module tại Apps; các view kế thừa và field tính toán sẽ được Odoo loại bỏ theo module. Không có bảng dữ liệu riêng cần xóa. KHÔNG gỡ addon khác.

## Kiểm thử đã thực hiện trong gói

- 13 trường hợp unittest cho thuật toán lịch sử Stage/active và ranh giới màu Stage: chạy qua Python chuẩn.
- Cú pháp Python, XML, `__manifest__.py`, kiểm tra XPath theo 3 view trong bản Scan.
- Chưa kiểm thử import/upgrade thực tế trong Odoo 19 trên máy chủ hay staging.

## Nâng cấp V01 → V02

1. Sao lưu database/filestore và thử trên staging.
2. **Giữ nguyên** tên thư mục kỹ thuật `sgt_crm_deal_timing`. Ghi đè thư mục V01 bằng thư mục V02 trong cùng addons path, **không** giải nén tạo hai bản module.
3. Restart Odoo và vào Apps → Update Apps List → tìm module → **Upgrade** (không Install bản thứ hai).
4. Refresh trình duyệt (Ctrl+Shift+R) để tải CSS mới; mở Kanban Leads, Opportunities và Form để kiểm tra Stage 0/3/4/7/8 ngày.
5. Đối chiếu rằng box Tổng giữ nguyên và MM Approval không có badge.

**Không thể cam kết xác suất cài đặt >99% khi chưa thực thi cài/upgrade trên staging Odoo Xinyang.**
