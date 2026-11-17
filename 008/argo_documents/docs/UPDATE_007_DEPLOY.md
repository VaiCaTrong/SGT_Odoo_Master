# Deploy 008 Update_007

1. Backup database, ZIP 008 Update_006; chạy trên Staging trước.
2. Thay source, restart Odoo và Upgrade `argo_documents` (`19.0.1.7.0`).
3. Settings → Kho tài liệu → CRM Infor: chọn Folder ID của thư mục cha (cấp gốc), Save lại kể cả khi lựa chọn giữ nguyên.
   Thao tác này đặt CRM root Public/View, company_id=False; quyền của folder con không tự được mở.
4. Discuss → Documents: Admin chuột phải CRM Infor → Lock Folder. Kiểm tra có biểu tượng khóa và menu Unlock Folder chỉ dành Admin.
5. Tất cả user nội bộ (`base.group_user`) xem được CRM Infor qua Discuss/Documents; không cần gán Documents User. Quyền ở ngoài CRM Infor vẫn theo nhóm Documents như cũ.
6. Kiểm tra người dùng chỉ có quyền View tại CRM Infor KHÔNG thể upload trực tiếp vào root qua RPC; chỉ có quyền tạo folder con.
7. Kiểm tra Sales A: root Public/View, tạo con Private/Edit, upload; Sales B không thấy con; Admin thấy tất cả.
8. Kiểm tra Lock: Admin không thể trash/delete trực tiếp, qua tổ tiên, qua RPC, kể cả cron; có thể xem, đổi tên, upload file con.
9. Kiểm tra MST trùng hai Deal: nếu có quyền Edit thì link cùng folder; nếu không, thông báo cấp quyền, không tạo trùng.
10. Test legacy folders/rights; sau đó mới nâng cấp CRM-005 Update_042.

LƯU Ý: Chưa nghiệm thu Odoo thực tế. Base internal user chỉ được thấy CRM Infor và các folder con thực sự được chia sẻ/được tạo bởi họ; ngoài CRM không tăng quyền. Kiểm thử RPC, model ACL, Record Rules trên staging trước production.
