# CRM-005 Update_067 — Chọn nhiều ảnh chỉ dành cho Admin + hộp xác nhận xóa có ảnh thu nhỏ

Nền: Update_066 (19.0.1.65.0). Manifest: 19.0.1.66.0. Không field/cột mới, không migration, không đổi view XML.

## Yêu cầu (user 14/11 22:54)
Chức năng xóa ảnh hàng loạt chỉ hiện với Admin; có hộp để xác nhận xóa 1 ảnh hoặc xóa hàng loạt.
Đã hỏi lại và user chốt: nút × xóa từng ảnh **giữ nguyên cho mọi người** (bật debug + có quyền sửa Deal); hộp xác nhận **có ảnh thu nhỏ**.

## Thay đổi
1. **Chỉ Admin chọn nhiều ảnh** ("Admin" = nhóm Settings, `base.group_system`):
   - Giao diện: thanh "Select images" chỉ hiện khi `user.isSystem` (không dùng `user.isAdmin` vì đó là nhóm Access Rights).
   - Máy chủ: `action_crm005_delete_gallery_images` báo `AccessError` nếu `not self.env.is_system()`, chạy ngay sau kiểm quyền ghi, trước mọi xử lý khác. Gọi RPC thẳng cũng bị chặn.
   - `action_crm005_delete_gallery_image` (xóa 1 ảnh bằng ×) **không đổi**.
2. **Hộp xác nhận mới `SGTGalleryDeleteDialog`** dùng chung cho × (1 ảnh) và xóa nhiều:
   - Hiện câu hỏi, các ảnh sắp xóa (tối đa 24 ảnh thu nhỏ, còn lại ghi "+N more"), nút **Delete** đỏ và **Cancel**. Một ảnh thì hiện ảnh lớn.
   - Khi xóa **mọi** ảnh của Gallery: dòng đỏ "This is EVERY picture of the gallery (N)."
   - Hộp không gọi RPC; chỉ bấm Delete mới chạy hàm `confirm` do widget truyền vào. Hai nút khóa trong lúc đang chạy (chống bấm đúp). Lỗi RPC: hộp đóng, thông báo đỏ, lỗi chuyển cho trình báo lỗi của Odoo như hộp cũ.
   - File mới: `static/src/js/gallery_delete_dialog.js`, `static/src/xml/gallery_delete_dialog.xml` (đã thêm vào manifest); CSS cuối `yellowpages_profile.scss` (không giới hạn trong `.o_form_view` vì hộp nằm dưới `<body>`).

## Kiểm thử (offline, KHÔNG chạy Odoo 19 thật)
- `test_update066_bulk_delete.py` (20): thêm không-Admin bị `AccessError` (dù có quyền ghi) và không ghi gì, kiểm Admin chạy trước kiểm payload, xóa 1 ảnh vẫn dùng được với không-Admin.
- `test_update067_contract.py` (13): cổng Admin ở máy chủ chỉ cho hàm xóa nhiều, cổng giao diện dùng `isSystem`, × không bị khóa, cả hai đường xóa dùng hộp mới, hộp không có `orm`, manifest/asset, tên template, nút, giới hạn 24, cảnh báo xóa hết, CSS không ràng buộc `.o_form_view`.
- Mutation: bỏ cổng máy chủ, thêm cổng Admin vào xóa 1 ảnh, bỏ cổng giao diện: đều có test đỏ (cổng giao diện bị bắt bởi test Chromium).
- Chromium thật + OWL 2 + JS/XML/SCSS thật, hộp dựng thật (`pg_gallery_select_test.py`, 63 kiểm tra): Admin thấy thanh; không-Admin không thấy thanh nhưng vẫn có × và xóa được 1 ảnh qua hộp mới; hộp 1 ảnh đúng ảnh được bấm; hộp nhiều ảnh đúng thứ tự; Cancel không gửi gì; xóa hết có cảnh báo đỏ; 30 ảnh ⇒ 24 thumbnail + "+6 more"; RPC lỗi đóng hộp và giữ lựa chọn; không lỗi console.
- `test_update062_compact_footer` ghim hash `models/crm_lead.py`: đã ghim lại. Test cũ khác y hệt Update_066.

**Chưa chạy trên Odoo 19 thật:** thành phần `Dialog` thật (kích thước/overlay), `user.isSystem` từ session thật, sanitizer Html. Test dùng bản giả của `Dialog` có cùng khe `default`/`footer` và props như Odoo 19 (đã đối chiếu mã nguồn 19.0 trên GitHub).
