# CRM-006 — `sgt_crm_contact_push` 19.0.1.5.0 (Update_006)

## Update_006 — Đồng bộ đầy đủ ngay sau Create Contact thành công (01/11/2026)

**Mục tiêu:** Sau khi addon `crm_sync_contact_odoo2` tạo/liên kết Contact thành công, CRM-006 tự động điền đầy đủ thông tin từ Deal vào Contact và Company trong một lượt, **không yêu cầu bấm thêm Cập nhật Contact**. Không thay đổi bất cứ file, wizard, method hay dữ liệu nào của addon cũ.

- **Trigger của riêng CRM-006:** `crm.lead.write()` kiểm tra hai trường tín hiệu `x_groupname` / `x_getfly_id` và sự kiện liên kết `partner_id`, hỗ trợ các thứ tự ghi khác nhau. Chỉ chạy nếu Contact đã được liên kết và cờ đồng bộ sẵn có `res.partner.x_sgt_crm_synced` còn False. Chống chạy lặp khi hai marker được ghi nhiều lần. Những lần sửa Deal thông thường không kích hoạt đồng bộ đầy đủ.
- **Đồng bộ đầy đủ lần đầu:** sử dụng `overwrite_native=True`, chung mapping với nút **Cập nhật Contact**: Contact nhận Address, Website, Job Position, VAT, Salesperson, Reference, Phone, Email, hồ sơ CRM-007 và Tags; Company nhận địa chỉ, website, VAT, hồ sơ và logo. Chỉ ghi khi Deal có giá trị mới; **Deal trống không xóa dữ liệu cũ**. Avatar Person được giữ nguyên; logo chỉ ghi vào Company.
- **Liên kết Company:** tìm mã số thuế trước, sau đó so tên chuẩn hóa. Có Company duy nhất và hợp lệ thì tái sử dụng; tên trùng nhưng VAT xung đột, có nhiều bản trùng hoặc bản lưu trữ thì **không tạo/không tự liên kết**, ghi cảnh báo để xử lý thủ công. Chưa có Company thì tạo mới một Company; lỗi xác thực VAT không thử tạo lại mà bỏ VAT vì có nguy cơ nhân đôi.
- **Báo cáo đúng dữ liệu:** đọc lại các field sau write, kiểm tra nghiêm ngặt `parent_id`. Không báo nhầm Latitude/Longitude reset về 0 là đã tính tọa độ thành công. Nếu geocoder không có kết quả hoặc thiếu địa chỉ, cảnh báo Geolocation riêng. Lỗi đồng bộ bổ sung phải không làm hỏng giao dịch Create Contact của addon cũ.
- **Nút Cập nhật Contact thủ công:** giữ đầy đủ chức năng Update_005, cho phép đồng bộ lại khi dữ liệu Deal thay đổi; không đổi `crm.lead.partner_id`, không tự đổi `is_company`, không merge/xóa Person cũ, không sinh Person giả theo tên công ty hay nhãn Hotline.
- **Không thêm field, model, JS/CSS, cron, API hay permission.** Phụ thuộc CRM-007 để dùng các trường hồ sơ Contact. Không sửa CRM-005/007 hoặc `crm_sync_contact_odoo2`.

### Kiểm thử và giới hạn

- **92 unit tests ngoại tuyến đạt**, bao gồm thứ tự tín hiệu trước/sau liên kết Contact, chống trùng trigger, Person và Company, avatar/logo, trường Phone/Email, field read-back, Company trùng/archived/VAT xung đột, Geolocation, lần cập nhật thủ công. XML parse, Python compile, ZIP CRC kiểm chứng trước phát hành.
- **Đang cần kiểm chứng trên bản sao Production:** nguồn addon cũ chưa được đọc, vì thế `x_groupname`/`x_getfly_id` là **tín hiệu quan sát được, chưa phải chứng cứ bất biến của nút Create Contact thành công**; có thể phát sinh từ luồng khác. Phải kiểm tra Chatter và thứ tự `crm.lead.write` thực tế, cài thử trên clone Production trước khi dùng trên Production. Các trường hợp ghi cạnh tranh đồng thời hoặc duplicate VAT ở cấp database chưa được bảo đảm tuyệt đối bởi test ORM giả.
- **Thứ tự nâng cấp:** backup DB + addons, clone Production, giữ CRM-005 Update_032 + CRM-007 Update_003, chỉ Upgrade CRM-006 Update_006, không Uninstall, kiểm thử Create Contact lần đầu và lần cập nhật sau; chỉ triển khai Production sau nghiệm thu.

---

# CRM-006 — `sgt_crm_contact_push` 19.0.1.4.0 (Update_005)

## Update_005 — Hoàn thiện trường Contact hiện có và sửa nguy cơ trùng Company (01/11/2026)

- **Bổ sung nút thủ công Cập nhật Contact:** ghi đè `res.partner.email` từ `crm.lead.email_from` (fallback `x_email01`) và `res.partner.phone` từ `crm.lead.phone` (fallback `x_phone`, `x_mobilephone`) nếu Deal có dữ liệu khác hiện tại. Deal bỏ trống: giữ số/email trên Contact. **Create Contact** vẫn bảo thủ: không tự ghi đè email/phone khi trigger cũ chạy.
- **Sửa lỗi nghiêm trọng khi tra Company:** Update_004 có thể TẠO Company trùng khi tìm thấy Company theo VAT/tên nhưng `fill_existing=False` (nút thủ công); bản mới tái sử dụng Company đã khớp, sau đó chỉ cập nhật trường có dữ liệu, không tạo bản thứ hai.
- **Giữ nguyên:** các profile field CRM-007, Address, VAT, Website, Job Position, Salesperson, VN Odoo ID, Tags trên Individual; cập nhật Company cha với Address/Website/VAT + profile + logo. Không ghi đè avatar Person; không chuyển Contact sang Company khác nếu đã có parent_id; không tự đổi tên Person hay tên Company khi dữ liệu chưa được đối chiếu. Phone/Email của Person **không đẩy lên Company cha** (tránh thay số/email tổng đài bằng số cá nhân). Nếu Deal trỏ trực tiếp vào Company thì đối tượng nhận là chính Company.
- **Không thể bảo đảm lấp đủ mọi field trên bản ghi #97:** trang Production đòi đăng nhập, chưa xem trực tiếp được; bản Scan 2026-10-11 có nhiều trường Contacts chuyên ngành không có nguồn trên CRM Deal (Company Registry, Industry ID, Language, kế toán...). Không tự điền suy diễn.
- Không sửa CRM-005/007, không thêm field/model/JS/cron/API, không can thiệp `res.partner` UI hay `web.assets_backend`. 006 chỉ thay đổi Python. Không thao tác trực tiếp Production.
- Cần thực nghiệm trên bản sao Xinyang Production: Deal với Contact đã có Company cha; Company trùng VAT/tên khi Person chưa có parent; Contact Person vs Contact Company; non-empty/empty Phone/Email, avatar/logo, address/geo, các fields 007, quyền user và thông báo đồng bộ. **Không thay cho test Odoo thực.**

---

# CRM-006 — `sgt_crm_contact_push` 19.0.1.3.0 (Update_004)

## Update_004 — Ghi đè có kiểm soát + Geolocation (01/11/2026)

- Nút thủ công **Cập nhật Contact**: field native của Deal có giá trị mới được ghi đè lên Contact/Company nếu khác; các trường rỗng của Deal KHÔNG xóa dữ liệu Contact. Gồm Street, Street 2, City, State, ZIP, Country, Website, Job Position, Tax ID, Salesperson, Internal Reference; các field hồ sơ 007 vẫn đồng bộ có chọn lọc (đã ghi đè từ Update_002). Company nhận địa chỉ/tax/website mới. Logo chỉ cập nhật Company, **không ghi đè Person avatar**.
- Trigger tự động của **Create Contact** giữ `fill_empty` cho field native để tránh tự động sửa dữ liệu cũ; profile và Company logo như bản 003. Không sửa addon cũ `crm_sync_contact_odoo2`.
- Tags giữ nguyên tag cũ và thêm tag mới; không xóa; không đổi liên kết `parent_id` đang tồn tại; không tự đổi tên Person trừ logic sửa tên trùng. **Phone/Email chưa thêm mapping Update** vì chưa được phê duyệt riêng; bản cũ tạo lần đầu vẫn xử lý theo addon cũ.
- Khi bấm nút thủ công, nếu địa chỉ thay đổi hoặc chưa có tọa độ, và Street+City+Country đều đủ, thử tính mới bằng phương thức chuẩn `geo_localize()` của Odoo **chỉ khi module định vị hỗ trợ**. Không tự thêm API. Nếu không có địa chỉ đủ, chưa cài provider, hay geocoder thất bại, giữ dữ liệu Contact đã cập nhật nhưng ghi cảnh báo Geolocation trong thông báo/Chatter; không coi tọa độ 0 là tọa độ hợp lệ.
- Lỗi ghi một trường được xử lý theo savepoint; lưu tên field thất bại trong Chatter. Không cấp thêm quyền hay tự sửa dữ liệu ngoài nút/trigger.

**Kiểm tra offline:** `python tests/test_push_unittest.py`. Chưa thử tương tác thật trên máy chủ Odoo, chưa xác minh hiện trạng Production. Cần nghiệm thu trên bản sao Production trước khi cài.

**Thứ tự:** Backup → CRM-007 Update_003 (CSS và field) → CRM-006 Update_004 (đồng bộ + định vị) → nghiệm thu Contact, Company, Avatar, Address, Geolocation, CRM, Discuss. Không Uninstall.

---

# CRM-006 — `sgt_crm_contact_push` 19.0.1.2.0 (Update_003)

## Update_003: bảo vệ avatar Person và chỉ cập nhật logo Company (2026-10-31)

- Khi bấm **Cập nhật Contact** hoặc chạy trigger **Create Contact**: Contact Individual **không bị ghi `image_1920`**, bất kể Deal có logo. Người dùng được thay avatar Individual trực tiếp tại Contacts (CRM-007 Update_002).
- Đúng Company (Contact trực tiếp là Company hoặc Company cha của Individual) vẫn được đồng bộ `image_1920` từ CRM-005, ưu tiên `x_yp_logo_upload` rồi đến ảnh `x_image` dạng `data:image/...;base64,...`. URL thường không tự tải.
- Các field hồ sơ và Notes còn lại vẫn cập nhật vào cả Individual và Company như Update_002. Không thêm field/cron/JS/API; không thay đổi dữ liệu cũ.
- Nếu Individual từng bị ghi logo công ty vào avatar trước Update_003, avatar cũ giữ nguyên cho tới khi được thay thủ công. Không tự xóa hay tìm khôi phục ảnh cá nhân.
- **Thứ tự nâng cấp trên Demo 2:** CRM-007 Update_002 trước, sau đó CRM-006 Update_003. Sao lưu DB rồi Upgrade (không Uninstall).
- **Kiểm thử offline:** 61 unit tests (bao gồm logo Company mới/cũ/trực tiếp, avatar Person sau khi người dùng thay, chạy lại không phát sinh thay đổi). Chưa chạy thử trên Odoo thật; cần kiểm tra trên Demo 2 trước Production.

---

## Lịch sử: Update_002 (19.0.1.1.0)

## Update_002 — có gì mới (cần addon CRM-007 `sgt_contact_company_profile` cài TRƯỚC)
Nút **Cập nhật Contact** (và lần đầu bấm **Create Contact**) giờ còn đẩy **hồ sơ công ty + logo** từ Deal sang Contact, **cả Contact cá nhân lẫn Company cha** (Company cũ trùng Tax ID/tên, Company có sẵn của Contact, hoặc Company mới tạo).

| Deal | → Contact / Company | Quy tắc |
|---|---|---|
| Business Type, Main Market, Employee Size, Business Industries, 4 link (Zalo Group, Profile, Group URL, Post URL), Founded Year | cùng tên field (CRM-007) | **Đồng bộ gương**: mỗi lần bấm, Contact = Deal (đè giá trị cũ; trên Contact các ô này chỉ xem) |
| `referred` (Yellow Pages link) | `x_yp_listing_url` | như trên |
| Company Introduction (English) / Image Gallery / Partners | `x_yp_intro_en` / `x_yp_gallery_html` / `x_yp_partners_html` | như trên |
| Notes (`description`, giới thiệu tiếng Việt) | `comment` (Notes của Contact) | như trên — **đè** nội dung Notes cũ của Contact nếu Deal có giới thiệu |
| Logo: `x_yp_logo_upload` (ảnh tải lên ở CRM-005); không có thì `x_image` chỉ khi nó chứa ảnh nhúng `data:image/...;base64` | `image_1920` (ảnh đại diện) | thay ảnh đại diện của Contact và Company. **Link ảnh (http...) KHÔNG được tải về** (không gọi mạng). Deal không có logo → ảnh đại diện giữ nguyên |
| — | `x_sgt_crm_synced` = đã đồng bộ từ CRM | đặt trên Contact và Company; từ đó ảnh đại diện của chúng chỉ xem (CRM-007) |

* **Giá trị rỗng trên Deal không xóa Contact.** Muốn xóa trên Contact phải xóa tay ở Contact (hoặc bảo mình).
* Các ô gốc của Update_001 (địa chỉ, website, chức vụ, **Tax ID**, Salesperson, mã tham chiếu, Tags) **vẫn chỉ điền khi còn trống**, không đè.
* Chạy lại khi Deal không đổi: không ghi gì thêm, không thêm Log note ("Contact đã đủ thông tin…").
* Log note ở Deal chỉ ghi tên trường (Contact: …; Company "…": …), không ghi dữ liệu.
* Deal chưa cài CRM-005 (thiếu các field hồ sơ): các ô đó coi như rỗng, phần còn lại chạy bình thường.
* Một Company dùng chung nhiều Deal: lần bấm sau cùng thắng.

### Cài (theo thứ tự) trên Demo 2
1. (Nếu chưa) CRM-005 Update_032 → CRM-002 Update_025.
2. **CRM-007** `sgt_contact_company_profile` Update_001 → Install.
3. **CRM-006** `sgt_crm_contact_push` Update_002: thay thư mục, restart, Apps → Upgrade (có thêm phụ thuộc CRM-007, nên 007 phải có trước).
4. Thử: Deal đã có Contact và đã điền hồ sơ + logo → bấm **Cập nhật Contact** → mở Contact cá nhân: khối Company Profile + 3 hộp, ảnh đại diện = logo (chỉ xem); mở Company cha: khối Company Profile; Log note ở Deal liệt kê tên trường. Bấm lần 2: "Contact đã đủ thông tin".
5. Sửa một ô ở Deal (ví dụ Main Market) → bấm lại → Contact và Company đổi theo.
6. Deal mới chưa có Contact → bấm **Create Contact** (nút cũ) → Contact được đẩy tự động lần đầu.

### Chưa kiểm chứng trên Odoo thật (thêm)
* Html (Gallery/Partners/Introduction) được Odoo lọc khi ghi; Deal và Contact dùng cùng bộ lọc nên thường giống hệt, nếu không Log note sẽ liệt kê lại trường đó mỗi lần bấm (không hại gì).
* Ảnh logo lớn hơn 1920 px bị Odoo thu nhỏ khi ghi → mỗi lần bấm có thể ghi lại và liệt kê "Logo (avatar)".
* Test dùng ORM giả (58 test); chưa chạy trong Odoo thật.

---

# (Nội dung gốc Update_001)

## Làm gì
Sau khi bấm nút **Create Contact** (addon `crm_sync_contact_odoo2`) thành công, addon này **tự đẩy thêm dữ liệu của Deal sang Contact** (Odoo1). Không đụng đồng bộ Odoo2, không sửa addon cũ.

| Contact (res.partner) | Lấy từ Deal |
|---|---|
| Company (ô Company của Contact) | `partner_name` — dùng lại Company trùng Tax ID, rồi trùng tên (không phân biệt hoa thường, thừa dấu cách); **không có thì TẠO MỚI** Company |
| Street / Street 2 / City / ZIP / State / Country | cùng tên |
| Website | `website`, nếu trống thì `x_website` |
| Job Position | `function`, nếu trống thì `x_jobtitle` |
| Tax ID | `x_yp_tax_code` (CRM-005; không có CRM-005 thì bỏ qua) |
| Salesperson | `user_id` |
| Internal Reference | `x_getfly_id` (VN Odoo ID) |
| Tags | Tag của Deal; tạo Tag Contact trùng tên nếu chưa có; `Hunter`/`hunter` chỉ ra một Tag; **không bao giờ xóa Tag có sẵn** |
| Name | chỉ khi tên bị lặp cả cụm ("Mr. Chinh Mr. Chinh" → "Mr. Chinh"); đồng thời sửa Contact Name trên Deal nếu nó bị lặp giống vậy |

Quy tắc: **chỉ điền ô còn trống**, không đè dữ liệu đã có. Chạy lại bao nhiêu lần cũng không đổi thêm gì. Mỗi lần có thay đổi: một Log note trong Chatter của Deal ("Đã đồng bộ N trường vào Contact: …", chỉ ghi tên trường, không ghi dữ liệu).
Ảnh Contact: addon này KHÔNG đụng (addon cũ đã tự đặt).

## Cách bắt "bấm nút"
Addon cũ, khi kết thúc Create Contact thành công, ghi `x_groupname` / `x_getfly_id` lên Deal. Addon này ghi đè `crm.lead.write`: thấy một trong hai field đó được ghi và Deal đã có Contact thì chạy đồng bộ (trong savepoint; lỗi chỉ ghi log, không chặn nút cũ).
Nút phụ **"Cập nhật Contact"** (cạnh nút cũ, chỉ hiện khi Deal có Contact) chạy đúng phần đồng bộ này bằng tay — dùng để bù cho Contact tạo trước đây (ví dụ Contact 96).

## Không có
Không field mới (field do CRM-007 tạo), không model mới, không JS/CSS, không cron, không API, không đụng CRM-001/002/004/005.
Phụ thuộc: `crm`, `crm_sync_contact_odoo2`, `sgt_contact_company_profile` (từ Update_002).

## Cài / nâng cấp trên Demo 2
1. Sao lưu DB. Chép thư mục `sgt_crm_contact_push` vào addons_path, restart Odoo.
2. Apps → Update Apps List → "SGT CRM-006" → Install.
3. Thử: mở một Deal mới có tên công ty, địa chỉ, Tax Code (CRM-005), tag; bấm **Create Contact**; mở Contact → phải có Company, địa chỉ, website, Tax ID, Tags, Salesperson, Internal Reference; tên không còn lặp; Chatter Deal có Log note.
4. Bấm **Cập nhật Contact** trên Deal đó → thông báo "Contact đã đủ thông tin…".
5. Mở Deal cũ (ví dụ Khả Tâm / Contact 96) → bấm **Cập nhật Contact** → Contact được bổ sung.
6. Thử Deal không có tên công ty → Contact không có Company, các ô khác vẫn được điền.

## Chưa kiểm chứng trên Odoo thật
- Trigger dựa trên việc addon cũ ghi `x_groupname` / `x_getfly_id` SAU khi Contact đã gắn vào Deal (đọc từ Chatter production, chưa đọc mã addon cũ). Nếu không có Log note sau khi bấm Create Contact thì gửi ZIP `crm_sync_contact_odoo2` để chuyển sang chặn thẳng hàm của nút.
- Odoo 19 tự đồng bộ địa chỉ/Tax ID từ Company xuống Contact con: kết quả cuối có thể là dữ liệu của Company đã có sẵn (đúng hành vi chuẩn).
- Nếu `base_vat` bật và Tax Code sai định dạng: Tax ID không ghi được, các ô khác vẫn ghi, Log note ghi "Không ghi được: Tax ID".
- Chạy test: `python3 tests/test_push_unittest.py` (36 test, không cần Odoo).

## Mở rộng cho CRM-007
Thêm field mới trên Contact → thêm một dòng trong `models/push.py` (`LABELS`, `build_wanted`) và một dòng trong `_sgt_crm006_lead_data`.


## Update_008 (2026-11-11): GPS from CRM-005
See `UPDATE_008_NOTES.md`. No new Contact field, explicit button updates GPS.
