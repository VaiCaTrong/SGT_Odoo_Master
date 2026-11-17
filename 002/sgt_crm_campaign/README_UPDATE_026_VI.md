# CRM-002 Update_026 (19.0.1.22.0) — kiểm tra trùng Deal toàn hệ thống cho Extension (5 hàm `yp_*`: 4 hàm kiểm tra/tạo/đọc/sửa + hàm quét cho Admin)

Nguồn: Update_025 (19.0.1.21.0). **Chỉ thêm**: không field, view, menu, record rule hay hàm cũ nào bị đổi. Extension cũ (017, 020-from-017) vẫn chạy bình thường. Extension Update_021/022 (kiểm trùng toàn hệ thống, tab Lọc trùng cho Admin) chỉ dùng được sau khi bản này đã cài và test xong trên Demo 2.

## Luật (user chốt 02/11/2026 08:58)
- Phạm vi: chỉ **Deal** (`crm.lead`). Trùng Contact/Company và báo cáo chưa làm.
- Trùng = cùng số điện thoại (9 số cuối, mọi dạng `0912…`, `+84 912…`, `0912.345.678`…) hoặc cùng Mã số thuế (`x_yp_tax_code`). Quét `phone, x_phone, x_mobilephone, description, name` (và `mobile` nếu DB có field này; Xinyang hiện không có). Tìm trên **toàn bộ** Deal: mọi phễu, mọi người phụ trách, cả Mark Lost và lưu trữ.
- Khi trùng: trả **tất cả** Deal trùng (tối đa 50, kèm `truncated`). Mỗi Deal chỉ có: tên, công ty, người phụ trách, phễu/bước/stage, trạng thái `active|lost|archived`, `is_owner`, `can_update`. Không bao giờ trả SĐT, email, ghi chú.
- **Tạo Deal mới**: bị chặn với mọi nhân viên khi còn Deal trùng (kể cả chủ của Deal trùng). Chỉ **Admin** tạo được, và chỉ khi gửi `force_duplicate=True` (tham số thứ 4 của `yp_create_lead`, mặc định `False`).
- **Cập nhật Deal**: tính theo từng Deal. Được phép nếu là **Admin**, nhân viên **phòng Kinh doanh (MMC)** (gồm phòng con, tìm theo tên phòng trong Employees, không thêm cấu hình mới) hoặc **chủ Deal** (`user_id` = người gọi). Còn lại `forbidden`.
- **Thứ tự "xa nhất"** (user chốt 02/11 09:10), dùng cho `matches` của `yp_duplicate_check` và `members` của hàm quét: Deal đang hoạt động đứng trước Deal đã mất/lưu trữ (bất kể vị trí); rồi nơi xa nhất: **Sale** (phễu New/Renew rồi stage của phễu) > **Match Making** (`stage_id`, cột 1 → 6) > **Data Funnel** (`potential` > `verified` > `data`, chỉ dùng khi Deal không có cột Match Making); bằng nhau thì Deal ID nhỏ (cũ) hơn đứng trước. **Việc cắt tối đa 50 diễn ra SAU khi sắp**, nên số hotline dùng chung cho 120 Deal vẫn hiện 50 Deal xa nhất.
- Giới hạn: kiểm tra trùng 30 lần/phút/user (đếm trong bộ nhớ từng tiến trình); tạo Deal 5/phút/user, Admin 10/phút (đếm từ `create_date` trong DB).
- Chỉ nhân viên nội bộ (`base.group_user`) gọi được; tài khoản portal nhận `forbidden`.

## 5 hàm (gọi `execute_kw` trên `sgt.crm002.service`, tham số theo thứ tự)
| Hàm | Trả về |
|---|---|
| `yp_duplicate_check(phone_keys, tax_code)` | `{ok, is_admin, is_sales, can_update, truncated, total, matches[]}` hoặc lỗi |
| `yp_duplicate_scan(options)` | **Chỉ Admin**, chỉ đọc: `{ok, is_admin, max_batch, scanned, from_id, to_id, next_after_id, done, groups[]}` (xem mục dưới) |
| `yp_create_lead(vals, phone_keys, tax_code, force_duplicate=False)` | `{ok:true, id}` hoặc `{ok:false, code:'duplicate', matches[], …}` |
| `yp_read_lead(lead_id, field_names)` | `{ok:true, values}` |
| `yp_update_lead(lead_id, vals)` | `{ok:true, id}` |

Mỗi phần tử `matches[]` (và `members[]` của hàm quét) có thêm 3 số thứ tự cột: `stage_seq` (= `crm.stage.sequence`), `sale_stage_seq`, `sale_funnel_seq` (= `sequence` phễu New/Renew); `null` khi Deal không ở nơi đó. `total` = số Deal trùng thật; `truncated = total > 50`.

Mã lỗi: `invalid` (kèm `message`), `forbidden`, `not_found` (chỉ Admin/Kinh doanh (MMC)), `duplicate`, `rate_limit` (kèm `retry_after`; khi hệ thống đang xử lý cùng SĐT/MST quá 10 giây thì trả `rate_limit` kèm `reason:'busy'`, `retry_after:3`). Field đọc/ghi là danh sách trắng cố định (handoff mục 3.3); `stage_id`, `user_id`, `tag_ids`, `sgt_crm002_*`, `active`… bị `invalid`.

## Hàm quét `yp_duplicate_scan(options)` (chỉ Administrator, chỉ đọc)
- **Quyền kiểm đầu tiên**, trước mọi truy vấn: không phải Admin (`has_group('base.group_system')`) → `forbidden`, **kể cả `probe`**, không chạm database (có test: 0 truy vấn). Hàm không ghi gì, không tạo Chatter, không đổi `write_date`.
- `options` (dict, key lạ bỏ qua): `probe` (bool), `after_id` (int ≥ 0, mặc định 0), `limit` (int, mặc định và **tối đa 2000**; số lớn hơn bị ép về 2000, nhỏ hơn 1 ép về 1). Sai kiểu → `invalid` (không tính vào giới hạn quét).
- `probe=True` → `{ok, is_admin:true, probe:true, max_batch:2000}`, không quét; riêng 30 lần/phút/user. Quét: **6 lần / 10 phút / user** (`rate_limit` kèm `retry_after`). Cả hai đếm trong bộ nhớ từng tiến trình Odoo.
- **Cách quét**: đọc **một lần** (SQL thuần, mỗi trang 1000 Deal, mọi phễu, cả Lost/lưu trữ) các cột SĐT/MST rồi nối các Deal chung khóa bằng union-find (A trùng B bằng SĐT, B trùng C bằng MST → một nhóm A, B, C). Dùng đúng hàm chuẩn hóa `phone_keys_in_text`/`tax_key` và đúng danh sách field của `yp_duplicate_check`; field không có trên DB thì bỏ qua. Không gọi `yp_duplicate_check` nhiều lần.
- **Lô và con trỏ**: hạt giống = Deal đang hoạt động (không ở cột Mark Lost) có `id > after_id`, theo ID tăng dần, tối đa `limit`. Mỗi nhóm có `owner_id` = ID nhỏ nhất trong các thành viên đang hoạt động, và **chỉ được trả ở lô có `after_id < owner_id <= to_id`**: quét nhiều lô không lặp nhóm và nhóm luôn đủ thành viên dù thành viên nằm ngoài lô. Nhóm chỉ gồm Deal Lost/lưu trữ thì không trả. `next_after_id = to_id` nếu còn Deal hoạt động phía sau, ngược lại `null` và `done=true`.
- Mỗi nhóm: `{size, truncated, members[]}` đã sắp theo thứ tự "xa nhất" rồi mới cắt 50 (`members[0]` là cha). `members[i]` cùng định dạng `matches[i]` của `yp_duplicate_check`; `phone` = chung SĐT với một Deal khác trong nhóm, `tax` = chung MST với một Deal khác. Không bao giờ có SĐT, email, ghi chú. Nhóm xếp theo `owner_id` tăng dần.
- Nhật ký máy chủ: một dòng info mỗi lần quét (uid, `after_id`, `scanned`, số nhóm, số ms), không có SĐT/MST.
- Hotline dùng chung **không** bị loại khỏi việc gom nhóm (mặc định user chốt); nhóm lớn bị cắt ở 50 thành viên nhưng `size` là số thật.

## Sự thật đã đọc trên production (chỉ đọc, 02/11/2026 ~10:00)
- Odoo hiện chỉ có **6 cột** `crm.stage`: 1.Opportunity (0), 2.Connected (1), 3.Interacted (2), 4.Interesting (4), 5.Match Making (5), 6.Approved Match Making (6). **Không còn cột "Mark Lost" hay "7.Chờ xử lý"**: Deal mất đều `active=False`. Quy tắc "Deal còn `active` nhưng nằm trong cột có tên chứa *Mark Lost* thì tính `lost`" đã cài sẵn (hằng `LOST_STAGE_NAME`) nhưng hiện không kích hoạt với dữ liệu thật.
- Phễu `sgt.crm002.funnel` và stage `sgt.crm002.funnel.stage` **đều có `sequence`** (New = 60, Renew = 70) nên `sale_funnel_seq` có số thật.
- Mọi Deal đã tắt (`active=False`) đều có `probability = 0`; chỉ một phần có `lost_reason_id`. Theo quy tắc `lost` = có lý do hoặc `probability == 0` thì **mọi Deal đã tắt đều là `lost`**, trạng thái `archived` thực tế gần như không xuất hiện trên Xinyang. Với thứ tự sắp xếp thì `lost` và `archived` cùng một hạng nên không ảnh hưởng.
- Deal ở Data Funnel (Outbound Hunter, Inbound Pool) đều mang cột Match Making `1.Opportunity` (sequence 0). Theo đúng đặc tả ("Match Making khi `stage_id` có giá trị"), với các Deal này `step` (data/verified/potential) **không dùng để xếp hạng**; chỉ dùng khi Deal không có `stage_id`. Cần đổi thì báo.

## Khác so với đặc tả ban đầu (và lý do)
1. **Khóa chống tạo đồng thời dùng hai cursor mới**: cursor 1 chỉ giữ `pg_advisory_xact_lock` (đã `SET LOCAL lock_timeout = '10s'`), cursor 2 mở **sau khi** có khóa để tìm trùng và tạo Deal (quyền của chính nhân viên, không sudo). Cursor 2 commit trước, cursor 1 nhả khóa sau cùng. Không cần `SET TRANSACTION ISOLATION LEVEL` (dễ lỗi nếu Odoo đã chạy câu lệnh trước đó).
2. **Lọc sơ bộ bằng regex từng cột** thay cho cách gỡ hết ký tự không phải số (chậm khoảng 30 lần trên ghi chú dài). Không bỏ sót dạng viết nào; Python khớp lại chính xác sau đó. `description` được bỏ thẻ HTML trước khi khớp (số nằm trong thuộc tính thẻ không tính).
3. **Máy chủ tự lấy SĐT/MST từ chính `vals`** (`phone`, `x_phone`, `x_mobilephone`, `x_yp_tax_code`) và cộng với phần Extension gửi, nên gửi `phone_keys` rỗng cũng không né được kiểm tra.
4. `yp_create_lead` không có SĐT lẫn MST (cả `vals` lẫn tham số) thì trả `invalid`.
5. `yp_update_lead` ghi trong savepoint: bị từ chối thì không để lại gì.
6. **Hàm quét đọc cả bảng một lần rồi union-find** thay vì mở rộng từ hạt giống (lọc `ilike` 6 số cuối với hàng nghìn khóa chậm hơn và khó đúng): đọc theo trang 1000 Deal nên bộ nhớ không phình khi CRM lớn. Kết quả luôn là thành phần liên thông đầy đủ.
7. **`lost` và `archived` cùng một hạng khi sắp xếp** (đặc tả: Deal đang hoạt động trước, còn lại sắp theo nơi xa nhất); `state` vẫn phân biệt hai loại để hiển thị.
8. `probe` có bộ đếm riêng 30 lần/phút nên không ăn vào 30 lần kiểm tra trùng của Admin; mỗi lần gọi sai kiểu `options` không bị tính vào 6 lần quét.
9. `yp_create_lead` trả `duplicate` kèm `total` (như `yp_duplicate_check`).

## Đã test
- Offline: **225 test** của addon xanh (188 cũ + 37 mới); file `tests/test_update026_duplicate.py` có **80 test** chạy **mã thật** của `duplicate.py` / `yp_utils.py` với ORM giả: quyền theo từng Deal, Lost/lưu trữ, định dạng SĐT, MST, giới hạn tốc độ, danh sách trắng, thứ tự khóa, riêng tư của kết quả, portal bị chặn; **thứ tự cột / cắt 50 sau khi sắp / `total`**; **hàm quét S1–S8, S10** (quyền và không truy vấn gì cho người không phải Admin, trần 2000, cha đứng đầu, không lặp nhóm giữa các lô, bắc cầu SĐT↔MST, MST riêng, cắt 50 giữ Deal xa nhất, chỉ đọc, giới hạn 6/10 phút, Mark Lost). Kiểm tra bằng cách cố ý làm hỏng code (bỏ kiểm Admin, cắt trước khi sắp, đổi quy tắc `owner_id`, bỏ nối MST, bỏ trần 2000, bỏ ưu tiên Deal hoạt động, bỏ điều kiện lô): cả 7 lần đều có test đỏ.
- Trên PostgreSQL 16 thật (kết nối thật, REPEATABLE READ như Odoo, chưa có Odoo):
  - lọc SQL không sót 15 dạng số/MST; khóa hai cursor cho **đúng 1 Deal trong 240/240 lượt đua** (2 phiên; 6 phiên với 6 cách viết cùng một số; 3 phiên với các Deal mang 2 số chéo nhau; 3 phiên cùng MST); cách khóa một cursor đơn giản sai 60/60 lượt (chứng minh bài test bắt được lỗi); khóa kẹt trả `busy` sau 1 giây thay vì treo; ~110 ms/lần kiểm tra trên 6.000 Deal với ghi chú dài 1,8 KB mỗi Deal.
  - **Hàm quét (S9)**: dữ liệu mô phỏng có nhóm trùng biết trước (chuỗi 2–6 Deal, số viết đủ dạng, nằm trong phone / x_phone / ghi chú HTML / tên, 20% Deal đã tắt, nhóm chỉ trùng MST, hotline 130 Deal). **khoảng 0,5 giây** cho một lần quét 2000 hạt giống trên ~3.400 Deal (cỡ production hiện nay ~2.900 Deal), **khoảng 1,6–1,8 giây** trên ~13.000 Deal. Quét hết CRM bằng lô 2000, 997 và 137: nhóm tìm được **đúng bằng nhóm đã cài**, không nhóm nào xuất hiện hai lần, hotline cắt 130 → 50 và Deal xa nhất đứng đầu. Chưa cần hạ `max_batch` (giữ 2000).
- **Chưa chạy trên Odoo thật.** Còn phải xem trên Demo 2: `registry.cursor()` + `api.Environment` trong Odoo 19, hook tạo Deal của CRM-002 chạy trong cursor thứ hai, Chatter ghi đúng người khi cập nhật, thời gian quét trên Odoo thật (ORM thật chậm hơn SQL thuần một chút ở bước đọc 50 thành viên/nhóm).

## Cài đặt
1. Backup Demo 2. Cài thứ tự: CRM-005 Update_032 → CRM-002 Update_026 (nâng cấp module; khởi động lại Odoo để nạp mã Python).
2. Chạy các bài test dưới đây. Dùng 4 tài khoản: Admin; nhân viên phòng **Kinh doanh (MMC)**; nhân viên phòng khác (ví dụ Công nghệ (CN)); chủ của một Deal thuộc phòng khác.
3. Chỉ sau khi đạt mới phát Extension Update_021/022 cho nhân viên.
4. Gỡ: cài lại CRM-002 Update_025; **trước đó** thay Extension về bản 020-from-017 (Extension 021/022 gặp Odoo thiếu hàm sẽ chặn tạo/cập nhật).

## Bài test trên Demo 2 (gọi qua `execute_kw`, đăng nhập đúng từng tài khoản)
| # | Làm | Kết quả đúng |
|---|---|---|
| 1 | NV phòng khác (không phải chủ) `yp_duplicate_check` số của Deal X thuộc phễu họ không thấy | Có X, `can_update=false`, `is_owner=false`; `yp_create_lead` cùng số → `duplicate`, không tạo gì |
| 2 | Deal đã Mark Lost và Deal lưu trữ cùng số | Có trong kết quả, `state` = `lost` / `archived` |
| 3 | Khớp chỉ bằng SĐT, chỉ bằng MST; số `0912345678`, `+84912345678`, `+84 912 345 678`, số nằm trong ghi chú | Đều ra Deal; số nằm trong thuộc tính thẻ HTML thì không |
| 4 | NV phòng khác: `yp_read_lead`/`yp_update_lead` Deal của người khác và id không tồn tại | Cả hai `forbidden`. Chủ Deal: đọc/ghi Deal của mình được. Kinh doanh (MMC) và Admin: ghi Deal không thấy được; ghi `stage_id`, `user_id`, `tag_ids`, `sgt_crm002_funnel_id`, `sgt_crm002_step` → `invalid` |
| 5 | Hai phiên `yp_create_lead` cùng SĐT/MST **cùng lúc**, lặp ≥ 50 lần | Luôn đúng 1 Deal |
| 6 | User tạo lần thứ 6 trong 60 giây; Admin lần thứ 11; kiểm tra trùng lần thứ 31 trong phút | `rate_limit` kèm `retry_after`; sau đó làm lại được |
| 7 | Deal tạo qua `yp_create_lead` | Đúng phễu, Tag, Source như tạo tay; `create_uid` đúng nhân viên |
| 8 | Cập nhật bằng `yp_update_lead` | Chatter/Lịch sử ghi đúng người sửa |
| 9 | Đo thời gian `yp_duplicate_check` trên dữ liệu thật | Vài chục đến vài trăm ms |
| 10 | Ghi `street2, city, state_id, zip, country_id`; `street=''` | Đúng từng ô địa chỉ; xóa được dòng cũ |
| 11 | Admin `force_duplicate=True` | Tạo được Deal trùng. NV thường gửi `True` vẫn `duplicate` |
| 12 | Chủ của Deal trùng (không phải Admin) `yp_create_lead` | `duplicate`; trong `matches` Deal của họ có `is_owner=true`, `can_update=true` |
| 13 | Một lần kiểm tra số có ≥ 3 Deal ở nhiều phễu/người phụ trách (gồm 1 Lost, 1 lưu trữ) | Trả đủ, `truncated=false`, `total` = số Deal |
| A1 | Một số có Deal ở `6.Approved Match Making`, ở Data Funnel `potential`, một đã mất, một lưu trữ; kiểm tra bằng NV thường | `matches` xếp: cột 6 → … → Data Funnel → Deal đã mất/lưu trữ; mỗi Deal có `stage_seq` (6, 0…), `sale_funnel_seq` (60/70 hoặc `null`) |
| A2 | Một số dùng chung ở 120 Deal | `matches` đủ 50 Deal **xa nhất** (không phải 50 Deal ID nhỏ), `total=120`, `truncated=true` |
| S1 | Tài khoản không phải Admin gọi `yp_duplicate_scan({'probe': True})` và `yp_duplicate_scan({})`; Admin gọi với `limit=999999` | Người thường: `forbidden` cả hai, không đọc gì; Admin: `ok=true`, tối đa 2000 hạt giống |
| S2 | 1 Deal ở cột 6 + 4 Deal trùng SĐT (Data Funnel `potential`, đã mất, lưu trữ, cột 4) | 1 nhóm; `members[0]` là Deal cột 6; Deal đang hoạt động trước, đã mất/lưu trữ sau cùng |
| S3 | Quét với `limit` nhỏ (3) nhiều lần bằng `next_after_id` tới `done=true` | Mỗi nhóm đúng một lần; nhóm có thành viên ở nhiều lô vẫn đủ thành viên |
| S4 | A trùng B bằng SĐT, B trùng C bằng MST; hai Deal cùng SĐT nằm ở hai lô khác nhau | Một nhóm A, B, C; một nhóm cho hai Deal ở hai lô |
| S5 | Hai Deal khác SĐT cùng MST; hai Deal cùng SĐT khác MST | Mỗi cặp một nhóm; cờ `phone`/`tax` của thành viên đúng |
| S6 | Một SĐT dùng chung ở 120 Deal | 1 nhóm 50 thành viên xa nhất, `size=120`, `truncated=true` |
| S7 | Sau khi quét | Không Deal nào đổi `write_date`; không Chatter mới |
| S8 | Quét lần thứ 7 trong 10 phút; gọi `probe` nhiều lần | Lần 7 `rate_limit` kèm `retry_after`; `probe` không bị tính vào 6 lần |
| S9 | Đo thời gian quét 2000 hạt giống trên Demo 2 và bản sao dữ liệu thật | Báo user; > 15 giây thì hạ `max_batch` (hằng `SCAN_MAX_BATCH`) |
| S10 | Deal đã mất (và Deal ở cột có tên chứa *Mark Lost*, nếu có) | `state='lost'`, đứng sau mọi Deal hoạt động trong nhóm; không phải hạt giống |

## Việc bên Extension (chat khác, sau)
- Dùng `matches[i].can_update` / `is_owner` để hiện nút Cập nhật từng dòng (cờ `can_update` ở cấp trên chỉ để tương thích).
- Admin thêm nút "Vẫn tạo mới" gửi `force_duplicate=true`.
- Hiểu `rate_limit` kèm `reason:'busy'` như chờ rồi thử lại.
- Tab "Lọc trùng" (chỉ Admin): gọi `yp_duplicate_scan({'probe': True})` một lần; `forbidden` hoặc hàm không tồn tại → ẩn tab. Quét lặp bằng `next_after_id` tới `done`, chờ tối đa 90 giây mỗi lần quét, hiểu `rate_limit` (`retry_after`) và `invalid`.
- Extension Update_022 chỉ phát **sau** khi Demo 2 đạt các bài test ở trên.

## Giới hạn đã biết
- Chỉ khớp chính xác SĐT/MST. Không bắt trùng theo tên công ty, website, địa chỉ hay số gõ sai.
- Quét `description` và `name` có thể báo trùng nhầm (ghi chú chứa số của đối tác).
- Bộ nhận dạng SĐT lấy cả chuỗi chữ số/dấu cách/chấm/gạch liền nhau làm một số. Nếu số điện thoại dính liền một dãy số khác chỉ cách nhau bằng dấu cách, chấm hoặc gạch (ví dụ tên `Cty 123 - 0912345678`) thì cả dãy bị loại vì quá dài và Deal đó bị **sót** (cả `yp_duplicate_check` lẫn hàm quét, vì dùng chung một hàm). Số nằm riêng hoặc cách chữ cái thì bắt đúng. Cần siết thêm thì báo.
- Hàm quét: nhóm chỉ gồm Deal đã mất/lưu trữ không được liệt kê; Deal có ID nhỏ hơn `after_id` tạo trong lúc đang quét không thấy ở các lô sau (quét lại từ đầu thì thấy); hotline dùng chung gộp nhiều Deal không liên quan thành một nhóm lớn (cắt ở 50); bộ đếm 6 lần/10 phút tính theo từng tiến trình Odoo.
- Hàm quét đọc toàn bộ Deal mỗi lần gọi (SQL thuần, trang 1000): với ~3.000 Deal chỉ vài trăm ms, CRM lớn gấp nhiều lần vẫn dưới vài giây.
- Deal tạo bằng form tay, import hoặc Extension bản cũ không đi qua khóa nên vẫn có thể trùng.
- Giới hạn kiểm tra 30 lần/phút đếm trong bộ nhớ từng tiến trình nên xấp xỉ khi Odoo chạy nhiều worker.
- CRM-002 lỗi hoặc đang nâng cấp thì Extension 021 chặn mọi thao tác tạo/cập nhật (kể cả Admin).
- Phòng Kinh doanh (MMC) nhận biết theo **tên** trong Employees: đổi tên phòng thì nhóm này mất quyền cập nhật cho tới khi sửa hằng số `SALES_DEPARTMENT_NAME` trong `models/yp_utils.py`.
