# Documents-008 Update_006 — Không đưa Admin vào danh sách cấp quyền

- Sửa hai API `explorer_users` / `explorer_departments`: lọc theo role thực tế, **không dựa vào tên**. Admin = Documents Manager (`argo_documents.group_argo_documents_manager`) hoặc Settings Administrator (`base.group_system`); `base.user_root` cũng được loại khỏi danh sách.
- Phòng ban có toàn nhân viên Admin bị ẩn; phòng ban có nhân viên thường vẫn xuất hiện (kể cả đường dẫn `Administration / Công nghệ`). Số nhân viên chỉ đếm tài khoản nội bộ đang hoạt động và không có role Admin.
- RPC `explorer_set_access` từ chối cấp quyền tường minh cho Admin hoặc phòng ban chỉ có Admin.
- Phân quyền đã lưu từ trước cho Admin không bị xóa âm thầm; khi mở hộp thoại, các lựa chọn/grants cũ này không xuất hiện và không được gửi lại khi bấm Lưu.
- Giữ nguyên quyền mặc định của Admin và View/Edit/Full cho user thường; giữ toàn bộ dữ liệu file/folder và tích hợp CRM-005 Update_039. Không yêu cầu nâng cấp CRM-005.
- Nên kiểm thử trên Staging: các nhóm Admin, phòng ban toàn Admin, phòng ban có cả Admin + nhân viên thường, RPC ngoài giao diện và cấp quyền sau khi chuyển vai trò.
