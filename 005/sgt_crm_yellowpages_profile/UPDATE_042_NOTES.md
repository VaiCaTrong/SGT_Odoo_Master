# Deploy CRM-005 Update_042

1. Backup database + addon CRM-005 Update_041.
2. Cài/Upgrade Documents-008 Update_007 và chọn/saved CRM Infor trong Settings trước.
3. Replace CRM-005 files → restart Odoo → Upgrade `sgt_crm_yellowpages_profile` `19.0.1.41.0`.
4. Ctrl+Shift+R, mở Deal, Documents nằm giữa Partners và Evidence.
5. Deal có MST đã lưu → Create Folder → upload catalog PDF/PNG/JPG → kiểm tra file trong Discuss/Documents theo Folder ID.
6. Deal thiếu MST → chỉ hiển thị cảnh báo; nhập MST và lưu Deal.
7. Kiểm tra Deal trùng MST, kiểm tra phân quyền 2 Sales, kiểm tra Owl widget không crash, Evidence và Kanban không đổi.
