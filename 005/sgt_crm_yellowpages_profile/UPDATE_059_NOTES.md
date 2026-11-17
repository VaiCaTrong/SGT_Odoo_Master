# CRM-005 Update_059 — Kanban Ctrl/Cmd/chuột giữa mở đúng Deal

Nguồn: CRM-005 Update_058 (19.0.1.57.0). Version mới: **19.0.1.58.0**.

## Lỗi được sửa

Odoo 19 KanbanCompiler gán `href="#"` cho `<a type="open">` không khai báo href.
Tab mở bằng Ctrl/Cmd hoặc chuột giữa vì vậy có thể không có đường dẫn chính xác đến `crm.lead`.

- `views/crm_yp_lead_kanban.xml`: giữ `type="open"` cho thao tác click thường;
  thêm `t-att-href="'/odoo/crm.lead/' + record.id.raw_value"`.
- `static/src/js/kanban_deal_new_tab.js`: chỉ xử lý click trong
  `.o_opportunity_kanban .o_kanban_record`, không patch toàn hệ thống.
  - Ctrl/Cmd+click tên/logo: sử dụng liên kết thật và hành vi tab mới của trình duyệt.
  - Ctrl/Cmd+click vùng trống thẻ: mở đúng Deal qua link của tên công ty.
  - Chuột giữa: tương tự.
  - Click thường trên tên/logo: vẫn do Odoo `type=open` xử lý.
  - Nút/hoạt động khác, menu, dropdown, link riêng: không can thiệp.

## Phạm vi an toàn

Không thêm/sửa model, field, dữ liệu, permissions, Python, cron, API; không thay đổi
`create=true`, `records_draggable=true`, CSS tên/logo, Geolocation Update_056,
Documents tự tạo folder Update_055, Gallery Update_058 hoặc đồng bộ CRM-006.

**Lưu ý kiểm thử**: kiểm thử Python/JS và trình duyệt mô phỏng không chứng minh Odoo
Production đã tải đúng asset. Trên staging xác nhận Ctrl+Click tại (1) logo,
(2) tên công ty, (3) thân thẻ; Cmd+Click trên macOS; chuột giữa;
click thường và kéo Deal giữa Stage. Khi mở tab mới, URL phải có đúng ID Deal
(`/odoo/crm.lead/<id>`); quyền đọc bản ghi áp dụng như Odoo gốc.

## Triển khai

1. Backup database và addon CRM-005 Update_058 đang chạy.
2. Thay trọn thư mục `sgt_crm_yellowpages_profile` bằng Update_059.
3. Restart workers/cron Odoo, Upgrade module từ Apps (không Uninstall).
4. Regenerate web assets nếu cần, Ctrl+Shift+R, nghiệm thu trên staging trước Production.
