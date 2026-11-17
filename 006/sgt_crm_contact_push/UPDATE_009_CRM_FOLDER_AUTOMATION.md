# MASTER ODOO — Automatic CRM Information folder after Create Contact

Ngày phát hành: 2026-11-12. Phạm vi: Documents-008 Update_009, CRM-005 Update_055, CRM-006 Update_009.

## Chức năng

- Khi nút Create Contact của `crm_sync_contact_odoo2` tạo/gắn Contact và phát tín hiệu `x_groupname`/`x_getfly_id`, CRM-006 hook gọi API Documents-008 để tìm hoặc tạo folder tự động. Không sửa module `crm_sync_contact_odoo2`.
- Tạo dưới folder hệ thống `CRM Information`, tên mới: `crm.lead.partner_name - crm.lead.x_yp_tax_code` (ví dụ `Công ty TNHH ABC - 0312345678`).
- Chỉ tạo khi Deal có tên công ty và MST hợp lệ. Thiếu thông tin / thiếu quyền / nhiều folder trùng MST => không tạo folder, không chặn Create Contact; CRM-006 ghi cảnh báo trong Chatter khi là lỗi nghiệp vụ Documents (UserError/AccessError).
- Dùng đúng API `argo.document.folder.explorer_create_deal_folder`, giữ thao tác Create Folder thủ công để dự phòng; chống trùng bằng advisory lock và kiểm tra MST chính xác.
- Deal đã có folder liên kết => giữ nguyên. Tìm và dùng lại các folder dạng `MST` (cũ) hoặc `Tên công ty - MST` (mới) trong CRM Information; folder cũ không bị đổi tên, di chuyển, xóa hoặc di chuyển file. Với nhiều Deal cùng MST, chỉ dùng chung khi user có quyền Edit folder; không tự mở quyền riêng tư.
- Documents-008 tìm kiếm theo tên folder `ilike`: tên công ty hoặc MST đều khớp vì tên mới chứa cả hai. Tìm từ cây `CRM Information` để thấy folder theo đúng quyền. Dữ liệu cũ chỉ có tên MST sẽ tìm được theo MST.
- CRM-005 Documents box hiển thị tên folder mới và có nút Refresh khi vừa Create Contact.
- Không tạo field/cột database mới trong bất kỳ module nào. Không sửa Geolocation CRM-005 Update_054, đồng bộ Lat/Lon CRM-006 Update_008 hay CRM-007 Update_003.

## Thứ tự nâng cấp trên CLONE/STAGING (bắt buộc kiểm thử trước Production)

1. Sao lưu DB `xinyang` và các addon đang chạy; xác nhận các module cũ hoạt động.
2. Thay toàn bộ addon `argo_documents` bằng Documents-008 Update_009.
3. Thay toàn bộ addon `sgt_crm_yellowpages_profile` bằng CRM-005 Update_055.
4. Thay toàn bộ addon `sgt_crm_contact_push` bằng CRM-006 Update_009, dựa trên nền ổn định CRM-006 Update_008 (không dùng Update_007 gây thiếu cột).
5. Restart **tất cả** Odoo workers và cron, sau đó Upgrade theo thứ tự: `argo_documents` → `sgt_crm_yellowpages_profile` → `sgt_crm_contact_push`; không Uninstall bất cứ module nào. Làm mới browser `Ctrl+Shift+R`.
6. Kiểm tra `CRM Information`, quyền người dùng, tên folder và Chatter.

## Các trường hợp nghiệm thu

- Deal mới có Company Name + MST, Create Contact thành công: xuất hiện đúng một folder `Company - MST` và link vào Deal.
- Bấm Create Contact/ghi marker lần nữa: không tạo trùng. Mở lại Documents box hoặc nhấn Refresh để thấy folder.
- Deal khác cùng MST: dùng lại folder nếu có quyền, không tạo folder thứ hai; nếu folder riêng của user khác, thông báo cảnh báo và Admin cấp quyền trước.
- Deal thiếu Company Name/MST: Contact vẫn được tạo, Folder chưa tạo, ghi cảnh báo.
- Đã có folder MST cũ / folder link cũ / folder trong Thùng rác / hai folder cùng MST: xử lý an toàn, không đổi tên và không ghi đè tài liệu.
- Tìm bằng tên công ty (chuỗi bất kỳ) hoặc MST từ Documents → CRM Information; chỉ hiển thị folder người dùng có quyền đọc.
- CRM-005 Geolocation thủ công và Cron, CRM-006 đồng bộ Contact/LatLon, CRM-007 Contact form, Kanban New/drag và Gallery giữ nguyên.

## Giới hạn

Việc tự tạo folder phụ thuộc vào tín hiệu ghi `partner_id` và `x_groupname`/`x_getfly_id` của addon Create Contact gốc. Cần kiểm tra đúng thứ tự trường trong Odoo production; các tình huống addon gốc không ghi tín hiệu không được chứng minh bởi unit test offline.

**Chỉ xác minh mã và kiểm thử offline; chưa chạy trên Odoo Production.**
