# CRM-002 Update_011 (19.0.1.7.0) — Bấm CRM chỉ vào phễu được phân quyền

## Vấn đề
Bấm app CRM thì Odoo mở **CRM › Sales › My Pipeline**, chạy server action gốc "Crm: My Pipeline" và luôn rơi vào pipeline Match Making, kể cả người chưa được phân quyền Match Making.

## Cách sửa
Menu **My Pipeline** (`crm.menu_crm_opportunities`) chạy server action mới `CRM-002: CRM landing by funnel permission`, gọi `sgt.crm002.service.landing_action()`:
1. Administrator, hoặc người dùng có quyền Match Making: vào pipeline Match Making như cũ (`crm.team.action_your_pipeline()`).
2. Không có quyền Match Making: vào phễu đầu tiên được phân quyền, theo thứ tự Data Funnel, Sale, rồi thứ tự phễu trong Cài đặt.
3. Không có quyền phễu nào (hoặc tài khoản chưa gắn Department trong Employee): màn hình Kanban trống (domain `id = 0`, không cột, không nút tạo) kèm dòng "Bạn chưa được phân quyền phễu nào".

Sidebar vẫn chỉ hiện các phễu được phân quyền. Nút Match Making trên sidebar không đổi.

## Không đổi
Không thêm field, model, JS. Chỉ: hàm `landing_action` + `_no_access_action` (service.py), `views/landing.xml` (server action, ghi đè action của menu My Pipeline, view Kanban trống), `sales_team` thêm vào depends (đã là phụ thuộc của crm).

## Giới hạn
- Chỉ chỉnh chỗ "hạ cánh" khi bấm CRM / My Pipeline. Các menu khác (Leads, My Activities, Teams, Reporting, Forecast) vẫn theo quyền gốc của Odoo.
- Gỡ module không trả menu My Pipeline về action gốc (Odoo không tự khôi phục); nếu cần gỡ, đặt lại action của menu "My Pipeline" thành `Crm: My Pipeline`.

## Test (Demo 2)
1. Admin bấm CRM: vào Match Making.
2. User có quyền Match Making: vào Match Making.
3. User chỉ có quyền một phễu Data/Sale: vào thẳng phễu đó, sidebar chỉ hiện phễu được phép.
4. User chưa tick Department nào (hoặc không có Employee/Department): màn hình trống kèm thông báo, không có nút New.
5. Sidebar Permissions/Settings (admin) vẫn mở bình thường.
