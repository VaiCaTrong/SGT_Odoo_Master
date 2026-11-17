# Upgrade Documents-008 Update_006

1. Sao lưu DB `xinyang` và addon `argo_documents` hiện hành (Update_005).
2. Thay addon bằng folder `argo_documents` trong ZIP Update_006. Khởi động lại dịch vụ Odoo, Upgrade `argo_documents` (manifest `19.0.1.6.0`).
3. Làm mới trình duyệt (Ctrl+Shift+R), vào Discuss → Documents → chuột phải folder → Phân quyền.
4. Kiểm tra **User** không còn Administrator/Docs Manager/Settings Admin. **Phòng ban** không còn phòng ban chỉ có Admin; các phòng ban có người thường vẫn có thể chọn, số người không đếm Admin.
5. Xác nhận Admin tiếp tục thấy mọi folder và được Full Access mặc định không cần cấp tên trong danh sách.
6. Test quyền người dùng thường với View/Edit/Full, phòng ban có trộn Admin và người thường, quyền file download/print; thử gọi RPC cấp quyền trực tiếp cho Admin → phải báo lỗi.
7. Kiểm tra CRM-005 Update_039 vẫn tạo và dùng chung folder/files. **Không cần thay lại ZIP 005**.

Lưu ý: Không tự xóa các grant Admin lịch sử trong database. Khi quản trị viên lưu lại quyền cho một folder, các lựa chọn Admin cũ không còn được gửi lên. Không nên cập nhật Production trước khi kiểm thử trên Staging.
