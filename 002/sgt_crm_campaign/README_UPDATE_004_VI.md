# CRM-002 V01 Update_004 — vá đúng lỗi help trên Kanban rỗng

## Khác biệt so với Update_003

- `models/service.py`: đổi giá trị `help` từ HTML literal `<p>...</p>` sang chuỗi văn bản thuần, do Kanban Update_003 in thẳng dấu `<p>`.
- `__manifest__.py`: version 19.0.1.2.0 → 19.0.1.3.0 để kích hoạt Upgrade.
- Không thay đổi model, field, view, asset, logic intake, phân quyền, Deal/Stage, CRM-001 hoặc MM Approval.

## Cài đặt

1. Sao lưu DB Demo 2.
2. Thay thư mục `sgt_crm_campaign` bằng thư mục trong ZIP này.
3. Khởi động lại Odoo.
4. Apps → Update Apps List → SGT CRM-002 → Upgrade.
5. Xóa cache web/Hard reload và mở một phễu chưa có Deal.

Nếu vẫn hiện `<p>` thì chụp tab Developer/Network và xác định có nhiều đường dẫn addon hoặc server chưa restart. Không uninstall module.
