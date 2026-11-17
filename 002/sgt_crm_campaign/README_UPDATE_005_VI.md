CRM-002 V01 Update_005 — CẬP NHẬT NHẬN DIỆN SIDEBAR

Phạm vi vá UI:
- Thêm logo ĐẦY ĐỦ XY/新扬/® Xinyang trên chữ XINYANG, căn giữa và đặt trong luồng layout bình thường. Bỏ nhãn CRM-002 khỏi Sidebar chính.
- Ảnh logo được đóng gói ngay trong addon CRM-002, KHÔNG phụ thuộc UI-004.
- Điều chỉnh CSS riêng cho header logo và responsive khi Sidebar từ 236px còn 185px.
- KHÔNG sửa logic Deal, Stage, field, quyền, model, Kanban card, font chung Odoo hoặc MM Approval.

Upgrade trên Xinyang Demo2 từ Update_004:
1. Sao lưu database.
2. Thay thư mục `sgt_crm_campaign` cũ bằng thư mục từ ZIP Update_005 (không để hai bản cùng tên).
3. Restart Odoo; Apps > Update Apps List > SGT CRM-002 > Upgrade.
4. Làm mới trình duyệt Ctrl+Shift+R; mở CRM > Sales > Pipeline và bốn Data Funnel.
5. Kiểm tra logo đứng trên chữ XINYANG, không đè chữ hoặc menu, Sidebar cuộn được, 4 phễu/Data Funnel, SALESPERSON và quyền vẫn bình thường.

Chưa được kiểm thử runtime trực tiếp trên Odoo Demo2; cần nghiệm thu trước Production.
