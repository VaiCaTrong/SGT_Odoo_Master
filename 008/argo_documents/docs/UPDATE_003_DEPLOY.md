# Xinyang Documents-008 · Update_003 — Triển khai và nghiệm thu

## Trạng thái
- Mã nguồn đã bổ sung. **Chưa được thử nghiệm trên Odoo 19 chạy thực tế hoặc Production.**
- Bản nền: Update_002 (`19.0.1.2.0`). Bản mới: Update_003 (`19.0.1.3.0`).
- Chỉ thay đổi addon `argo_documents`; **không thay đổi CRM-005/CRM-002**.
- Cần nâng cấp module bằng Odoo module upgrade để tạo các cột quan hệ/field mới. Chỉ chép đè file rồi restart là **chưa đủ**.

## Nguyên tắc phân quyền

| Vai trò/thao tác | View | Edit | Full |
|---|---|---|---|
| Xem, xem trước, download | ✓ | ✓ | ✓ |
| Upload, tạo folder con, sửa file, di chuyển | — | ✓ | ✓ |
| Xóa folder, file, thùng rác | — | — | ✓ |
| Đổi phân quyền | — | — | **Chỉ** Documents Manager hoặc được cấp nhóm ủy quyền chia sẻ và có Full trên folder |

- `Public` là *Documents Users nội bộ có quyền đăng nhập*, **không phải người ngoài Internet**. Với folder mới, còn giới hạn theo `company_id`.
- Folder con không được cấp quyền rộng hơn folder cha. Nếu Admin muốn chia sẻ sang nhóm khác phải cấp quyền thích hợp ở folder cha trước.
- Người tạo folder là `create_uid` (không được thay bằng Salesperson hiện tại). Folder mới mặc định Private; người tạo Edit; **không tự Full**.
- Folder cấp gốc chỉ do Documents Manager hoặc người mang nhóm `Được tạo thư mục cha` tạo. Tạo file trực tiếp ở root chỉ Documents Manager.
- Thay đổi chia sẻ chỉ từ Explorer, lưu vào `argo.document.permission.audit`, hiển thị trong `Discuss → Technical → Documents: Nhật ký phân quyền`.
- Nhân viên chỉ có View không được upload/sửa/xóa; kiểm tra thêm ở ORM server và Record Rules, không chỉ trên UI.

## Folder cũ (Legacy) — điều kiện an toàn
- Các bản ghi cũ chưa được đặt chế độ mới vẫn được xử lý dưới `access_mode=legacy`; không tự đổi Private/Public, không xóa hoặc di chuyển file.
- Legacy cố gắng giữ khả năng **xem và sửa** trước đây nhưng **xóa** bị thu hẹp để an toàn (chỉ Full hoặc Admin). Admin phải rà soát folder cũ và chuyển từng folder sang chế độ mới.
- Legacy folder chưa có `company_id` không bị tự ép sang công ty hiện tại; phải rà soát quyền và công ty trước khi chuyển.
- Thay đổi Model và Rule có tác động an ninh toàn hệ thống 008; **staging bắt buộc** và cần kiểm thử tài khoản thật.

## Cài đặt trên Staging (không áp Production trước nghiệm thu)
1. Sao lưu DB và sao lưu gói `xinyang_documents_008_V01_Update_002.zip`. Đảm bảo có thể phục hồi snapshot DB.
2. Giải nén Update_003 vào `addons_path` đúng tên thư mục `argo_documents` và sửa quyền file phù hợp.
3. Dừng worker liên quan, nâng cấp module `argo_documents` bằng chức năng Upgrade Odoo (hoặc CLI `-u argo_documents -d xinyang --stop-after-init` với cấu hình môi trường phù hợp). Theo dõi migration SQL và registry load, nếu lỗi rollback cả DB + file.
4. Khởi động lại worker, cập nhật assets; mở Discuss → Documents, F5/hard reload.
5. Trong Users/Access Rights, cấp `Người dùng kho tài liệu`, và riêng cho người được ủy quyền cấp gốc `Được tạo thư mục cha`; người được ủy quyền quản lý chia sẻ thêm `Được quản lý chia sẻ folder có Full Access` (vẫn phải có quyền Full thực tế trên folder).
6. Admin tạo `CRM Information` và `Xinyang Information` tại root, đặt quyền View/Edit/Full cho phòng ban hoặc User theo nhu cầu. **Không auto tạo hoặc auto Public khi cài module.** Lưu folder ID của `CRM Information` để dùng trong CRM-005 Update_039 sau này.
7. Không bắt đầu CRM-005 nếu các ca phân quyền bên dưới chưa đạt.

## Bộ kiểm thử nghiệm thu bắt buộc trên Odoo thật

| ID | Thao tác | Kỳ vọng |
|---|---|---|
| D01 | User thường tạo folder cấp root | Từ chối; root creator được tạo |
| D02 | Sales A tạo con trong CRM Information nơi có Edit | Tạo Private, `create_uid` = A, Edit không tự Full |
| D03 | Sales B mở folder Private của A | Không thấy / AccessError qua RPC, menu cây, URL |
| D04 | User chỉ View tải tài liệu | Được |
| D05 | User chỉ View upload, rename, move, trash, gọi `write/unlink` RPC trực tiếp | Bị từ chối |
| D06 | User Edit upload / thay file / đổi tên / tạo thư mục con | Được |
| D07 | User Edit xóa file/folder bằng UI và RPC | Bị từ chối |
| D08 | User Full xóa file, folder, khôi phục (khi toàn bộ subtree cho phép) | Được, có xác nhận |
| D09 | Quyền theo phòng ban / User | Chỉ đúng người, đúng mức, khi chuyển phòng quyền thay đổi |
| D10 | Public View/Edit/Full | Chỉ User nội bộ có Documents, không lộ ra công khai Internet |
| D11 | Người tạo không có nhóm Share Manager tự gọi `explorer_set_access` | Bị từ chối |
| D12 | Người có Share Manager nhưng chưa Full tự đổi quyền | Bị từ chối |
| D13 | Thu hồi quyền View/Edit/Full | RPC tiếp theo bị chặn, cả download/preview/ZIP và ir.attachment |
| D14 | Folder con định cấp quyền vượt folder cha | Từ chối, không âm thầm nới quyền |
| D15 | User ở Company A thử truy cập folder thuộc Company B | Bị từ chối, Manager theo quản trị được cấp |
| D16 | Folder Legacy cũ | Dữ liệu giữ nguyên, không tự chuyển Public/Private |
| D17 | Copy, Move, Replace, Folder upload, text editor, ZIP, Trash, Cron | Không lách quyền hoặc lỗi hồi quy |
| D18 | Nhân viên thao tác trên `ir.attachment` bằng `/web/content`, `/web/image` và RPC trực tiếp | Không thể đọc/ghi attachment nếu tài liệu gốc không cho phép |
| D19 | Tải nhiều file, file lớn, concurrent delete/move, hai user cùng cấp quyền | Không có cập nhật nửa chừng hoặc rò thông tin |
| D20 | Kiểm tra Group admin, root creator, user, share delegate | Đúng phân tách chức năng, không tăng quyền CRM khác |

**T17/T18 ở mức HTTP/attachment cực kỳ quan trọng:** Odoo tiêu chuẩn thường kiểm tra quyền từ res_model/res_id khi truy xuất attachment, nhưng phải **chứng minh trên bản Odoo triển khai thật**. Không tuyên bố an toàn tuyệt đối khi chưa nghiệm thu.

## Rollback
- Nếu cài lỗi: khôi phục snapshot Database và bản addon Update_002 tương ứng, sau đó khởi động lại Odoo. Tránh chỉ ghi đè code cũ, vì có thể để lại schema/rules/role không đồng bộ.
- Nếu muốn quay về ACL Update_002, quyền sẽ rộng hơn; phải đánh giá bảo mật trước khi rollback, không làm im lặng trên Production.

## Phụ thuộc tiếp theo
- CRM-005 Update_039 sẽ tích hợp Create Documents, chọn vị trí trong cây, liên kết Deal/folder bằng ID và upload theo cùng chính sách 008. Gói này **chưa** sửa CRM-005.
