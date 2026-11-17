# CRM-007 — `sgt_contact_company_profile` 19.0.1.2.0 (Update_003)

## Update_003 — Giao diện mới + phòng tránh lỗi CSS (01/11/2026)

- Cải tạo Form Contact theo mẫu người dùng duyệt: thẻ Person/Company, Contact, **Địa chỉ & Tọa độ trong cùng box**, Business Type, Main Market, Employee Size, Industries, Quick Info, Profile Links; Introduction English/Vietnamese hai box ngang, Gallery và Partners trước notebook chuẩn Odoo. Individual có đủ phần; Company chỉ các box cơ bản.
- Không làm thay đổi field lưu dữ liệu, không tạo field/model/JS/cron/API mới. Tọa độ dùng **`res.partner.partner_latitude` / `partner_longitude`** đã tồn tại trên Scan Xinyang 11/10/2026. Tọa độ 0/thiếu hiển thị "Chưa xác định". Không tự tính tọa độ, không mở Google Maps tự động; muốn tự cập nhật tọa độ dùng CRM-006 Update_004 và Odoo Geolocation đã cài.
- **Asset stability:** bỏ file SCSS và chuyển sang `static/src/css/contact_company_profile.css` (CSS thuần), sửa manifest tương ứng. Loại biểu thức Sass `min(100%,300px)` trong bản 002, tránh nguồn nghi vấn của lỗi `Style compilation failed` trên backend. Không khẳng định đây là nguyên nhân duy nhất khi chưa có stacktrace Odoo Production.
- CSS chỉ tác động lên `.sgt_cp_*` bên trong `.o_form_view`; bỏ can thiệp `.o_address_format` gốc. Dùng grid an toàn `minmax(0,1fr)` và breakpoint mobile/Chatter. Không thay UI-004/navbar/Discuss.
- Person avatar `image_1920` chỉnh được theo quyền Contact; Company logo đọc từ `parent_id.image_128` qua field related không lưu đã có từ Update_002; Company avatar chỉ xem.
- Profile Contact chỉ xem; sửa ở Deal CRM-005 rồi bấm Cập nhật Contact của CRM-006. Không ảnh hưởng dữ liệu bản ghi cũ; không cài bằng Uninstall.
- Các tab và trường nhập địa chỉ chuẩn Odoo vẫn được giữ. Box địa chỉ bản mới chỉ hiển thị giá trị hiện tại của chính Contact (Individual), không thay bằng address related Company cha.

**Kiểm tra offline:** chạy `python tests/test_update001_offline.py <odoo_views.csv> <odoo_fields.csv>` với dữ liệu Scan Xinyang 11/10; kiểm tra XML, 15 field có sẵn/đã duyệt, XPath, CSS thuần và 2 field tọa độ. Chưa chạy/biên dịch trên chính máy chủ Xinyang. Muốn nghiệm thu an toàn phải backup và thử bản sao production, kiểm tra browser console/server log, Discuss/Contacts/CRM, mobile/desktop, Chatter mở, từng loại Contact.

**Cài đặt:** thay thư mục mã addon qua `addons_path` và **Upgrade CRM-007** (không Uninstall), sau khi đã sao lưu. Đảm bảo đã cài UI-004 và `contacts`; không yêu cầu thêm module nào. Sau đó có thể nâng CRM-006 Update_004. Chỉ cài lên Production khi đã test staging giống Production và có phương án rollback.

---

# CRM-007 — `sgt_contact_company_profile` 19.0.1.1.0 (Update_002)

## Update_002: bố cục theo CRM-005, viền và avatar độc lập (2026-10-31)

- Contact **Individual**: avatar `image_1920` cho phép nhân viên sửa theo ACL chuẩn của Odoo, kể cả khi `x_sgt_crm_synced=True`.
- Contact **Company**: logo nằm ở ảnh chuẩn `image_1920` của bản ghi Company, avatar tại header là chỉ xem.
- Thẻ Company trên Individual dùng field **liên kết không lưu** `x_sgt_crm007_company_logo = related('parent_id.image_128')`, không dùng `image_128` của Person, nên không thể hiện nhầm ảnh cá nhân thành logo Company.
- Company card: tên công ty, ảnh Company, thông tin địa chỉ được hiển thị thêm bằng các field Contact chuẩn (dòng Street rồi đến Street 2/City/State/ZIP/Country). Không thay thế các trường địa chỉ gốc của Odoo. Lưu ý: địa chỉ hiển thị sử dụng địa chỉ hiện có của Contact, không thêm các related address field mới; nếu cần riêng địa chỉ Company cha phải có quyết định khác.
- Khung tổng Company Profile và các box thông tin lớn có đường viền và thanh trên xanh #0061BD, bo góc và đổ bóng nhẹ theo CRM-005 Update_032; thêm Contact card ở cột phải, giữ Quick Info, links, Industries.
- Individual có cặp **Company Introduction (English/Vietnamese)** độc lập, bằng nhau, cạnh nhau như CRM-005; Gallery và Partners phía dưới, tất cả nằm **trước** các tab chuẩn Odoo. Company vẫn chỉ có hồ sơ doanh nghiệp cơ bản; ba phần Intro/Gallery/Partners không hiển thị.
- Các field hồ sơ, Gallery, Partners và Introductions vẫn read-only; nút CRM-006 đồng bộ. `x_sgt_crm_synced` vẫn đánh dấu record đã đồng bộ nhưng không khóa avatar.
- **Field mới duy nhất:** `x_sgt_crm007_company_logo` (fields.Image related, `store=False`, readonly). Không thêm JS/API/cron, không tạo cột hình ảnh mới.
- **Kiểm thử offline:** 20/20 kiểm tra với Scan Odoo 19 Xinyang 2026-10-11 (field/xpath/SCSS/contracts), chưa chạy Odoo thật. Luồng hiển thị Company/Individual và nút avatar phải thử trên Demo 2 trước Production.

## Cài đặt

1. Sao lưu Demo 2; thay thư mục addon bằng Update_002, restart Odoo, **Upgrade** CRM-007 (không Uninstall).
2. Mở Contact Individual có Company: avatar Person chỉnh được; thẻ Company hiển thị logo từ Company cha. Thay ảnh Person → Company không đổi.
3. Mở Contact Company: Company Profile cơ bản, logo hiện từ chính Company; các box Intro/Gallery/Partners ẩn.
4. Mở Contact #97 (hoặc dữ liệu test tương đương), xác nhận giao diện không tràn khi Chatter mở; không phải kiểm chứng trên Production trước.
5. Nâng CRM-006 Update_003; thử thay logo CRM-005 rồi bấm **Cập nhật Contact**: chỉ Company đổi logo, Person không đổi avatar.

---

## Lịch sử: Update_001 (19.0.1.0.0)

## Làm gì
Form **Contact** (res.partner) hiển thị **hồ sơ công ty Trang Vàng** giống Deal (CRM-005). Dữ liệu mới trên Contact là **chỉ xem**: sửa ở Deal trong CRM, rồi bấm **"Cập nhật Contact"** (addon CRM-006 Update_002) để đẩy sang.

| Hiển thị trên Contact | Field | Ghi chú |
|---|---|---|
| Business Type / Main Market / Employee Size | `x_type_contact` / `x_country` / `x_yp_employee_range` | 3 thẻ |
| Business Industries | `x_fb_industry` | thẻ riêng |
| Profile Link: Link Zalo Group, Link Profile, Group URL, Post URL | `x_url_zalo_group`, `x_url_fb_profile`, `x_group_link`, `x_group_post_link` | link bấm được |
| Quick Info: Tax Code / Founded Year / Yellow Pages | `vat` (có sẵn) / `x_yp_founded_year` / `x_yp_listing_url` | |
| Company Introduction (English \| Vietnamese) | `x_yp_intro_en` / `comment` (Notes, có sẵn) | hộp, mở sẵn |
| Image Gallery | `x_yp_gallery_html` | hộp, mở sẵn |
| Partners | `x_yp_partners_html` | hộp, mở sẵn |
| Logo công ty = ảnh đại diện | `image_1920` (có sẵn) | chỉ-xem **chỉ với Contact đã đồng bộ từ CRM** (`x_sgt_crm_synced`) |
| Address | `street`… (có sẵn) | cùng bố cục thẻ Company của CRM-005: Street dòng 1 (có ghim), dòng 2 = Street 2, City, State, ZIP, Country |

* **Cá nhân (Individual)**: thẻ công ty (logo + tên Company cha), các thẻ thông tin, rồi 3 hộp dưới các tab.
* **Công ty (Company)**: chỉ khối **Company Profile** (các thẻ thông tin); 3 hộp bị ẩn.
* Khối Company Profile tự ẩn khi Contact chưa có dữ liệu nào trong các ô trên. Hộp trống cũng ẩn.
* Màn hẹp / mở Chatter: các cột tự xuống dòng, không tràn ngang.

## Field mới (14, đều `copy=False`)
13 field hồ sơ (bảng trên) + `x_sgt_crm_synced` (Boolean, chỉ đọc; do nút "Cập nhật Contact" đặt). **Không tạo** field cho Tax Code (dùng `vat`), giới thiệu tiếng Việt (dùng `comment`), logo (dùng `image_1920`), địa chỉ. Đối chiếu Scan 2026-10-11: không field nào trùng. Danh sách + lý do: `FIELD_REGISTRY_CRM007.csv`.

## Không có
Không JS, không cron, không API, không dữ liệu mặc định, không sửa bố cục địa chỉ của CRM-005, không đụng nút Create Contact. Phụ thuộc: `contacts`. Chỉ sửa 3 chỗ của form Contact gốc: thuộc tính `readonly` của ảnh đại diện, class của khối địa chỉ, và chèn 2 khối (trước / sau notebook).

## Cài / nâng cấp trên Demo 2 (cài TRƯỚC addon 006 Update_002)
1. Sao lưu DB. Chép thư mục `sgt_contact_company_profile` vào addons_path, restart Odoo.
2. Apps → Update Apps List → "SGT CRM-007" → Install.
3. Mở một Contact bất kỳ chưa đồng bộ: **không có gì thay đổi** ngoài bố cục địa chỉ (Street dòng 1; Street 2, City, State, ZIP, Country dòng 2); ảnh đại diện vẫn bấm đổi được.
4. Cài tiếp CRM-006 Update_002, bấm "Cập nhật Contact" trên một Deal → mở Contact → thấy khối Company Profile + 3 hộp; ảnh đại diện (logo) lúc này chỉ xem.

## Chưa kiểm chứng trên Odoo thật
* Bố cục kiểm bằng trình duyệt giả lập từ đúng arch của Scan (form 127 + toàn bộ extension), chưa mở trên Odoo thật.
* Widget `html` chỉ-xem hiển thị ảnh dán của Gallery/Partners dạng lưới: dùng cùng kỹ thuật CSS của CRM-005; cần nhìn thử trên Odoo thật.
* Địa chỉ dùng chung các ô `street…` của Odoo nên geolocation vẫn dùng cùng dữ liệu; chỉ đổi cách xếp.
