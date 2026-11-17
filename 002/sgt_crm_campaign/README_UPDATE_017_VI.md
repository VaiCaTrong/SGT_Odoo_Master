# CRM-002 Update_017 (19.0.1.13.0) — danh sách bắt buộc chốt + viền đỏ khi bấm chuông

Thay đổi so với Update_016 (user 2026-10-28 13:00):
1. **Dữ liệu bắt buộc để vào `5.Match Making` / `6.Approved Match Making`** (trống một ô là bị báo thiếu): **Contact** (`partner_id`), **Email** (`email_from`), **Phone** (`phone`), **Source** (`source_id`), **VN Odoo ID** (`x_getfly_id`), **Address** (`street`). (Industry của bản 016 bỏ.) Tax Code (Quick Info) KHÔNG nằm trong danh sách. Sửa ở `models/timing.py` → `MM_REQUIRED_FIELDS`.
2. **Bấm vào chuông trên form chi tiết** → mọi ô còn trống trong 6 ô trên hiện **viền đỏ**; bấm ra chỗ khác thì mất viền. Rê chuột vẫn hiện tên các ô thiếu. Chỉ CSS (chuông nhận focus; các thẻ cờ `sgt002-miss-*` chỉ tồn tại khi ô trống), không JS. Chuông xanh khi đủ dữ liệu như cũ.
3. Hộp thoại chặn và tooltip Kanban/List liệt kê theo nhãn ở mục 1.

Lưu ý:
- View form giờ tham chiếu `x_getfly_id` (VN Odoo ID): trường này có trên production và Demo 2; database không có trường này thì không cài được view (phần Python vẫn bỏ qua trường vắng).
- `Contact` là trường `partner_id` (nhãn "Contact" trong Scan); nếu Deal chưa gắn Contact (chỉ có tên liên hệ `contact_name`) thì vẫn bị tính là thiếu.
- Chưa kiểm chứng trên Odoo thật: `.o_field_widget[name="..."]` và `:has()` trên form thật; nếu ô nào không hiện viền thì xin ảnh DOM của ô đó.

Còn lại giữ nguyên README_UPDATE_016_VI.md (kèm trong gói).
