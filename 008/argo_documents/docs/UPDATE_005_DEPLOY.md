# Triển khai Documents-008 Update_005 + CRM-005 Update_039

## Thứ tự bắt buộc

1. **Sao lưu DB `xinyang` và source addons** `argo_documents` / `sgt_crm_yellowpages_profile` trước khi thay đổi.
2. Trên Staging: chép folder `argo_documents` từ ZIP Update_005 vào Odoo addons path, restart, **Upgrade addon** (manifest `19.0.1.5.0`).
3. Xác nhận Odoo Settings Administrator (group `base.group_system`) hoặc Documents Manager có thể đọc/tạo/sửa/xóa folder Private do User khác tạo mà không cần grant, và những user thường không được leo quyền.
4. Tạo root folder **CRM Information** bằng Admin; tại Odoo Settings > General Settings > Kho tài liệu, gán chính Folder ID này vào `CRM Information — thư mục gốc cho CRM-005`.
5. Với nhu cầu Sales tạo folder bên dưới root: Admin cấp quyền **Edit** tại root `CRM Information` (ví dụ Public nội bộ Edit hoặc restricted theo phòng ban/User). Quyền ở root chỉ cho phép điều hướng/tạo bên dưới, không mặc nhiên mở folder con Private do Sales khác tạo.
6. Sau khi 008 được nghiệm thu, chép `sgt_crm_yellowpages_profile` Update_039 vào addons path, restart, **Upgrade addon** (manifest `19.0.1.38.0`). Module này phụ thuộc `argo_documents`.
7. Mở Deal đã lưu: Detail Fields > Documents (nằm trên Zalo Group Post), nhấn Create Documents, chọn CRM Information hoặc folder của mình, tên mặc định theo công ty, tạo folder rỗng, kéo-thả Catalog/ảnh/PDF. Mở Documents ở Discuss để đối chiếu cùng folder/files.
8. Trong trình duyệt refresh cứng Ctrl+Shift+R để cập nhật JS/CSS; nếu cần dùng chế độ debug assets để phân tích lỗi.

## Trường hợp phải kiểm thử

- Admin Settings/Manager: thấy toàn bộ folder/file, mở phân quyền, xem mọi folder cá nhân, cập nhật file và xóa có kiểm soát.
- Sales A với root Edit: tạo folder Deal A (Private), upload và tải xuống; không được xem Deal B Private của Sales B.
- Sales B chỉ View: không có nút upload/tạo folder tại khu vực không cấp Edit; yêu cầu RPC trái phép phải bị chặn.
- Folder đang trống: hai bên 005/008 báo trống, không tự tạo ảnh hoặc file mặc định.
- File > giới hạn dung lượng: server từ chối; lỗi được hiển thị nhưng các file đã tải thành công vẫn tồn tại.
- Folder đã tạo/Deal đã có link: không tạo trùng, kiểm tra lặp request/2 tabs.
- Thay người phụ trách Deal: không thay `create_uid` của folder; không tự động đổi quyền nếu Admin chưa cấp.
- Record chưa Save: 005 yêu cầu lưu Deal trước khi tạo folder.
- Folder ngoài CRM Information hoặc nằm trong Trash: có cảnh báo, không lén tạo liên kết thứ hai.
- API `/argo_documents/upload`, `explorer_deal_folder_info`, URL `/web/content` với tài khoản không có quyền; kiểm tra quyền RPC.
- Đối chiếu tập tin cũ: danh sách folder và file trước/sau upgrade, bản ghi trong Trash, ảnh Gallery / MM, Kanban logo và spacing không thay đổi.

## Giới hạn kiểm thử

Gói ZIP được kiểm tra tĩnh (Python, JS, XML, manifest, hợp đồng API); **chưa chạy test database Odoo 19 thật**. Không trực tiếp triển khai Production khi chưa nghiệm thu Staging.
