# CRM-002 Update_016 (19.0.1.12.0) — chặn vào cột 5 khi thiếu dữ liệu, chuông, số ngày ở stage

**Cài trên Demo 2 trước.** Chưa chạy trên Odoo thật (xem mục "Chưa kiểm chứng").

## Làm gì
1. **Chặn chuyển vào `5.Match Making` / `6.Approved Match Making` khi Deal thiếu dữ liệu bắt buộc** (server, mọi cách chuyển: kéo thả Kanban, bấm thanh stage trên form, import). Hiện hộp thoại lỗi chuẩn của Odoo, liệt kê trường thiếu bằng tên người dùng quen; Deal ở nguyên stage cũ. Admin cũng bị chặn. Luật chuyển giao (hand-off) và phễu Data/Sale không bị ảnh hưởng.
   - Danh sách bắt buộc (mặc định): **Phone** (`phone`), **Email** (`email_from`), **Industry** (`x_fb_industry`). Sửa ở `models/timing.py` → `MM_REQUIRED_FIELDS`. Trường không có trong database thì bị bỏ qua, không báo thiếu.
   - Stage bị chặn: đúng tên `5.Match Making`, `6.Approved Match Making` (`MM_GUARD_STAGE_NAMES`, không khớp mờ).
2. **Chuông** thiếu dữ liệu: đỏ kèm số trường thiếu (Kanban) / chỉ chuông (List, form); xanh khi đủ. Rê chuột hiện tên trường thiếu (Kanban: tooltip Odoo; form và List: CSS thuần, không JS). Chuông trên form nằm cạnh tên Deal (icon bánh răng nằm trong thanh điều khiển của Odoo, arch form không với tới nếu không viết JS).
3. **Thanh ngang Kanban theo số ngày ở stage**: xanh 0–3, vàng 4–7, đỏ >7 ngày; **số Deal trong từng đoạn** và **tổng Deal ở đuôi thanh** (mở rộng template `web.ColumnProgress`, chỉ áp dụng cho thanh này; không JS). Deal Won (xác suất 100) không tô màu. Bấm vào đoạn màu vẫn lọc như cũ.
4. **Thẻ Kanban**: bỏ viền màu trái (chưa từng thêm); nhãn "Nd" tô màu thay cho nhãn rotting gốc; chuông cạnh nhãn.
5. **List**: cột "Days in Stage" (số + "d", màu), cột chuông "Data", nền dòng vàng/đỏ theo ngày + vạch màu trái.

## Field mới (đã nói rõ khi hỏi, user "triển")
| Field | Loại | Ghi chú |
|---|---|---|
| `sgt_crm002_stage_since` | Datetime **có lưu** (1 cột mới) | Lần đổi stage gần nhất ở bất kỳ phễu nào (stage CRM, bước Data, stage Sale). Deal cũ để trống → dùng `date_last_stage_update`, rồi `create_date`. |
| `sgt_crm002_age_days` | Integer, **không lưu** | Số ngày nguyên. |
| `sgt_crm002_age_bucket` | Selection, **không lưu** | fresh / warn / late; nhóm bằng `_read_group_groupby` (SQL CASE) nên **không cần cron**. |
| `sgt_crm002_missing_info` | Char, **không lưu** | Nhãn trường thiếu, rỗng = đủ. |

Không model mới, không cron, không file JS mới (manifest vẫn 2 file JS cũ). 2 file mới: `views/lead_age_bell.xml`, `static/src/xml/column_progress.xml` (template), `static/src/scss/age_bell.scss`.

## Đếm ngày
Đồng hồ chạy lại mỗi lần Deal đổi stage: stage CRM (kéo thả/form), bước phễu Data, stage phễu Sale. Một Deal nằm ở nhiều phễu dùng chung 1 đồng hồ (lần đổi gần nhất).

## Không làm (đã nói)
Chuông / thanh số ngày chỉ ở Kanban và List chuẩn của Match Making (view CRM chuẩn); Kanban phễu Data/Sale của CRM-002 (`intake_kanban.xml`) chưa gắn. Chuông chưa nằm ngang icon bánh răng (xem mục 2).

## Chưa kiểm chứng (cần Demo 2)
- Odoo 19 nhận `_read_group_groupby` cho field không lưu (như `activity_state`) → thanh ngày; nếu không, thanh trống hoặc lỗi khi mở Kanban (gỡ bằng cách trả `colors` về activity_state).
- Mở rộng template `web.ColumnProgress` (nếu sai xpath, Odoo báo lỗi khi tải assets: kiểm tra màn hình đăng nhập/CRM mở được).
- Xpath trên view Kanban CRM chuẩn đã được người dùng sửa tay (`rotting_days`, `progressbar`, `stage_id`).
- CSS-only: tooltip chuông trên form / List, nền dòng bằng `:has()` (Chrome 105+).
- Chặn kéo thả: hộp thoại lỗi và thẻ quay về cột cũ; import có thông báo ở dòng lỗi.
- Test offline: 9 file test xanh (`test_update016_age_guard.py` 22 test: guard chạy code thật với dữ liệu giả, buckets, xpath khớp view production Scan).
