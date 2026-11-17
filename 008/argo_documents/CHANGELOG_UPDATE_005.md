# Documents-008 Update_005 — Admin toàn quyền & tích hợp CRM-005

- Documents Manager (`group_argo_documents_manager`) **hoặc** Odoo Settings Administrator (`base.group_system`) xem và quản trị toàn bộ folder/file không cần grant riêng.
- Bổ sung ACL + Record Rules cho base.group_system, cập nhật menu Discuss/Documents và phép thử `_is_manager()` phía backend.
- Giữ nguyên phân quyền View/Edit/Full cho người dùng thông thường; không thay đổi cách lưu folder/file, cũng không tự cấp Public.
- `explorer_my_crm_folders`: Admin chọn được tất cả folder dưới CRM Information; nhân viên chỉ chọn folder do mình tạo.
- `explorer_deal_folder_info(lead_id)`: API đọc folder và file theo Deal, kiểm tra quyền `crm.lead`, folder và tài liệu trước khi trả; file vẫn nằm trong `argo.document`/`ir.attachment`.
- API tạo folder theo Deal giữ nguyên, upload qua `/argo_documents/upload` (Odoo session + CSRF).
- Triển khai: **Update 008 trước, 005 sau**; cấu hình CRM Information trong Settings; root cần quyền Edit cho nhân viên được tạo folder con.
- Bảo mật: cần nghiệm thu trên Odoo 19 thực tế, đặc biệt người không có quyền, public/private, nhiều công ty, attachment URL, và phương thức RPC trực tiếp.
