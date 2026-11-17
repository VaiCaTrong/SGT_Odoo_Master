# CRM-002 — V01 Update_003 (Demo 2)

**Đây là bản nâng cấp, không phải addon mới.** Module kỹ thuật vẫn là `sgt_crm_campaign`; manifest `19.0.1.2.0`. Chỉ kiểm thử trên Xinyang Demo 2 trước Production.

## Thay đổi thực hiện

1. **Kanban chuẩn Odoo:** Cả bốn Data Funnel sử dụng view `sgt_crm_campaign.view_crm002_intake_kanban` (primary inherited từ `crm.crm_case_kanban_view_leads`). Không sao chép bất kỳ HTML/QWeb card nào, không CSS chỉnh kích thước/font thẻ. Tiếp tục nhận các thẻ tùy chỉnh từ View Xinyang và CRM-001. Kanban chia cột theo `sgt_crm002_step`, *không ghi* `crm.lead.stage_id` khi đổi Data/Verified.
2. **New:** dùng tạo Deal/Form chuẩn CRM, mặc định tiếp nhận vào phễu được chọn và bước `1.Data`. Addon gắn Tag/Source tương ứng khi tạo thủ công trong phễu. Quyền tạo Deal vẫn phụ thuộc CRM ACL gốc; không nâng quyền User.
3. **Chỉ Deal mới:** Chỉ trong `crm.lead.create()` mới tự đối chiếu Tag hoặc Source hiện được cấu hình. Bản ghi cũ chỉ mang Tag hunter/pool/... **không** được nhập lại. Dữ liệu `sgt.crm002.progress` sinh tự động bởi Update_001/002 vẫn lưu; `intake_active` mặc định `False` trên dữ liệu cũ; không xóa bất kỳ bản ghi `crm.lead`.
4. **Bàn giao Potential:** Native Kanban kéo từ `1.Data`/`2.Verified` sang `3.Potential` gọi `crm.lead.write()` để xử lý; backend xác minh quyền, ghi thời gian, kết thúc tiến trình (`intake_active=False`), xóa `sgt_crm002_funnel_id`, `sgt_crm002_step` của lead, và đưa **cùng Deal** sang CRM Stage `4.Opportunity` nếu chưa tiến xa hơn. Deal rời Data Funnel tức thì, Tag gốc vẫn tồn tại. Cột Potential là cột giao nhận, thường không có Deal tồn đọng.
5. **Pipeline chính:** Chỉ thay domain của **action** `crm.crm_lead_action_pipeline` để ẩn Deal đang nằm trong hàng đợi tiếp nhận. **Không thay `crm.lead` ACL/Record Rules**, không sửa action riêng của MM Approval, không sửa code CRM-001.
6. **Sidebar:** `CRM Campaign → Data Funnel / Match Making Campaign` có nút mở/đóng. Administrator có SALESPERSON Departments/Employees; User thông thường không thấy. Nút cấu hình chuyển đến list/form chuẩn của Odoo (cả Tag/Source và danh sách Department được phép xem), không dùng popup tự viết để tránh Owl `ctx.String`.
7. **Mốc nâng cấp:** không backfill, không quét dữ liệu lịch sử. Queue bắt đầu bằng Deal mới tạo **sau Upgrade**. Trong các bản ghi tiến trình cũ, chỉ bổ sung field mới; không xóa lịch sử hay bản ghi Deal. Nếu bạn đã kéo Deal thực tế trên V01/002, hãy lưu ý thay đổi trạng thái CRM main đã xảy ra trước V03 sẽ không được đảo ngược.

## Model/field CRM-002 mới trong Update_003

| Model | Field | Loại | Chức năng |
|---|---|---|---|
| `crm.lead` (kế thừa, không tạo model) | `sgt_crm002_funnel_id` | Many2one `sgt.crm002.funnel`, indexed | ID phễu đang tiếp nhận; False nếu đã bàn giao hoặc chưa vào phễu |
| `crm.lead` | `sgt_crm002_step` | Selection `data,verified,potential`, indexed, group_expand | Group 3 cột Kanban Odoo |
| `sgt.crm002.progress` (đã tồn tại từ V01) | `intake_active` | Boolean (default False) | Phân biệt tiến trình V03 hợp lệ với tiến trình V01/002 tự khởi tạo từ dữ liệu cũ |
| `sgt.crm002.progress` | `intake_created_at` | Datetime | Thời điểm bắt đầu tiếp nhận |
| `sgt.crm002.progress` | `completed_at` | Datetime | Thời điểm giao nhận Potential |

Tất cả mang mã sở hữu **CRM-002**. Field/model được đối chiếu với Scan Xinyang 2026-10-11 và các model đã có trong bản Update_002. Scan cũ không thể thay kiểm tra registry hiện tại của Demo 2.

## Cách Upgrade — CHỈ DEMO 2

1. Sao lưu database, chụp nhanh thư mục `/mnt/extra-addons/sgt_crm_campaign` đang hoạt động và xuất dữ liệu test quan trọng.
2. Giải nén ZIP, thay *đúng thư mục* `sgt_crm_campaign` ở addon path; không để nhiều bản trùng module cùng đường dẫn. **Restart Odoo service** để nạp file Python mới.
3. Apps → Update Apps List → tìm `SGT CRM-002` → **Upgrade** (KHÔNG uninstall/reinstall).
4. Hard refresh trình duyệt (`Ctrl+Shift+R` hoặc `?debug=assets`), vào **CRM → Sales → Pipeline**. Sidebar ở trái, Pipeline chính dùng chính Kanban gốc.
5. Admin mở phễu `Outbound hunter` khi vừa Upgrade, phải **không tự hiện lại 100 Deal hunter cũ**.
6. Admin nhấn **New**, tạo Deal thử `CRM002 TEST A` trong Outbound hunter → `1.Data`. Kéo sang `2.Verified` rồi `3.Potential`. Deal phải mất khỏi phễu, xuất hiện tại `4.Opportunity` trong Match Making, cùng `crm.lead.id`, cùng Chatter/Tag/contact.
7. Admin kiểm tra `Cấu hình phễu`, `Phân quyền phễu` (form chuẩn của Odoo); kiểm tra department filter/nhân viên; bấm nhóm cha để thu gọn/mở rộng.
8. Login User thuộc MMC: không thấy SALESPERSON và Data Funnel nếu chưa cấp quyền; User vẫn được xem qua CRM gốc theo quyền cũ (phương án A).
9. Kiểm tra CRM-001 badges ở Pipeline gốc, kiểm tra MM Approval gốc, sau đó kiểm tra trường hợp đổi Stage/đặt Tag trên Deal **cũ** không khiến nó tự quay về Data Funnel.

### Lưu ý và giới hạn

- Chưa có quyền truy cập runtime Odoo Demo 2, PostgreSQL của Demo 2 hoặc UI để chạy Upgrade end-to-end. Đã kiểm tra offline: syntax Python/JS, XML, view inheritance targets trong Scan, 8 timing tests và 8 structural contract tests. **Không cam kết thành công >99% trước khi thử thật.**
- Kanban CRM-001 vẫn tính nhãn Stage-days dựa vào **Stage chính của CRM**, không phải 1.Data/2.Verified. CRM-002 lưu lịch sử visit cho bước Intake nhưng chưa thay đổi chỉ số CRM-001 trên thẻ, nhằm giữ đúng thiết kế và không can thiệp addon CRM-001. Nếu yêu cầu hiển thị tuổi riêng theo Data/Verified ngay trên badge hiện có, cần quyết định cách tích hợp với CRM-001 trong vòng kiểm thử tiếp.
- Chuyển vào Potential xác định Stage đích theo tên **`4.Opportunity`** và Team thực tế, không hard-code ID. Nếu mơ hồ (hai Stage cùng tên/team), backend báo lỗi và rollback giao dịch.
- Một Deal mới khớp nhiều phễu Tag/Source chỉ được đưa vào **một** phễu, ưu tiên `sequence`/ID cấu hình; không nhân bản.
- Nếu lỗi Owl/ParseError/RPC_ERROR, gửi traceback đầy đủ và hành động vừa bấm, đặc biệt khi lần đầu mở native intake Kanban.
