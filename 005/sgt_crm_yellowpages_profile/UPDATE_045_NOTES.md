# CRM-005 V01 Update_045 — Khôi phục New và kéo-thả Deal

## Nguyên nhân
Từ Update_036, Kanban inherited view đặt `create=false` và `records_draggable=false` để chặn thao tác trực tiếp. Điều này đồng thời ẩn nút **New** và ngăn kéo các Deal giữa các Stage, kể cả đối với tài khoản có quyền tạo/sửa Lead.

## Phạm vi sửa từ Update_044
- `views/crm_yp_lead_kanban.xml`: `create=true` và `records_draggable=true`.
- Giữ `quick_create=false`: **New** mở form Deal đầy đủ; không tạo nhanh trong cột.
- Giữ `edit=false`, `delete=false`, `groups_draggable=false`, `group_create=false`, `group_edit=false`, `group_delete=false`: không bật chỉnh sửa/xóa trực tiếp hay kéo cả cột Stage.
- Giữ nguyên tất cả form, Documents-008, đồng bộ ảnh Gallery, Partners, Evidence, Image Gallery, CSS khoảng cách 16px, logo và marquee.
- `__manifest__.py`: `19.0.1.44.0`.
- Điều chỉnh ba bài test Kanban cũ có kỳ vọng `create=false/records_draggable=false` đã lỗi thời; thêm bài kiểm tra hồi quy Update_045.

## Triển khai
1. Sao lưu database `xinyang` và addon CRM-005 hiện hành.
2. Giữ nguyên Documents-008; thay addon CRM-005 bằng ZIP Update_045, restart dịch vụ và Upgrade `sgt_crm_yellowpages_profile` trên staging.
3. F5/Hard Refresh; vào CRM Pipeline: kiểm tra nút **New** mở form; lưu Lead mới.
4. Kéo Deal từ một Stage sang Stage khác, kiểm tra `stage_id` và log/chuông CRM-002 nếu có. Lưu ý các quy tắc server/record rules của CRM-002 vẫn có thể chặn chuyển Stage.
5. Xác nhận không kéo được cột Stage, không có quick-create, khoảng cách 16px và Documents box vẫn nguyên.

## Giới hạn kiểm thử
Đã kiểm thử offline XML/Python/cấu trúc gói. Chưa kiểm thử trực tiếp Odoo 19 Production và các quy tắc chuyển Stage tùy biến của CRM-002.
