# CRM-002 Update_027 (19.0.1.23.0) — phân quyền phễu theo trường Sales (trên form User) × Department (nút Permissions)

Nguồn: Update_026 (19.0.1.22.0). **Chỉ đổi cách CRM-002 quyết định ai thấy phễu nào, và ai dùng được 5 hàm lọc trùng `yp_*`.** Không field, model, view, menu, cron, JS, record rule hay ACL nào thêm/đổi. Nâng cấp module bình thường, không có upgrade script.

## Vì sao (user nêu 02/11/2026 14:16)
Muốn cho một user xem toàn bộ dữ liệu TẠM để xử lý. Trước đây chọn Sales = All Documents / Administrator không đủ, vì CRM-002 không đọc trường Sales mà chỉ hỏi "Role Administrator?" và Department. Phải đổi Role thành Administrator → nguy hiểm (lộ cả Settings, Users, mọi app). Nay chỉ cần đổi **một dropdown Sales** trên form User.

## Luật (user chốt 14:35–14:48)
| Trường Sales trên form User | Phễu CRM-002 thấy được | Lọc trùng (5 hàm `yp_*`) |
|---|---|---|
| **No** | **Không phễu nào** (màn hình "Bạn chưa được phân quyền phễu nào"; Odoo vốn đã ẩn app CRM và chặn đọc Deal) | **Không dùng được** (`forbidden`) |
| **User: Own Documents Only** | Chỉ phễu Data Funnel / Match Making đã gán cho Department của user ở nút **Permissions** (như trước). **Không bao giờ thấy phễu Sale (New/Renew)**, kể cả khi thuộc phòng Administration | Dùng được |
| **User: All Documents** | **Mọi phễu**, kể cả phễu để trống Department (Outbound Data, Inbound GB) và Sale New/Renew, bỏ qua Department | Dùng được |
| **Administrator** (Sales) | Như All Documents (Odoo: Sales Administrator đã gồm All Documents) | Dùng được |
| **Role Administrator** (Settings) | Mọi phễu + nút Permissions/Settings + Luật bàn giao | Cần **thêm** nhóm Sales (xem dưới) |

- **Chỉ Role Administrator** (`base.group_system`) vẫn có: nút Permissions/Settings, menu Cài đặt phễu / Phân quyền phễu / Luật bàn giao, danh sách phòng ban, hàm quét `yp_duplicate_scan`, `force_duplicate=True`, bỏ lọc "My Pipeline" mặc định khi vào CRM. Sales Administrator hay All Documents KHÔNG có các thứ này (ACL của phễu/luật vẫn là `base.group_system`).
- **Người All Documents vào CRM vẫn bị lọc "My Pipeline" mặc định** (user chốt 14:48); bấm bỏ bộ lọc là thấy hết.
- **Deal trong phễu vẫn do Odoo quyết định**: Own Documents Only chỉ thấy Deal của mình hoặc chưa gán người (rule "Personal Leads"); All Documents thấy và **sửa** được mọi Deal (rule "All Leads") và xem báo giá/đơn hàng. CRM-002 chỉ quyết định phễu nào hiện.
- **Lọc trùng** (`yp_duplicate_check`, `yp_read_lead`, `yp_update_lead`, `yp_create_lead`, `yp_duplicate_scan`): đòi tối thiểu nhóm Sales **Own Documents Only** (nhóm All Documents và Sales Administrator đã gồm nó). **Role Administrator không kéo theo nhóm Sales** (đã kiểm trên production), nên Role Administrator để Sales = No cũng bị `forbidden`, kể cả hàm quét. Hàm quét đòi **cả hai**: Role Administrator VÀ nhóm Sales. Ai không có quyền nhận `{ok:false, code:'forbidden', message}` trước mọi truy vấn.
- **Cập nhật Deal trùng qua `yp_update_lead`** không đổi: Admin, phòng Kinh doanh (MMC) hoặc chủ Deal. All Documents không tự được cập nhật.
- **Bỏ**: không có nút/cột "người dùng ngoại lệ". Muốn đổi quyền ai thì vào chính user đó đổi trường Sales.
- Màn hình **Permissions** vẫn liệt kê phễu Sale (user chốt giữ), nhưng giá trị Department của New/Renew **không còn tác dụng**.

## Đã đổi trong mã
- `models/service.py`: thêm `_sees_all()` (= Role Administrator hoặc `sales_team.group_sale_salesman_all_leads`) và `_has_sales()` (= `sales_team.group_sale_salesman`). Dùng trong đúng 4 nơi: `_allowed` (kéo theo `_check_funnel`, `board`, `move`, `open_intake`, tạo/kéo thẻ phễu), `_visible_funnels` (sidebar `bootstrap`, `landing_action`), `_mm_allowed` (khóa dữ liệu Match Making của Update_012), `landing_action`. `_is_admin()` giữ nguyên cho mọi thứ cấu hình.
- `models/duplicate.py`: `_yp_internal_only()` đòi `sales_team.group_sale_salesman` (trước đây `base.group_user`); `yp_duplicate_scan` gọi thêm cổng này sau khi kiểm Role Administrator.
- `models/yp_utils.py`: hằng `SALES_USER_GROUP`.
- Tên nhóm đã kiểm trên production (02/11): `sales_team.group_sale_salesman` (id 22) → `group_sale_salesman_all_leads` (23, kéo theo 22) → `group_sale_manager` (24, kéo theo 23). Rule `crm.lead`: Personal Leads (nhóm 22), All Leads (nhóm 23). ACL đọc `crm.lead` chỉ cho nhóm 22 và 24.

## Hệ quả cần biết trước khi cài
1. **User Own Documents Only đang thuộc phòng Administration sẽ MẤT phễu New/Renew** (trước đây phễu Sale gán cho Administration). Ai cần xem Sale: đổi Sales sang All Documents/Administrator.
2. **Kinh doanh (MMC) vẫn không vào được Sale** (như cũ). Phòng ban khớp đúng ID, không tính phòng con; việc này chưa đổi.
3. **Role Administrator để Sales = No** thấy mọi phễu và nút cấu hình nhưng **không đọc được Deal** (Odoo gốc không cấp ACL `crm.lead` cho nhóm hệ thống). Đặt Sales = Administrator cho các tài khoản admin.
4. Nhân viên đang để Sales = No và dùng extension: kiểm trùng/tạo Deal nhận `forbidden` (trước đây kiểm trùng vốn đã không chạy được vì không đọc được Deal; tạo Deal vốn bị Odoo chặn).
5. Sau khi đổi trường Sales của một user, user đó **tải lại trang (F5)** mới thấy thay đổi.

## Đã test
- Offline: **251 test xanh** (225 cũ + 26 mới: `test_update027_sales_tiers.py` 19 test chạy CODE THẬT `_sees_all`, `_has_sales`, `_allowed`, `_check_funnel`, `_visible_funnels`, `_mm_allowed`, `landing_action` với đúng 7 phễu production; `SalesGateTests` 7 test trong `test_update026_duplicate.py` cho 5 hàm `yp_*`). Cố ý làm hỏng mã 12 kiểu (All Documents không thấy hết, Sale mở theo phòng, Sales No thấy phễu, `_mm_allowed`/landing bỏ qua All Documents, cổng `yp_*` về `base.group_user`, hàm quét không đòi Sales, kiểm trùng không cổng, All Documents mất lọc My Pipeline…) đều có test đỏ.
- Đọc production chỉ đọc: nhóm Sales 22/23/24 và xml id, rule và ACL `crm.lead`, menu CRM (nhóm 22 và 24), `base.group_system` không kéo theo nhóm Sales, cấu hình 7 phễu.
- **Chưa chạy trên Odoo thật**: `has_group` trên Odoo 19, trường Sales trên form User, hiển thị sidebar.

## Cài đặt
1. Backup Demo 2. Thứ tự: CRM-005 Update_032 (nếu chưa), rồi CRM-002 Update_027 (nâng cấp trực tiếp từ Update_026 hoặc cũ hơn; module `sales_team` đã nằm trong depends từ Update_011).
2. Upgrade module, restart Odoo.
3. Rollback: cài lại Update_026 (không đổi dữ liệu nào).

## Bài test trên Demo 2
Chuẩn bị 8 user (đúng một thứ khác nhau mỗi user), mỗi lần đổi quyền thì F5:
| User | Role | Sales | Department |
|---|---|---|---|
| U1 | User | No | Kinh doanh (MMC) |
| U2 | User | Own Documents Only | Kinh doanh (MMC) |
| U3 | User | Own Documents Only | Công nghệ (CN) |
| U4 | User | Own Documents Only | Administration |
| U5 | User | All Documents | (không phòng) |
| U6 | User | Administrator | Công nghệ (CN) |
| U7 | Administrator | Administrator | bất kỳ |
| U8 | Administrator | No | bất kỳ |

| # | Làm | Kỳ vọng |
|---|---|---|
| 1 | U1 mở CRM-002 (link phễu / sidebar) | Không phễu nào; màn hình "Bạn chưa được phân quyền phễu nào"; app CRM bị Odoo ẩn |
| 2 | U2 vào CRM | Sidebar: Outbound Hunter, Inbound Pool, Match Making; không Outbound Data, Inbound GB, không nhóm Sale; vào thẳng pipeline Match Making có lọc My Pipeline |
| 3 | U3 vào CRM | Chỉ Inbound Pool; vào thẳng Inbound Pool; mở link Match Making → danh sách rỗng |
| 4 | U4 vào CRM | Không phễu nào (hệ quả đã chốt: mất New/Renew) |
| 5 | U5 vào CRM | Sidebar đủ 7 phễu (Outbound Hunter, Inbound Pool, Outbound Data, Inbound GB, Match Making, New, Renew); **không** có nút Permissions/Settings; vào Match Making có lọc My Pipeline, bỏ lọc thì thấy Deal của mọi người |
| 6 | U6 làm như bài 5 | Giống U5 |
| 7 | U7 vào CRM | Đủ 7 phễu + nút Permissions/Settings; vào Match Making **không** gắn My Pipeline |
| 8 | U8 vào CRM | Đủ 7 phễu + nút cấu hình; mở Deal bị Odoo báo thiếu quyền (đặt Sales = Administrator để sửa) |
| 9 | Mở phễu Sale New bằng link trực tiếp bằng U2 và U4 | Báo "Bạn không được cấp quyền truy cập phễu này" |
| 10 | Đổi U2 sang All Documents → F5 | Thấy đủ 7 phễu; đổi lại Own Documents Only → F5 → còn 3 phễu; **không cần động vào Role** |
| 11 | U5 kéo một thẻ trong phễu Sale New sang cột khác | Được; có Log note chuyển stage |
| 12 | U2 kéo thẻ Match Making sang `6.Approved Match Making` | Luật bàn giao vẫn chạy (Deal sang Sale New); không báo lỗi quyền |
| 13 | Extension/`execute_kw` `yp_duplicate_check`: U1 | `forbidden` (message nhắc quyền Sales) |
| 14 | Như 13: U2, U5, U6 | `ok:true`; `is_admin:false`; `can_update` chỉ true với Deal của chính họ hoặc nếu thuộc Kinh doanh (MMC) |
| 15 | Như 13: U8 (Role Administrator, Sales = No) | `forbidden`; `yp_duplicate_scan` cũng `forbidden` |
| 16 | `yp_duplicate_scan({'probe': True})`: U7 | `{ok:true, is_admin:true, probe:true}`; U6 (Sales Administrator, không Role Administrator) và U5 → `forbidden` |
| 17 | `yp_create_lead` trùng + `force_duplicate=True`: U7 | Tạo được (như Update_026); U6 → `duplicate` |

## Việc bên Extension / tài liệu liên quan
Extension không phải đổi mã: `forbidden` đã là mã lỗi nó hiểu (hiện thông báo, chặn thao tác). Cần dặn nhân viên: tài khoản dùng extension phải có Sales tối thiểu Own Documents Only.

## Giới hạn đã biết
- Khớp phòng ban theo ID đúng (không tính phòng con) và theo tên phòng "Kinh doanh (MMC)" cho `is_sales` của lọc trùng: như Update_026.
- Số điện thoại dính liền dãy số khác chỉ cách bằng dấu cách/chấm/gạch bị sót khi kiểm trùng: như Update_026 (chưa sửa).
- Không có tự hết hạn: bật tạm rồi nhớ đổi lại Sales về Own Documents Only.
