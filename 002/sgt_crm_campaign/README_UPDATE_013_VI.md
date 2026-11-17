# CRM-002 Update_013 (19.0.1.9.0) — Thanh nút chuyển giao diện cho phễu Data và Sale

## Yêu cầu (user 2026-10-27 11:08, duyệt 11:14)
Trang phễu không có 6 nút chuyển giao diện như CRM Pipeline chuẩn (Kanban, List, Calendar, Pivot, Graph, Activity). Match Making đã có đủ vì dùng Pipeline chuẩn của Odoo.

## Làm gì (chỉ Python, không JS, không field/model mới)
- Action của phễu **Data Funnel** và **Sale (New/Renew)** giờ khai báo đủ view: Kanban (thẻ riêng của phễu, giữ nguyên), List, Calendar, Pivot, Graph, Activity (view chuẩn CRM, cùng id mà Pipeline chuẩn dùng; thiếu id nào thì Odoo dùng view mặc định cùng loại), Form.
- Domain của phễu giữ nguyên nên mọi view chỉ tính Deal của phễu đó.
- Nhóm sẵn theo stage của chính phễu để cột khớp với Kanban: Data = `sgt_crm002_step` (3 cột), Sale = `sgt_crm002_sale_stage_id`. Dùng context `group_by` (List), `pivot_row_groupby` (Pivot), `graph_groupbys` (Graph). User vẫn đổi nhóm bằng ô Group By.
- Kéo thả Deal giữa các stage vẫn chỉ ở Kanban. Calendar và Activity không phụ thuộc stage.

## Không đổi
Match Making (Pipeline chuẩn + khóa quyền Update_012), menu, landing theo quyền, Kanban, handoff, dữ liệu.

## Test Demo 2
1. Vào Data Funnel: thấy 6 nút (Kanban, List, Calendar, Pivot, Graph, Activity).
2. List: nhóm sẵn Data / Verified / Potential, số Deal khớp Kanban. Pivot và Graph: hàng/trục là 3 stage đó.
3. Vào Sale New và Renew: List/Pivot/Graph nhóm theo stage Sale.
4. Calendar và Activity mở được, chỉ có Deal của phễu.
5. Match Making vẫn như cũ; user không có quyền Match Making vẫn không xem được dữ liệu MM.

## Giới hạn / chưa kiểm chứng ngoài Odoo thật
- Odoo 19 có nhận 3 khóa context nhóm sẵn không: nếu bỏ qua thì 5 nút vẫn hiện, chỉ mất nhóm sẵn (bấm Group By một lần).
- View chuẩn của CRM có thể hiện cột/đo lường theo stage CRM thường nếu user bỏ nhóm.
## Rollback
Cài lại Update_012 (không có thay đổi dữ liệu).
