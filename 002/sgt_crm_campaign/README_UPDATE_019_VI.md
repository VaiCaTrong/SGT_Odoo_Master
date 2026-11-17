# CRM-002 Update_019 (19.0.1.15.0) — sửa lỗi cài/nâng cấp Update_016–018

Lỗi production (xinyang.sge.vn, 2026-10-28 07:31, Upgrade module): `ParseError ... views/lead_age_bell.xml:8 ... Forbidden attribute used in arch (t-att-data-tooltip)`.
Nguyên nhân: Odoo 19 cấm thuộc tính `data-tooltip` (và `data-tooltip-template`, `data-tooltip-info`, cả dạng `t-att-` / `t-attf-`) trong MỌI arch của view. Bản 016–018 dùng chúng cho tooltip chuông / số ngày.
Sửa: trong `views/lead_age_bell.xml` mọi `data-tooltip` đổi thành `title` (`t-att-title` cho tooltip động trên thẻ Kanban). Tooltip của chuông trên thẻ Kanban và các nhãn tĩnh nay là tooltip trình duyệt (`title`), hiện sau khi rê chuột giữ yên một lúc. Chuông form và List vẫn là CSS tooltip. Template `static/src/xml/column_progress.xml` không phải view arch nên giữ `data-tooltip`.
Không đổi logic. Nếu Upgrade báo lỗi view khác, gửi lại nội dung lỗi: cùng nhóm (validator view Odoo 19).
Test: thêm `test_update019_no_forbidden_attribute_in_view_arch`; 9 file test xanh.
