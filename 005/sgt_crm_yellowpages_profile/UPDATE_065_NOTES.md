# CRM-005 Update_065 — Sửa lỗi: ảnh đẩy từ Documents hiện thành chữ HTML trong Image Gallery

Nền: Update_064 (19.0.1.63.0). Manifest: 19.0.1.64.0. Không field/cột mới, không migration.

## Lỗi (user báo 14/11 11:30, ảnh chụp Deal "Ms. Kim Nga")
Bấm "Cập nhật ảnh lên CRM" trên Deal đã có sẵn ảnh Gallery: ảnh mới hiện ra là chữ
`<figure><img src="data:image/jpeg;base64,…" alt="…"><figcaption>…</figcaption></figure>` thay vì ảnh.

## Nguyên nhân
Odoo trả giá trị field Html dưới dạng `markupsafe.Markup`. `Markup + str` tự escape phần `str` bên phải
(`<` → `&lt;`, `"` → `&#34;`), nên thẻ ảnh mới bị lưu thành chữ. Chỉ xảy ra khi Gallery đã có nội dung
(Gallery trống: `'' + str` vẫn là str thường). Test Update_064 dùng chuỗi thường nên không bắt được.

## Sửa
- `merge_gallery_html`: đổi cả hai vế sang `str` trước khi nối.
- Tự sửa dữ liệu đã hỏng: `heal_escaped_figures` đổi lại các thẻ `&lt;figure&gt;…&lt;/figure&gt;` mà bên trong có
  `<img src="data:image/…` (đúng dấu vết của lỗi này); chữ khác giữ nguyên. Bấm "Cập nhật ảnh lên CRM" một lần trên
  Deal bị hỏng (kể cả khi toàn ảnh trùng) là trang được sửa, ảnh hiện lại.
- Test mới (5): Gallery dạng Markup không bị escape, nối Markup, sửa thẻ đã hỏng, sửa riêng khi toàn ảnh trùng, không đụng chữ
  không phải thẻ của mình. Fake Lead trong test giờ trả `Markup` như Odoo. Mutation: 4 kiểu làm hỏng đều có test đỏ.

**Chưa chạy trên Odoo 19 thật.**
