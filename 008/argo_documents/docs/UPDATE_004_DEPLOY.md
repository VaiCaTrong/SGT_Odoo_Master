# Documents-008 Update_004 — Vá lỗi khi mở Phân quyền

## Phạm vi
- Bản vá nhỏ kế thừa Update_003 (không lùi quyền về Update_002).
- Chỉ đổi cách sắp xếp danh sách phòng ban; không tạo hoặc đổi field database.
- Manifest: `19.0.1.4.0`.

## Triển khai
1. Sao lưu addon và database Odoo `xinyang` hiện tại (đặc biệt nếu Update_003 đã được nâng cấp).
2. Trên Staging, ghi đè đúng thư mục `argo_documents` với Update_004; restart Odoo workers và upgrade module `argo_documents` (Odoo Apps > Upgrade hoặc quy trình CLI chuẩn hiện hành).
3. Đăng nhập theo quyền quản lý chia sẻ, mở Discuss > Documents > Phân quyền. Xác nhận danh sách phòng ban tải được.
4. Chọn phòng ban, lưu View / Edit / Full; đăng nhập bằng tài khoản nhân viên để xác nhận quyền tương ứng.
5. Kiểm thử riêng phần tạo folder, tải file, quyền xóa và quyền Public nội bộ theo `docs/UPDATE_003_DEPLOY.md`. Nếu đạt mới triển khai Production.
6. Khi vẫn phát sinh RPC_ERROR, lưu traceback mới để phân biệt lỗi khác thay vì đoán.

## Hoàn tác
- Nếu chỉ lỗi giao diện từ thay đổi này, phục hồi gói Update_003 và khôi phục snapshot theo kế hoạch nâng cấp (lưu ý Update_003 có chính sách quyền khác Update_002).
- Không sửa trực tiếp PostgreSQL hoặc đặt `store=True` cho `hr.department.complete_name`.
