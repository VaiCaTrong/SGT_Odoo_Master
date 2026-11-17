# sgt_xinyang_welcome — UI-009 (trang đăng nhập) + UI-010 (app Home)

**1 module, 1 ZIP.** Phụ thuộc: `web`, `website` (Odoo 19). Phiên bản 19.0.1.11.0 (Update_020).

## Update_020 (17/11/2026) — Trang Match Making gộp cột 5 + cột 6
**Cài:** Upgrade trên DB đang ở Update_019 (19.0.1.10.0) hoặc Update_018, rồi Ctrl+Shift+R. Không có nhóm quyền hay trường mới.

- **Một con số, một danh sách:** trang Match Making gộp **cột 5 (Match Making)** và **cột 6 (Approved Match Making)**. Phần tóm tắt có tổng chung (cột 5 + cột 6), số của từng cột, kỳ trước, % so với kỳ trước. Bên dưới là **một danh sách Deal duy nhất**, mới nhất trước, mỗi thẻ có nhãn Stage; bộ lọc *Tất cả | Match Making · cột 5 | Approved Match Making · cột 6* (kèm số đếm) thu hẹp danh sách, con số tổng vẫn giữ nguyên.
- **Quy cách lọc = Dashboard cũ:** mỗi cột giữ đúng quy tắc của báo cáo tuần trong Management Dashboard (Deal đang ở Stage, ngày tính theo lần vào Stage đầu tiên trong Chatter, múi giờ Asia/Ho_Chi_Minh, cùng bộ lọc thời gian chung). Một Deal chỉ ở một Stage nên hai nhóm không trùng nhau, tổng chung = cột 5 + cột 6.
- Thẻ Deal, ảnh Evidence, quyền và bảo mật: giữ nguyên Update_019.
- Backend: `kpi/xinyang.py::mm_all_report`, chỉ số mới `mm_all` (tham số `col=all|mm|approved`); trang Tổng quan không chạy chỉ số này nên không chậm thêm. Các chỉ số `mm` / `approved_mm` vẫn còn cho Tổng quan.
- Kiểm tra: HTTP 8 kiểm tra mới (tổng = cột 5 + cột 6 = hai thẻ riêng, đúng tập Deal, sắp xếp, lọc cột, phân trang, `col` sai → 422, Sales chỉ thấy Deal của mình, không quyền → 403); Chromium thật (bộ lọc, tổng, lẫn hai cột trong một danh sách, chỉ Approved khi lọc cột 6).

## Update_019 (17/11/2026) — Trang Match Making: số đếm theo bộ lọc + danh sách Deal kèm thông tin CRM và ảnh Evidence
**Cài:** Upgrade trên DB đang ở Update_018 (19.0.1.9.0), rồi Ctrl+Shift+R. Không có nhóm quyền hay trường mới; không tạo trường nào trong CRM.

- **Trang Match Making (Dashboard > Match Making):** hai ô số đếm (Match Making, Approved Match Making) theo **bộ lọc thời gian chung**, giữ nguyên quy tắc của Update_018 / báo cáo tuần của Management Dashboard (Deal đang ở Stage, tính theo lần vào Stage đầu tiên trong Chatter). Bên dưới là **danh sách Deal** (nút chuyển Match Making | Approved Match Making, mỗi trang 10 Deal).
- **Mỗi Deal là một thẻ:** tên Deal, Stage, thời điểm vào MM / được duyệt, **thông tin trong CRM**: Công ty (`partner_name`), Người liên hệ (`contact_name`) + chức vụ (`function`), Điện thoại, Email, Website, Địa chỉ (street / city / state / country), Phễu (`sgt_crm002_sale_funnel_id`, nếu rỗng thì `sgt_crm002_funnel_id`), Nguồn, Thẻ, Sales, Ngày tạo, Ghi chú CRM (`description`, chỉ chữ, tối đa 280 ký tự); riêng Approved MM thêm "Duyệt bởi / lúc" (`x_mm_approved_by / _at`). Link **nhóm Zalo** (`x_url_zalo_group`, chỉ https://…zalo.me) và **Mở Deal trong CRM**. Chỉ đọc các trường đã có sẵn; trường nào DB không có thì bỏ qua, không tạo thêm.
- **Ảnh MM · Evidence:** đọc từ trường HTML `x_yp_evidence_html` (như báo cáo tuần của Dashboard). Hiện ảnh nhỏ (360 px) ngay trong thẻ, **bấm để xem ảnh lớn (1600 px)**, mũi tên ←/→ để chuyển ảnh, Esc để đóng. Deal không có ảnh ghi "Chưa có ảnh Evidence".
- **Điểm khác Dashboard v2.3.9 (quan trọng):** trình soạn thảo Odoo 19 ghi ảnh dạng `/web/image/5473-fc173dfd/image.png?access_token=…` (có `-mã kiểm` sau id). Bộ nhận dạng của Dashboard v2.3.9 chỉ chấp nhận `/web/image/ir.attachment/<id>/datas` và `/web/image/<id>` nên sẽ bỏ qua **cả 21 ảnh** của 29 Deal thật (đã đối chiếu trên xinyang.sge.vn ngày 17/11/2026); bản này nhận dạng cả dạng có mã kiểm, dạng `ir.attachment/<id>/datas`, `/web/content/<id>` và ảnh dán trực tiếp `data:image/…;base64`. Ảnh nằm ngoài Odoo (https://nơi-khác) **không được tải**, thẻ ghi rõ "n ảnh nằm ngoài Odoo… không tự tải".
- **Quyền:** ảnh đọc bằng **quyền của chính người xem** (route `/sgt_home/kpi/evidence`, cần nhóm Dashboard Viewer hoặc Settings Administrator): Sales chỉ thấy Deal và ảnh của Deal mình; ảnh trỏ tới tệp của Deal người khác bị Odoo từ chối (thẻ hiện "Không tải được ảnh"). Không có link công khai, không dùng quyền nâng cao, không ghi gì. Ảnh được thu nhỏ trên máy chủ (Pillow, JPEG; PNG trong suốt được đặt lên nền trắng), trình duyệt giữ đệm 10 phút.
- **An toàn dữ liệu CRM:** mọi chữ lấy từ CRM đều qua `esc()`; link chỉ nhận `https://…zalo.me` (Zalo) và `http(s)` (website); `javascript:` bị bỏ; mô tả CRM bỏ thẻ HTML, `script`, `style`.
- **Kiểm tra:** 27 kiểm tra HTTP trên Odoo 19 thật (admin / Sales / không quyền / chưa đăng nhập: thông tin CRM, ảnh nhỏ & lớn, ảnh `data:`, PNG trong suốt, ảnh trỏ sang Deal người khác bị chặn, ảnh ngoài Odoo bị bỏ, tham số xấu), 22 kiểm tra giao diện trên Chromium thật (ảnh tải đủ, mở / chuyển / đóng ảnh lớn, đổi EN / VI, số trang MM = số ở tổng quan, 420 px không tràn ngang, dữ liệu CRM chứa HTML không chạy), kiểm tra bộ lọc đường dẫn / Zalo / website.
- **Chưa kiểm chứng:** Dashboard Viewer thật là Sales trên production (chỉ thử Sales giả lập); số lượng và dung lượng ảnh nhiều hơn 21 ảnh hiện có; so số đếm với Management Dashboard hiện tại cùng một kỳ.

## Update_018 (17/11/2026) — Dashboard trong Home: bộ lọc thời gian chung, trang tổng quan 4 chỉ số, 4 trang con
**Cài:** Upgrade trên DB đang ở Update_017 (19.0.1.8.0). **Phải bấm Upgrade** (có nhóm quyền mới "Dashboard Viewer" và 4 trường cài đặt mới), rồi Ctrl+Shift+R. Không cần cài thêm thư viện (dùng `requests` có sẵn của Odoo).

- **Menu "Dashboard"** trên đầu Home (cạnh Heat Map), mở trang `/sgt_home/kpi` thay cho phần thân Home. Chỉ hiện cho người trong nhóm **Home > Dashboard Viewer** (Home Manager tự có, Settings Administrator luôn xem được). Gọi thẳng đường dẫn mà không có quyền: 403 (chưa đăng nhập: 302/401). Cấp quyền ở **Home > Settings > "KPI Dashboard access"** hoặc Settings > Users > Access Rights > Home > Dashboard.
- **Bộ lọc thời gian dùng chung** (giống Dashboard): Ngày / Tuần / Tháng / Toàn thời gian + chọn ngày + mũi tên lùi/tiến + "Hôm nay" + làm mới. Tuần thứ Hai–Chủ nhật, mọi ngày tính theo giờ Việt Nam; so với kỳ trước (tuần trước, tháng trước, hôm qua; Toàn thời gian không có kỳ trước). Màu so sánh: xanh khi ≥ 0 %, đỏ khi < 0 %, "N/A" khi kỳ trước bằng 0 mà kỳ này > 0 hoặc không có kỳ trước. Kỳ chọn được nhớ trong phiên.
- **Trang tổng quan:** 4 thẻ như Dashboard: **GB · Bài post đã duyệt**, **Content · Đã duyệt**, **Data · KH tiềm năng**, **Match Making** (kèm Approved Match Making). Mỗi thẻ lỗi riêng: một chỉ số chưa xác minh được thì chỉ thẻ đó hiện lý do, các thẻ khác vẫn có số.
- **4 trang con** (thẻ trên cùng, mỗi chỉ số một tab): GB (Tổng / Đã duyệt / Không được duyệt / Chưa kiểm tra); Content (Tổng / Chưa duyệt / Đã duyệt / Đã lưu trữ / Từ chối, góc nhìn theo tháng, theo ngày, theo tác giả); Data (số KH tiềm năng, kỳ trước, Lead mới vào phễu Data, danh sách Deal bàn giao, phân trang); Match Making và Approved Match Making (số lượng, kỳ trước, danh sách Deal, phân trang, số Deal chưa có lịch sử Tracking nên không được tính).
- **Nguồn số liệu (bản chuyển từ Management Dashboard, cùng quy tắc):**
  - *Data · KH tiềm năng* = Deal **lần đầu** được bàn giao vào Match Making › 1.Opportunity (log note "Bàn giao Deal (CRM-002)", ngày của log note). Một Deal chỉ tính một lần, ở kỳ bàn giao đầu tiên.
  - *Match Making / Approved Match Making* = Deal **đang** ở Stage 5.Match Making / 6.Approved Match Making, tính theo **lần đầu** đổi Stage từ Stage khác vào Stage đó (Chatter tracking `stage_id`). Đổi tên Stage cũ (5.MM, 8.Match Making, 9.Approved..., Won) được nhận diện; Deal tạo thẳng ở Stage hoặc chưa có tracking không bị đoán ngày mà được đếm riêng.
  - Các số này đọc bằng **quyền và record rule của chính người đang đăng nhập**: Sales chỉ đếm Deal mình được thấy.
  - *GB* (Publishing History) và *Content* đọc từ **social360** (SGT, Project XINYANG), chỉ đọc.
- **Điểm khác Dashboard cần biết (1): lịch sử Stage.** Odoo 19 chỉ cho Settings Administrator đọc Chatter tracking. Để Sales cũng xem được Match Making của chính mình, phần lịch sử Stage được đọc bằng một cổng **nâng quyền, chỉ đọc, giới hạn đúng 4 model và đúng phương thức** (`mail.message`, `mail.tracking.value`, `ir.model.fields` chỉ `search_read`; tên phễu chỉ `read_group`), và **chỉ cho các Deal mà cổng quyền của chính người dùng đã đọc được**. Không ghi, không trả nội dung ghi chú; chỉ ngày đổi Stage đi vào kết quả.
- **Điểm khác Dashboard cần biết (2): kết nối social360.** Dashboard đăng nhập social360 bằng tài khoản của từng người; trong Odoo không có mật khẩu để dùng lại, nên GB và Content dùng **một tài khoản dịch vụ chỉ-đọc**. Cách nhập: **Home > Settings > "KPI Dashboard · social360 connection"** (URL, database, login, API key). Bốn trường chỉ Settings Administrator thấy và sửa (kiểm tra ở mức trường, Home Manager và user thường nhận AccessError), khóa không bao giờ gửi xuống trình duyệt hay hiện trong kết quả. Máy chủ Xinyang phải ra được địa chỉ social360 qua HTTPS. **Chưa nhập thì thẻ GB và Content hiện "Chưa kết nối social360"**, không hiện số đoán. GB/Content là số của cả Project XINYANG (mọi người có quyền Dashboard thấy cùng số).
- **Cache:** 60 giây theo người dùng (Data/MM) và theo kết nối (GB/Content); nút làm mới bỏ cache.
- **Kiểm tra:** hợp đồng (+23 kiểm tra mới: quyền, không ghi, khóa không lộ, cổng nâng quyền giới hạn, giao diện); test thuần Python cho bộ lọc kỳ (đầu/cuối tuần, tháng 12 → 1, năm nhuận, so sánh); **social360 giả** có dữ liệu mẫu (GB 12/6/3/3, Content 4/1/1/2/1 đã tính tay) qua cuộc gọi JSON-RPC thật bằng HTTP, lỗi Cloudflare 520, trả HTML, sai khóa, mất kết nối, dữ liệu Content không khớp; **Odoo 19 thật trong sandbox** (Upgrade, nhóm quyền, ma trận truy cập, dữ liệu CRM-002 mẫu có log note + Chatter tracking, user Sales so với admin: Deal của người khác không lọt vào số, các biên tuần 00:00/23:59 giờ Việt Nam, Deal vào Match Making hai lần, đổi tên Stage, bàn giao lần hai), và giao diện Chromium trên Odoo thật (menu theo quyền, 4 thẻ, bộ lọc, 4 trang con, đổi EN/VI, màn Settings). Đã phá cố ý 5 chỗ trong logic tính (bỏ lọc "lần bàn giao đầu", không bỏ qua đổi tên Stage, lấy lần vào muộn nhất, lệch tuần 1 ngày, kỳ trước = kỳ này), đều bị bắt.
- **Chưa kiểm chứng:** social360 thật (không có tài khoản và mạng từ sandbox; đã mô phỏng giao thức và các lỗi), dữ liệu CRM-002 / Chatter production thật (sandbox dùng trường giả lập `sgt_crm002_*`), tốc độ với số lượng Deal / log note lớn (có giới hạn an toàn 5000 log note, 10000 Deal; vượt thì báo lỗi, không cắt cụt), khớp từng con số với Dashboard hiện tại trên cùng dữ liệu thật.

## Update_017 (16/11/2026) — sửa lề thật trên Odoo, nút bo tròn, animation, Potential Map, cấp quyền Heat Map ngay trong Home > Settings
**Cài:** Upgrade trên DB đang ở Update_016 (19.0.1.7.0). **Phải bấm Upgrade** (Apps > "XINYANG | UI-009 Login + Home" > Upgrade): nếu chỉ thay file mà không Upgrade thì nhóm "Heat Map Viewer" chưa có trong DB (Home vẫn mở Heat Map được cho Settings Administrator, nhưng không gán được cho ai). Sau đó Ctrl+Shift+R.

- **Lề hai bên (lỗi Update_016):** trên Odoo thật, Bootstrap ép `.container` tối đa 1320 px nên bố cục rộng không có tác dụng (ảnh đo được 1319 px). Nay bỏ giới hạn đó: ở 1863 px nội dung rộng 1751 px, lề 56 px mỗi bên; 1920 px lề 58 px (94%); 1366 px lề 41 px.
- **Nút bo tròn:** "Get in touch", "Explore solutions", "View product catalog", nút gửi form, hai mũi tên hero, nút Add/Edit của Home Manager bo 10-12 px; các nhãn lọc sản phẩm thành viên thuốc; thẻ nổi và thẻ giải pháp bo nhẹ để hài hòa.
- **Animation (vừa đủ):** vào trang: chữ hero hiện lần lượt, ảnh hero trượt vào, gạch đỏ dưới "every space." được vẽ ra, hai thẻ nhỏ bên ảnh lơ lửng nhẹ (±7 px). Cuộn trang: các khối (số liệu, giới thiệu, thẻ giải pháp, lĩnh vực, sản phẩm, quy trình, liên hệ) hiện dần từ dưới lên, các thẻ cùng lúc xuất hiện nối nhau cách 70 ms. Rê chuột: gạch đỏ dưới menu, nút nhấc lên và mũi tên "bay", thẻ nhấc lên. Mở sản phẩm: nền mờ dần, khung nổi lên. Chuyển Home <-> Heat Map: mờ dần. Tắt hết khi hệ điều hành bật "giảm chuyển động"; trình duyệt cũ không có IntersectionObserver thì không ẩn gì cả; in trang thì hiện đủ.
- **Potential Map / Heat Map báo lỗi "Invalid field 37 on res.partner" (lỗi Update_016):** hàm đọc theo danh sách id (`read`) gọi sai cách trên ORM (JSON-RPC gửi id trước, ORM gọi `browse(ids).read(fields)`), làm id bị hiểu thành tên trường. Đã sửa trong bộ chuyển `heatmap/adapter.py`. Mọi lỗi bất ngờ khác trong phần đọc dữ liệu nay hiện thành thông báo "lỗi nội bộ" trong bản đồ (kèm dòng ghi trong nhật ký máy chủ), không còn trang lỗi 500.
- **Phân quyền Heat Map ngay trong Home > Settings:** khối **"Heat Map access"** (chỉ Settings Administrator thấy và sửa): ô "People who can open the Heat Map" để thêm / bớt người (chính là tích / bỏ nhóm Home > Heat Map Viewer), và dòng "Also allowed automatically" liệt kê Home Manager (được quyền theo vai trò). Nếu module chưa Upgrade, khối này hiện cảnh báo. Cách cũ vẫn dùng được: Settings > Users > (người dùng) > Access Rights > Home > Heat Map.
- **Cách đọc quyền (không đổi):** nhóm Heat Map Viewer chỉ cho phép mở bản đồ; deal và contact nào hiện ra vẫn theo quyền CRM và record rule của chính người đó (Sales chỉ thấy deal của mình; người không có quyền CRM nhận thông báo từ chối).
- **Kiểm tra:** ngoài bộ test giả lập (hợp đồng, parity Dashboard, Chromium + OWL cho Home, lề + nút, animation, Heat Map; lớp ORM giả nay mô phỏng đúng `read` trên recordset và tên trường sai), lần này đã chạy **trên Odoo 19 thật trong sandbox** (Python 3.13, PostgreSQL 16, DB mới + CRM + base_geolocalize, trường x_yp_* tạo thủ công): cài mới, Upgrade, nhóm và privilege "Heat Map" trong Settings > Users, ma trận truy cập (khách 302/401, user thường 403, Viewer, Home Manager, Settings Administrator), record rule của Sales, 4 route dữ liệu với ORM thật (Deals 4 điểm, Potential 3 điểm, logo, hồ sơ), khối cấp quyền (đọc / ghi chỉ admin; Home Manager và user thường bị AccessError), và giao diện thật bằng Chromium (Bootstrap thật, nút, Heat Map, màn Users, màn Home > Settings). Đã phá cố ý 13 chỗ mới, đều bị bắt.
- **Chưa kiểm chứng:** dữ liệu production thật (trường x_yp_* của CRM-005 trong sandbox là bản tạo tay), ảnh nền bản đồ (sandbox không ra Esri/OSM), bản ZIP trên server của anh.

## Update_016 (16/11/2026) — lề rộng, nút EN | VI có nền, Heat Map trong Home (chỉ người có quyền)
**Cài:** Upgrade trên DB đang ở Update_015 (19.0.1.6.0). Có thêm 1 nhóm quyền (Heat Map Viewer), nên Upgrade là bắt buộc; sau đó Ctrl+Shift+R.

- **Lề rộng (phương án C):** nội dung Home dùng khoảng 94% chiều ngang màn hình (lề mỗi bên 3% màn hình), thay cho khung cố định 1310 px. Trần 2400 px để màn hình siêu rộng không bị kéo giãn quá mức. Màn hình ≥1600 px: lưới sản phẩm 4 cột; ≥1500 px: ảnh hero lớn hơn và nhãn "1996" đi theo ảnh. Máy tính bảng và điện thoại (≤1220 px, ≤700 px) giữ như cũ.
- **Nút EN | VI:** vẫn là một nút chung của Home, nay nằm trên nền xanh nhạt dạng viên thuốc, ngôn ngữ đang chọn là nút đặc màu xanh, chữ trắng (độ tương phản ≥ 4.5:1). Nút này cũng đổi ngôn ngữ của Heat Map.
- **Heat Map (XINYANG MAP) trong Home:** menu trên cùng có mục **Heat Map** (chỉ hiện cho người có quyền). Bấm vào thì bản đồ thay cho phần thân trang Home (khung đầy chiều cao còn lại, menu Home vẫn ở trên); bấm bất kỳ mục menu khác thì quay về Home và cuộn tới mục đó. Đổi EN/VI thì bản đồ đổi ngôn ngữ ngay, không tải lại và không mất bộ lọc / vị trí.
- **Quyền:** Settings > Users > (người dùng) > Access Rights > **Home** > **Heat Map Viewer**. **Home Manager** tự có quyền này; **Settings Administrator** luôn xem được. Người dùng nội bộ bình thường không thấy mục menu và gọi thẳng `/sgt_home/map` hoặc các đường dữ liệu đều bị chặn ở máy chủ (403; chưa đăng nhập thì chuyển về trang đăng nhập hoặc 401).
- **Dữ liệu:** bản đồ đọc **trực tiếp từ Odoo này** bằng chính tài khoản đang đăng nhập (quyền và record rule của người đó áp dụng, không dùng sudo, không ghi). Phần tính toán là bản chuyển nguyên từ Management Dashboard (Deals + Contacts + Potential), đã kiểm chứng cho ra cùng dữ liệu với Dashboard trên cùng bộ dữ liệu mẫu. Đây là **bản sao thứ hai** của bản đồ (Dashboard vẫn còn bản của nó); sau này gỡ Dashboard thì Home là bản duy nhất. Ảnh nền bản đồ lấy từ Esri / OpenStreetMap (không qua proxy của Dashboard), máy người dùng cần ra được internet.
- **Kiểm tra:** hợp đồng (security, route, không sudo/ghi, file đủ), parity Dashboard với bản chuyển, 29 kiểm tra Chromium + OWL cho Heat Map (hiện/ẩn theo quyền, khung bản đồ, đổi ngôn ngữ, quay về Home, điện thoại), 23 kiểm tra bố cục + nút EN | VI ở 390 / 1024 / 1366 / 1440 / 1680 / 1920 / 2560 px, và các bộ cũ vẫn đạt. Đã phá cố ý 16 chỗ (bỏ quyền ở máy chủ, bỏ kiểm tra ở nút, trả lại khung 1310 px, bỏ đồng bộ ngôn ngữ, cho sudo / ghi...), đều bị bắt.
- **Chưa chạy trên Odoo thật:** Upgrade, giao diện gán nhóm quyền, các route trong Odoo thật (kiểm chứng bằng bộ giả lập), ảnh nền bản đồ (sandbox không ra được Esri/OSM), khác biệt nhỏ giữa ORM và JSON-RPC với dữ liệu thật.

## Update_015 (16/11/2026) — ảnh cố định + nhiều ảnh, Home > Settings, khu "Lĩnh vực ứng dụng", sửa chữ đen trên nền xanh
**Cài:** Upgrade trên DB đang ở Update_014 (19.0.1.5.0) hoặc Update_013. Có thêm 2 model (ảnh phụ, cài đặt), nên Upgrade là bắt buộc (không chỉ tải lại trang).

- **Cửa sổ sản phẩm:** ảnh và dãy ảnh nhỏ nằm cố định bên trái, chỉ phần chữ bên phải cuộn; ảnh sát mép trên khung. Điều hướng sản phẩm chuyển xuống **thanh cố định ở chân khung** ("PREVIOUS PRODUCT <tên>", vị trí "3 / 12", "NEXT PRODUCT <tên>"). Nút đổi ảnh là nút xanh navy ở hai đầu dãy ảnh nhỏ, không còn nút nào đè lên ảnh, nên không lẫn với nút đổi sản phẩm. Phím ← → vẫn đổi sản phẩm, Esc đóng. Điện thoại (dưới 700 px): ảnh nằm trên chữ, không cố định.
- **Nhiều ảnh cho một sản phẩm:** form sản phẩm có khối **"Extra images"** (danh sách sửa tại chỗ, kéo biểu tượng tay cầm để đổi thứ tự, bấm ô ảnh để tải lên; mỗi dòng một ảnh). Ảnh chính (trường Product image) luôn là ảnh đầu tiên, ảnh phụ theo sau. Sản phẩm chỉ có **1 ảnh thì ẩn dãy ảnh nhỏ, hai nút, nhãn "1 / n" và thanh tiến trình** (ảnh vẫn cố định). Sản phẩm không có ảnh nào hiện logo Xinyang.
- **Home > Settings** (menu ngang hàng Products / Banners / Highlights; chỉ Home Manager và Settings Administrator thấy và sửa): một bản ghi cài đặt chung cho cả Home, tạo sẵn khi cài (noupdate). Cài đặt đầu tiên **"Change product images automatically"**: Off / Every 10 seconds / **Every 30 seconds (mặc định)** / Custom. Chọn Custom thì gõ số giây tự do (cho phép 3 đến 3600; ngoài khoảng này Odoo báo lỗi khi lưu). Tự chuyển ảnh dừng khi rê chuột vào ảnh hoặc khi tab phím đang ở trong khối ảnh, chạy lại khi rời đi, bấm ảnh nhỏ thì tính lại từ đầu; tắt hẳn khi người dùng bật "giảm chuyển động" của hệ điều hành. Cài đặt mới trong tương lai chỉ cần thêm trường vào model `sgt.home.setting` và dòng vào form `view_sgt_home_setting_form`. Mọi tài khoản nội bộ đọc được bản ghi này (Home cần đọc), nên không lưu thông tin nhạy cảm ở đó. Không ai tạo thêm hoặc xóa được bản ghi (chỉ sửa).
- **Khu "Lĩnh vực ứng dụng":** tiêu đề căn giữa, bên dưới 4 thẻ nhỏ có biểu tượng (4 cột trên laptop, 2 cột trên máy tính bảng, 1 cột trên điện thoại). Nội dung chữ giữ nguyên. Thẻ chỉ đổi màu viền khi rê chuột, không phải liên kết (như bản cũ).
- **Sửa lỗi màu chữ:** Odoo ép màu đen cho h1-h6 nên tiêu đề khu "Lĩnh vực ứng dụng" và "Partnering on projects" (nền xanh đậm) bị chữ đen. Nay đặt chữ trắng tường minh. Bộ kiểm tra có thêm CSS giả lập kiểu Odoo ép màu đen để bắt lại lỗi này.
- **Dữ liệu:** 2 model mới `sgt.home.product.image` và `sgt.home.setting` (quyền đọc cho mọi tài khoản nội bộ; ghi theo Home Manager / Settings Administrator như sản phẩm). Không đổi dữ liệu sản phẩm cũ.
- Sau Upgrade: Ctrl+Shift+R. Người được gán Home Manager cần đăng nhập lại hoặc tải lại trang để thấy mục Settings.
- Kiểm tra: 281 kiểm tra hợp đồng, 47 kiểm tra Chromium + OWL thật cho ảnh/chân khung/tự chuyển/Applications/màu tiêu đề (cộng 55 kiểm tra Home và 52 kiểm tra EN/VI cũ vẫn đạt), logic cài đặt chạy thử với Odoo giả, thử phá cố ý 12 chỗ (10 bị bắt, 2 chỗ không đổi hành vi). **Chưa chạy trên Odoo thật:** Upgrade, form "Extra images", menu Settings, `/web/image/.../128x128` của ảnh phụ.
- Hạn chế: khung chọn tệp của Odoo chỉ chọn một ảnh mỗi lần, nên thêm nhiều ảnh phải thêm từng dòng.

## Update_014 (15/11/2026) — chuyển ngôn ngữ EN/VI, nội dung chi tiết sản phẩm, sửa chữ chồng nhau ở hero
**Cài:** Upgrade trên DB đang ở Update_013 (19.0.1.4.0) hoặc dòng 1.1.x. Có thêm tệp `i18n/vi.po` và `static/src/home/i18n.js`.

- **Sửa lỗi chữ chồng nhau** (ảnh bạn gửi: dòng "EXPLORE SOLUTIONS 01 Acoustics..." đè lên câu "For MEP contractors..."): hero và khung nội dung hero trước đây có chiều cao cố định (630 / 524 px), màn hình rộng làm tiêu đề lớn tràn xuống. Nay chiều cao tự giãn theo nội dung. Đã đo ở 10 kích thước (1920x1080 đến điện thoại 390 px), cả tiếng Anh và tiếng Việt: không còn chồng.
- **Chuyển ngôn ngữ:** nút **EN / VI** ở thanh đầu trang. Mặc định tiếng Anh. Lựa chọn được nhớ trên trình duyệt (localStorage; bị chặn thì vẫn chuyển được, chỉ không nhớ). Chuyển ngôn ngữ khi cửa sổ sản phẩm đang mở thì cửa sổ vẫn mở đúng sản phẩm đó.
  - Chữ cố định của trang (menu, tiêu đề, nút, form, chân trang, nhóm sản phẩm...) lấy từ `static/src/home/i18n.js`.
  - Tên, phụ đề và nội dung sản phẩm lấy từ Odoo theo ngôn ngữ đã chọn (`context.lang`). Nếu Odoo không đọc được tiếng Việt thì tự quay về tiếng Anh, trang không bị trắng.
  - Không dịch: banner và Highlights (Settings admin tự nhập), nội dung thư nháp gửi nhà sản xuất (giữ tiếng Anh vì nhà sản xuất ở Trung Quốc), poster hình ảnh.
- **Nội dung chi tiết sản phẩm** (hiện khi bấm vào sản phẩm): trường **Product content** (`description`) giờ nằm trong khối riêng, rộng hết form, tên "Content shown when a visitor opens this product". Nhập tay cho từng sản phẩm mới; mỗi dòng một tính năng là đẹp nhất (xuống dòng được giữ nguyên). Không bắt buộc nhập; sản phẩm không có nội dung thì cửa sổ không hiện khối trống.
  - 6 sản phẩm mới của Update_013 (BD1, FASU, HVAC Noise, Damper Range, XY-WE, XYYL) trước đây chưa có nội dung; nay đã có, chỉ dựa trên chữ có trên poster và catalog. Dữ liệu mẫu là noupdate nên 6 sản phẩm đã có sẵn giữ nguyên nội dung bạn đã sửa; 6 sản phẩm mới chỉ được tạo trong lần Upgrade này nên nhận nội dung mới.
  - **Bạn cần kiểm tra lại các nội dung mẫu** trước khi công khai (đặc biệt "giảm đến 50% thời gian lắp đặt", lấy từ poster FASU).
- **Dịch nội dung sản phẩm sang tiếng Việt:** tên, phụ đề, nội dung là trường dịch được. Cách làm: (1) vào **Settings > Languages**, bật **Vietnamese / Tiếng Việt** (Activate) nếu chưa có; (2) mở sản phẩm, bấm biểu tượng quả cầu cạnh trường để nhập bản tiếng Việt. `i18n/vi.po` đã có sẵn bản dịch cho 12 sản phẩm mẫu và được nạp khi cài ngôn ngữ Việt hoặc khi Upgrade (nếu tiếng Việt đã bật). Nếu một sản phẩm chưa có bản tiếng Việt thì Home hiện bản tiếng Anh của sản phẩm đó.
- Nhãn trường đổi: bỏ chữ "(English)" ở tiêu đề / phụ đề, đổi "Description / notes" thành "Product content".
- Kiểm tra: 258+ kiểm tra hợp đồng (mọi chuỗi trong template có bản dịch, msgid của vi.po khớp tuyệt đối với dữ liệu mẫu) và 51 kiểm tra Chromium + OWL thật cho chuyển ngôn ngữ (kể cả tiếng Việt không đọc được, localStorage bị chặn, mở cửa sổ rồi đổi ngôn ngữ) + 55 kiểm tra cũ vẫn đạt. Đã thử phá cố ý 8 chỗ, đều bị bắt. **Chưa chạy trên Odoo thật:** việc nạp `vi.po` cho dữ liệu mẫu và việc đọc `context.lang=vi_VN` cần bạn xác nhận trên demo.

## Update_013 (15/11/2026) — bản gộp: nền Update_010 + giao diện concept + phân quyền của ZIP 1.1.x
**Đối tượng cài:** nâng cấp (Upgrade) trên DB đang chạy dòng ZIP 1.1.x (production). KHÔNG cài đè lên DB đã cài bản Update_010 gốc (19.0.1.2.0) hoặc Update_011 (19.0.1.3.0): hai bản đó có model sản phẩm khác (nhóm chữ tự do, ghi chú, màu) và nhóm quyền khác tên. DB demo nào đang ở 19.0.1.2.0 / 19.0.1.3.0 thì **gỡ module rồi cài lại** (hoặc dùng DB mới).

- **Giao diện:** Home dùng bố cục concept (hero, năng lực, giải pháp, sản phẩm có bộ lọc, liên hệ). Lấy từ Update_010: 12 poster sản phẩm, nút **+ Add product** và nút **Edit** trên từng thẻ (chỉ Manager/Admin), cửa sổ xem poster có mũi tên và phím Esc / ← → (đóng thì trả focus về nút đã mở), ảnh thu nhỏ 560 px ở lưới (tải nhanh), dải thông tin Saigon Trade. Banner và Highlights vẫn hiện ở mục "Company highlights".
- **Phân quyền (giữ nguyên của ZIP 1.1.x):** Settings > Users > Access Rights > **Home** > **Home Manager**. Settings Administrator mặc định quản lý được. Người dùng nội bộ thường chỉ xem. Menu **Home > Products** và các nút Add/Manage/Edit chỉ hiện với Home Manager hoặc Settings Administrator; quyền được chặn ở máy chủ (ir.model.access). Banners/Highlights/Website switch vẫn chỉ Settings Administrator.
- **Trường sản phẩm (giữ của ZIP 1.1.x):** tên, mã, phụ đề, mô tả, nhóm (Air distribution / Acoustic solutions / Fire & smoke control / Other), ảnh, thứ tự, hiện/ẩn, ghi chú nội bộ. Không thêm hay bớt trường nào.
- **Dữ liệu mẫu:** 6 poster của ZIP 1.1.x trùng 6 trong 12 poster của 010 nên giữ nguyên 6 bản ghi cũ (cùng xml-id, **không đổi, không trùng**) và chỉ thêm 6 thẻ mới: BD1 Butterfly Valve, FASU Ceiling Ventilation, HVAC Noise-Control Solutions, Ventilation Damper Range, XY-WE Linear Slot Diffuser, XYYL Circular Tube Silencer. Dữ liệu mẫu là noupdate: chỉnh sửa của bạn không bị ghi đè khi Upgrade; thẻ đã **xóa** hẳn sẽ được tạo lại ở lần Upgrade sau (muốn ẩn hãy dùng công tắc Show on Home).
- **Giữ từ bản sửa trước:** sửa lỗi `Service user is not available` và `this.el` (Update_012), sửa Search View cho Odoo 19, chuyển hướng "/" -> đăng nhập, đăng nhập xong vào Home.
- **Đã dọn:** 3 ảnh PNG poster không còn dùng (aluminum, eggcrate, smoke) và `home.scss` thừa; quyền tệp của 2 logo đặt lại thành 644.
- Sau Upgrade: Ctrl+Shift+R. Người được gán Home Manager cần đăng nhập lại hoặc tải lại trang.
- Kiểm tra: 238+ kiểm tra hợp đồng (đã thử phá cố ý 15 chỗ, đều bị bắt) và 55 kiểm tra trên Chromium + OWL thật (service chặt như Odoo 19; ba trường hợp quyền: Manager, Settings Admin, người thường). Chưa chạy trên Odoo thật.
- Lưu ý còn lại: thư mục static của module (catalog PDF 13,6 MB, poster hero) là công khai với ai biết đường dẫn; ô "Internal notes" mọi tài khoản nội bộ đều đọc được qua RPC nên không ghi thông tin nhạy cảm.

## Update_012 (15/11/2026) — sửa lỗi "Service user is not available" khi mở Home
- **Lỗi bạn gặp** (OwlError ... `Service user is not available` tại `SgtHome.setup`): `static/src/home/home.js` gọi `useService("user")`, mà Odoo 19 không có service tên "user". Đã sửa: dùng `import { user } from "@web/core/user"` rồi `user.hasGroup(...)`.
- **Lỗi thứ hai cùng tệp** (sẽ nổ ngay khi bấm menu trên Home hoặc thẻ "Solutions"): `this.el` không tồn tại trong OWL 2. Đã sửa: dùng `useRef("home")` (template đã có `t-ref="home"`).
- Dọn nhỏ trong `home.xml`: bỏ class tĩnh `active`/`selected` và `aria-expanded="false"` tĩnh đang trùng với phần động.
- **Giữ nguyên toàn bộ bố cục** (concept.css, poster, catalog, màn hình, quyền, model, chuyển hướng login → Home, bản sửa Search View). Không đổi model/dữ liệu nên chỉ cần Upgrade.
- Kiểm tra: tái hiện đúng lỗi trên tệp cũ bằng Chromium + OWL thật (service chặt như Odoo 19); tệp mới chạy 31 kiểm tra (hero, lọc, menu, mở/đóng chi tiết, form email, nút Manage chỉ cho Manager/Admin, điện thoại 390px, không lỗi console); thử phá cố ý thì bị bắt. Chưa chạy trên Odoo thật.
- Sau Upgrade nhớ Ctrl+Shift+R (assets cũ nằm trong cache trình duyệt).

## Search View compatibility hotfix for Odoo 19 (15/11/2026)
- Corrects `views/home_product_views.xml`: removes legacy `expand`/`string` attributes from the Search View's `<group>`. This fixes the `Invalid view sgt.home.product.search definition` upgrade error reported at XML record line 50.
- Removes `string` on `<search>` roots in Products, Banners and Highlights to align with Odoo 19 search architecture rules.
- Preserves `group_by: category`, Show/Hidden filters, products, banners, settings, redirects and ACLs.
- Manifest version and Update_011 release identity are unchanged; use this ZIP instead of the previous Update_011.
- Offline contract checks are NOT a substitute for installing on a live Odoo 19 server.

## Bổ sung quyền Administrator trong Update_011 (bản thay thế trước cài đặt)
- **Settings Administrator** (`base.group_system`) mặc định quản lý được **Home > Products**, bao gồm thêm, sửa, ẩn/hiện, sắp xếp và xóa sản phẩm. Không cần gán thêm Home Manager cho tài khoản này.
- **Home Manager** (`sgt_xinyang_welcome.group_home_manager`) vẫn được Admin cấp thủ công trong **Settings > Users > Access Rights > Home**, dùng cho nhân viên phụ trách sản phẩm.
- **Internal User** không thuộc hai nhóm trên: chỉ được xem Home và sản phẩm, không được phép tạo/sửa/xóa sản phẩm. Việc giới hạn áp dụng cả ở server-side ACL, menu và nút **+ Manage products**.
- **Banners / Highlights / Website switch** vẫn chỉ dành cho Settings Administrator; việc cấp Home Manager đơn thuần không mở các mục đó.
- Giữ nguyên tên module, manifest version `19.0.1.1.8` và luồng Login → Home/đường dẫn Lead của Update_011; đây là ZIP Update_011 đã sửa, **không phải module phụ hoặc gói cài riêng**.

## Update_011 (15/11/2026) — Login trước, Home ngay sau đăng nhập
- Khách truy cập địa chỉ gốc `https://xinyang.sge.vn/` được chuyển tạm thời (HTTP 302) tới trang đăng nhập có thương hiệu `/web/login`. **Không có Home công khai**.
- Sau khi nhân viên đăng nhập thành công từ trang đăng nhập, tự động mở đúng client action `sgt_xinyang_welcome.action_sgt_home` tại đường dẫn `/odoo/action-<ID thực tế>` (không phụ thuộc thứ tự app menu).
- Người dùng đã đăng nhập mở lại `/` được chuyển thẳng về Home. Tài khoản Portal giữ chuyển hướng mặc định `/my`.
- Giữ nguyên các đường dẫn cụ thể có tham số `redirect=` trong login để không chặn việc mở link từ email/CRM. Trường hợp thiếu Home action thì về `/odoo` thay vì gây lỗi.
- **Không thay giao diện login**, không công khai thư viện, không thay model/dữ liệu Home. Chỉ bổ sung quyền quản lý sản phẩm mặc định cho Settings Administrator trong bản thay thế Update_011. Home dùng nội dung tiếng Anh của Update_010.
- Giữ cơ chế Website switch của Update_010: Admin bật Website thì `/` trở lại trang Website; tắt đi trở về Login → Home. Chế độ mặc định vẫn là tắt Website.
- Phần kiểm tra offline xác nhận luồng chuyển hướng; cần test trên Odoo 19 demo trước khi Production.

## Update_010 (15/11/2026) — Xinyang Home B2B + quản lý sản phẩm có phân quyền
- Nâng cấp **giao diện ứng dụng Home nội bộ Odoo** sang trang doanh nghiệp tiếng Anh dựa trên Home concept đã duyệt: Hero, năng lực, giải pháp, ngành ứng dụng, thư viện sản phẩm, quy trình hợp tác, thông tin liên hệ và lời mời liên hệ qua email.
- **KHÔNG thay đổi trang login**, Website switch, root redirect và thiết kế logo Xinyang / Saigon Trade từ Update_009.
- Vẫn dùng `sgt.home.slide` và `sgt.home.fact`: banner cũ xuất hiện trong phần **Company highlights**, fact cũ xuất hiện dưới thông số chính. Quản lý Banners/Highlights vẫn theo quyền Settings như Update_009.
- Model `sgt.home.product`: `name` (tiêu đề tiếng Anh), `code` (mã sản phẩm), `subtitle` (dòng ngắn), `description` (ghi chú hiển thị), `category`, `image`, `sequence`, `active` (Show on Home), `internal_note` (không hiển thị). **Home > Products** là nơi thêm/sửa/đổi thứ tự/ẩn sản phẩm mà không cần cập nhật ZIP.
- **Settings > Users & Companies > Users > chọn nhân viên > Access Rights > Home > Home Manager**: người được chọn có thể tạo/sửa/xóa sản phẩm (ngoài Settings Administrator, vốn được cấp mặc định). Cấu hình Odoo 19 bằng `res.groups.privilege` + group `group_home_manager`. Người dùng nội bộ thường được đọc sản phẩm (ACL read-only); menu Products và nút `+ Manage products` chỉ hiện với Home Manager hoặc Settings Administrator. **Superuser Odoo** vẫn có quyền đặc biệt theo cơ chế chuẩn của hệ thống.
- 06 sản phẩm mẫu đã có ảnh từ bộ poster người dùng gửi, mô tả giao diện tiếng Anh. *Nội dung chữ tiếng Việt đã in sẵn trong các poster không thể chuyển thành tiếng Anh bằng form nhập nội dung; thay ảnh bằng bản tiếng Anh khi sẵn sàng.* Các record mẫu `noupdate=1` bảo toàn sửa đổi sau này.
- Catalog PDF được đóng gói làm tài liệu xem trực tiếp bằng nút View catalog. Các thông tin sự kiện doanh nghiệp chỉ sử dụng nội dung từ catalog/ảnh nguồn do người dùng cung cấp.
- Form liên hệ chuyển thành **email draft** tới email nhà sản xuất (mở ứng dụng email trên máy), không tự lưu thông tin trên Odoo hoặc tự tạo CRM lead.

### Cách thêm sản phẩm
1. Settings Administrator có thể vào ngay **Home → Products** mà không cần cấp Home Manager. Với nhân viên khác, Admin vào **Settings → Users & Companies → Users**, chọn nhân viên, mục **Access Rights** → **Home** → **Home Manager**, bấm Save.
2. Người đã được cấp quyền vào **Home → Products** hoặc **Home → nút + Manage products** → **New**.
3. Tải ảnh lên `Product image`; điền `Product title (English)`, `Model / product codes`, `Short subtitle`, `Description / notes`, chọn nhóm sản phẩm.
4. Bật `Show on Home` để hiện, sắp xếp bằng kéo cột `Display order`; tắt để ẩn tạm nhưng không xoá dữ liệu.
5. Quay lại trang Home hoặc tải lại để thấy sản phẩm mới. Chọn All products / Air outlets / Acoustics / Fire & smoke để lọc.

### Triển khai an toàn
- **Chưa cài thử trong cơ sở dữ liệu Odoo thật**; cần nâng cấp trên môi trường staging (xinyangdemo2) trước khi production.
- Sao lưu Odoo database và thư mục `sgt_xinyang_welcome` hiện tại. Giải nén ZIP lấy nguyên thư mục addon, chép đè (không xoá dữ liệu DB); Restart Odoo → Apps → Update Apps List → Upgrade module **XINYANG | UI-009 Login + Home** → Ctrl+Shift+R.
- Kiểm tra 2 loại tài khoản: người không được cấp Home Manager (xem Home nhưng không tạo được `sgt.home.product` qua UI/API) và người được cấp (đầy đủ thao tác); đăng nhập và Website switch vẫn hoạt động.
- Odoo mỗi nơi có thể thay đổi asset bundles / theme; sau khi upgrade cần xác nhận bố cục tại nơi chạy thật.

## Update_009 (14/11/2026)
- Logo hợp tác Saigon Trade × Xinyang = đúng ảnh `Logo_Match_Making.png` bạn gửi lúc 21:28 (chữ Y gốc, không ghép logo mới), dùng ở mọi nơi: header đăng nhập, slide Saigon Trade, dải đối tác Home, góc phải 004. Nền trắng bên trong giữ nguyên. Ảnh đổi tên `..._v3.png`. Logo Xinyang chuẩn (chữ Y + 新扬) vẫn dùng ở slide Xinyang Home và icon app.

## Update_008 (14/11/2026)
- Logo hợp tác luôn có nền trắng bên trong: ảnh được đổi tên (`..._v2.png`) để trình duyệt tải lại, và thêm nền trắng hình tròn phía sau logo ở header đăng nhập và dải đối tác Home. Nguyên nhân bạn thấy ruột trong suốt: production đang chạy bản 009 cũ (trước Update_005), chưa cập nhật.

- Địa chỉ gốc `/` (xinyang.sge.vn): chưa đăng nhập -> trang đăng nhập; đã đăng nhập -> app Home (người dùng portal -> /my). Chuyển hướng tạm thời (302).
- App Website MẶC ĐỊNH ẨN khỏi menu ứng dụng (không gỡ, không xoá dữ liệu). Bật lại: Settings > nút **Website** (bên phải Technical) > bấm **Active**; trang tự tải lại, app Website hiện lại và địa chỉ gốc trở về trang chủ Website. Tắt lại: cùng chỗ đó bấm **Deactivate**. Chỉ nhóm Settings (Admin) thấy nút này.
- Trang Website vẫn mở được ở các địa chỉ khác (ví dụ /contactus) và trong trình soạn thảo của app Website, kể cả khi đang ẩn.
- Cách hoạt động: model `sgt.website.switch` (1 bản ghi) lưu tắt/bật, bật/tắt menu gốc `website.menu_website_configuration` và tham số `sgt_xinyang_welcome.website_on`. Gỡ 009 thì menu Website KHÔNG tự hiện lại: vào Settings > Technical > User Interface > Menu Items, bỏ lưu trữ (Archived) menu "Website".

## Update_007 (14/11/2026)
- Logo Xinyang chuẩn: dùng ảnh bên trái của logo chuẩn (chữ Y + 新扬) thay 2 logo cũ: (1) logo Xinyang: slide Xinyang và màn hình trống của Home, icon app; (2) chữ Y bên trong logo hợp tác Saigon Trade × Xinyang (header đăng nhập, slide Saigon Trade, dải đối tác Home). Riêng form đăng nhập giữ logo ngang có tên công ty (đúng ảnh mẫu bạn gửi 21:02). Module 004 cũng đổi logo hợp tác ở góc phải (bản 004 Update_006).
- Banner: tắt = "tạm ẩn". Công tắc "Show on Home" ở mỗi dòng Home > Banners; banner ẩn vẫn nằm trong danh sách (chữ xám) để bật lại bằng 1 click. Bộ lọc "Shown on Home" / "Hidden". Không thêm trường mới (dùng trường `active` có sẵn).

## MẪU BANNER (dùng để thêm banner mới)
Một banner = 1 bản ghi `sgt.home.slide` (Home > Banners > New, hoặc thêm `<record>` vào `data/home_data.xml`).
- Bố cục: thẻ rộng, nửa trái chữ (nhãn đỏ nhỏ viết hoa -> tiêu đề lớn -> 1 câu mô tả -> nút tùy chọn), nửa phải là ảnh 960x560 (tùy chọn) hoặc, nếu không có ảnh, một đĩa trắng chứa logo. Mũi tên, chấm chuyển slide, tự chạy 6 giây, dừng khi rê chuột.
- Theme `blue` (nền trắng/xanh nhạt, tiêu đề xanh `#0061BD`, đĩa logo Xinyang) dùng cho nội dung Xinyang. Theme `red` (nền trắng/hồng nhạt, tiêu đề đỏ đậm `#B3181A`, đĩa logo hợp tác Saigon Trade × Xinyang) dùng cho nội dung Saigon Trade.
- Trường: `tag` (nhãn, ngắn), `name` (tiêu đề), `text` (1 câu), `theme`, `button_label` + `button_url` (chỉ `https://`, `http://` hoặc `/đường-dẫn`), `image` (tùy chọn), `sequence` (10, 20, 30...), `active`.
- Quy tắc: chữ tiếng Anh; không đưa thông tin về Xinyang nếu chưa có nguồn (website hoặc do bạn cung cấp); chỗ chưa có thì để trống.
- Mẫu thêm bằng XML:
```xml
<record id="slide_ten_moi" model="sgt.home.slide">
    <field name="sequence">30</field>
    <field name="theme">blue</field>
    <field name="tag">NHÃN NGẮN</field>
    <field name="name">Tiêu đề banner</field>
    <field name="text">Một câu mô tả.</field>
    <field name="button_label">Tên nút</field>
    <field name="button_url">https://...</field>
</record>
```

## Update_006: header xanh của trang đăng nhập hiện thêm dòng tiếng Anh bên phải logo hợp tác: "We accompany organizations in and outside Vietnam to expand their business in the Vietnamese market." (bản dịch khẩu hiệu saigontrade.vn, cần bạn xác nhận cách dịch). Trên điện thoại chữ nhỏ hơn và xuống 2 dòng.

## Update_005: chân trang dùng logo chữ SAIGON TRADE (file user gửi 14/11) thay logo tròn, đặt phía trên tên công ty ở cột trái.

## Update_004 (14/11/2026)
- Header trang đăng nhập: nền xanh `#0061BD` + vạch đỏ 4px sát mép dưới, giống thanh menu của trang chính (UI-004). Logo hợp tác ở góc trái trên.
- Chân trang: thêm logo bên trái (Update_005 đổi sang logo chữ SAIGON TRADE).
- Logo hợp tác đã làm lại: nền trong suốt ở ngoài vòng tròn, trắng đặc ở trong (bản cũ bị "thủng" nền khi đặt lên nền xanh).
- Khôi phục banner Saigon Trade: khi Upgrade, nếu slide chỉ bị lưu trữ (archive) thì được bật lại; nếu bị xóa thì Odoo tạo lại từ dữ liệu mẫu. Thêm bộ lọc **Archived** ở Home > Banners và Highlights để tự khôi phục sau này.
- Không đổi dữ liệu bạn đã sửa (slide Welcome, thẻ số liệu…).

## Update_003: chỉ đổi tên hiển thị trong Apps thành "XINYANG | UI-009 Login + Home" (cùng kiểu tên với UI-004); tìm bằng "UI-009" hoặc "009". Tên kỹ thuật/thư mục vẫn là `sgt_xinyang_welcome`.

## Thay đổi Update_002 so với Update_001
Chỉ 1 thay đổi an toàn: view gắn cờ trang đăng nhập nay kế thừa `website.login_layout` thay vì `web.login_layout`,
để nếu view đó của Odoo bị tắt thì module bỏ qua chứ không làm hỏng trang đăng nhập. Không đổi giao diện hay dữ liệu.

## Module làm gì
1. **Trang đăng nhập `/web/login`** (chỉ trang này, phần còn lại của Website không đổi):
   logo kết hợp Saigon Trade × Xinyang góc trái trên; logo Xinyang phía trên form; thông tin công ty
   Saigon Trade ở cuối trang; xanh `#0061BD`, đỏ `#E51922`, đỏ đậm `#B3181A` (đo từ file logo).
2. **App "Home"**: app đầu tiên trong menu, mở ngay sau khi đăng nhập, mọi tài khoản nội bộ đều thấy.
   Banner chuyển động (tự chạy 6 giây, tạm dừng khi rê chuột, có nút ◀ ▶ và chấm), tiếng Anh;
   khối "Xinyang at a glance" (ẩn nếu chưa có thẻ nào); dải Saigon Trade ở cuối.
3. **Home > Banners / Home > Highlights** (chỉ nhóm Settings): thêm/sửa/xóa slide và thẻ số liệu
   ngay trong Odoo, **không cần ZIP mới** mỗi lần đổi nội dung.

## Cài đặt (khuyến nghị: cài thử trên xinyangdemo2 trước, rồi mới lên xinyang)
1. Sao lưu database.
2. Chép **thư mục** `sgt_xinyang_welcome` (giải nén ZIP, lấy thư mục bên trong) vào thư mục addons của Odoo,
   cùng chỗ với các module sgt_ khác. Khởi động lại dịch vụ Odoo.
3. Đăng nhập admin, bật Developer mode → Apps → **Update Apps List** → bỏ bộ lọc "Apps", tìm
   **UI-009** (tên: XINYANG | UI-009 Login + Home) → **Install**. (Nếu Website chưa cài, Odoo tự cài kèm.)
4. Bấm **Ctrl+Shift+R** trên trình duyệt (xóa cache giao diện).
5. Kiểm tra theo mục dưới.

Cập nhật bản sau: chép đè thư mục → khởi động lại → Apps → module → **Upgrade**.
Slide/thẻ do bạn sửa trong Odoo không bị ghi đè khi Upgrade.

## Kiểm tra sau khi cài
- Mở cửa sổ ẩn danh, vào `/web/login`: có logo kết hợp góc trái, logo Xinyang trên form, chân trang xanh có thông tin Saigon Trade.
- Đăng nhập một tài khoản thường (không phải admin): vào thẳng **Home**; menu app (ô vuông góc trái) có Home đứng đầu.
- Tài khoản admin: thấy thêm mục **Banners**, **Highlights** trên thanh menu của Home.
- **Tài khoản có "Home Action"** sẽ vào Home Action đó thay vì Home. Kiểm tra bằng SQL
  `SELECT id, login FROM res_users WHERE action_id IS NOT NULL;`
  hoặc Settings → Users → từng user → tab Preferences → ô *Home Action* phải trống.
- Link sâu (ví dụ email chứa link tới một Deal) vẫn mở đúng chỗ, vì Odoo chỉ về Home khi không có địa chỉ đích.

## Nội dung ban đầu (cố ý tối giản, KHÔNG có số liệu Xinyang nào)
- Slide 1 "Welcome to Xinyang" + logo 新扬 (logo do bạn cung cấp).
- Slide 2 "Connecting customers in Vietnam with Xinyang" (đỏ): câu về Saigon Trade là **bản dịch tiếng Anh của tôi**
  từ khẩu hiệu trên saigontrade.vn — cần bạn xác nhận. Tên "SAIGON TRADE COMPANY LIMITED" cũng là bản dịch của tôi
  (tên pháp lý tiếng Việt, MST 0318419089, địa chỉ, hotline lấy từ saigontrade.vn ngày 14/11/2026).
- Thông tin Xinyang (sản phẩm, năm thành lập, chứng nhận, ảnh nhà máy…): nhập ở Home > Banners / Highlights khi có nguồn
  (jsxyjd.com chặn công cụ đọc web nên chưa lấy được). Cột *Source* của Highlights để ghi nguồn.
- Ảnh banner khuyến nghị 960 × 560 px (không có ảnh thì hiện logo).

## Cần bạn xác nhận (chưa có đáp án)
- CN2 trên saigontrade.vn ghi mâu thuẫn (Cobi Tower 69 Hoàng Văn Thái hay Phú Mỹ Apartments) — đang dùng "69 Hoàng Văn Thái".
- Email Saigon Trade (trang web mã hóa) — chưa đưa vào chân trang.
- Giữ cả 6 chi nhánh hay chỉ văn phòng đại diện.

## Gỡ module
Apps → XINYANG | UI-009 Login + Home → Uninstall. Trang đăng nhập về như cũ; menu Home biến mất; hai bảng banner/highlight bị xóa.

## Tệp trong module
`views/login_templates.xml` (đăng nhập) · `static/src/css/login.css` · `static/src/home/*` (component Home) ·
`models/*` (banner, thẻ) · `views/home_views.xml` (menu + màn hình quản trị) · `data/home_data.xml` (2 slide mẫu, noupdate) ·
`tests/test_welcome_contract.py` (chạy `python3 -I tests/test_welcome_contract.py`, không cần Odoo).
