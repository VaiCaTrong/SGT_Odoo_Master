# CRM-002 Update_012 (19.0.1.8.0) — Chặn dữ liệu Match Making theo quyền, không dùng JS

## Luật
- Có quyền Match Making (hoặc Administrator): bấm CRM vào My Pipeline Match Making như cũ.
- Không có quyền Match Making: không xem được dữ liệu Match Making. Bấm CRM thì vào phễu đầu tiên được phân quyền (Data Funnel trước, rồi Sale). Không có phễu nào: màn hình trống kèm dòng "Bạn chưa được phân quyền phễu nào".

## Cách làm (chỉ Python/XML, không JS)
1. **Chuyển hướng đúng chỗ.** `crm.team.action_your_pipeline()` là hàm mà server action gốc "Crm: My Pipeline" gọi. Hàm này giờ gọi `sgt.crm002.service.landing_action()`. Mọi đường vào My Pipeline (menu CRM / Sales / My Pipeline, app CRM, menu Configuration) đều đi qua quyền phễu. Pipeline gốc của Odoo vẫn mở được qua `_sgt_crm002_native_pipeline()`.
2. **Khóa dữ liệu ở server.** Action pipeline gốc `crm.crm_lead_action_pipeline` mang thêm cờ context `sgt_crm002_mm_guard`. `crm.lead._search` thấy cờ này và user không có quyền Match Making thì trả về rỗng. Kanban, list, pivot, graph, lịch, đếm đều rỗng, dù user vào bằng menu, link hay tab cũ. Không có cờ thì không đổi gì.
3. `service._mm_allowed()` là điều kiện dùng chung: Administrator, hoặc có phễu `mm`/`is_main` trong danh sách phễu được phân quyền.

## Không đổi
Không thêm field, model, JS. Giữ nguyên Update_011 (server action landing, menu, view Kanban trống). Phễu Data/Sale không mang cờ nên không bị ảnh hưởng.

## Giới hạn
- Không dùng JS nên user không có quyền mở thẳng link Match Making chỉ thấy màn hình trống (vẫn hiện các cột Stage, không có thẻ), không tự nhảy sang phễu khác.
- Chỉ khóa pipeline Match Making (action `crm.crm_lead_action_pipeline`). Các menu khác (Leads, My Activities, Teams, Reporting, Forecast) vẫn theo quyền gốc của Odoo. Mở form của một Deal bằng ID trực tiếp cũng không bị chặn.
- Tài khoản chưa gắn Department trong Employee được xem là chưa có phễu nào.
- Nếu Odoo đổi context gốc của `crm.crm_lead_action_pipeline` ở bản cập nhật sau, cần cập nhật lại `views/landing.xml`.

## Test (Demo 2)
1. Admin bấm CRM: vào Match Making, thẻ hiện bình thường.
2. User có quyền Match Making: như trên.
3. User chỉ có quyền Inbound Pool: bấm CRM vào thẳng Inbound Pool.
4. Cùng user, bấm nút Match Making ở sidebar (nếu còn) hoặc mở link Match Making cũ: không có thẻ nào.
5. User chưa có phễu nào: màn hình trống, không nút New.
6. Menu Leads, Reporting vẫn mở bình thường.
