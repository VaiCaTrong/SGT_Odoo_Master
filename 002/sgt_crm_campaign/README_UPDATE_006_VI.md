# CRM-002 V01 Update_006 — Một Deal, hai vị trí hiển thị

**Addon:** `sgt_crm_campaign` — **phiên bản:** `19.0.1.5.0`

## Yêu cầu đã triển khai

- Khi Deal được kéo đến `3.Potential` ở **Data Funnel**, tiếp tục giữ chính `crm.lead.id` đó tại cột `3.Potential`, **không xóa** liên kết với phễu.
- Cùng Deal xuất hiện tại `4.Opportunity` trên CRM Pipeline của **Match Making Campaign**; các lần chuyển tiếp tiếp theo trong Pipeline không làm Deal rời `3.Potential`.
- **KHÔNG** `copy()` hoặc tạo thêm bản ghi `crm.lead`. Dữ liệu, Chatter, người phụ trách, Tag... là một bản ghi chung.
- Việc bàn giao chỉ xảy ra một lần. Yêu cầu `Potential` lặp lại không đưa Deal từ Stage cao hơn về `4.Opportunity`; kéo ngược Deal đã bàn giao về `1.Data`/`2.Verified` bị chặn ở backend.
- Chỉ Deal được tiếp nhận **mới** mới hiện trong Data Funnel; không quét lại toàn bộ Deal lịch sử theo Tag/Source.
- Thẻ Kanban kế thừa View chuẩn Xinyang/Odoo; giữ nút **New**, Sidebar, phân quyền Department/Admin/SALESPERSON và CRM-001.

## Cơ chế dữ liệu

- `crm.lead.sgt_crm002_funnel_id`: vẫn trỏ tới Data Funnel nguồn.
- `crm.lead.sgt_crm002_step = 'potential'`: lưu bước cuối Data Funnel.
- `crm.lead.stage_id`: Stage pipeline độc lập (4.Opportunity hoặc các bước tiếp theo).
- `sgt.crm002.progress.completed_at`: thời điểm bàn giao; `intake_active=False` có nghĩa là **đã xử lý**, không có nghĩa ẩn khỏi cột Potential.

## Phục hồi handoff từ Update_003–Update_005

Script nâng cấp `upgrades/19.0.1.5.0/post-10-restore-potential.py` chỉ khôi phục liên kết với Data Funnel cho Deal có **đúng một** tiến trình thực sự hoàn tất (`completed_at IS NOT NULL`, `stage_key=potential`), `crm.lead` chưa được gán phễu khác và đang là Opportunity. Bản ghi lịch sử chưa từng hoàn tất hoặc có nhiều phễu không rõ ràng bị bỏ qua. Script **không sửa Stage CRM, không tạo/xóa Deal**. Cần backup database trước Upgrade.

## Triển khai trên môi trường Demo 2

1. Backup DB `xinyangdemo2` cùng thư mục addon cũ.
2. Thay thư mục `sgt_crm_campaign` bằng bản Update_006; tránh hai addon cùng tên ở nhiều addon paths.
3. Restart Odoo, vào **Apps → Update Apps List → SGT CRM-002 → Upgrade**. **Không Uninstall**.
4. Hard refresh `Ctrl+Shift+R`.
5. Tạo Deal mới trong Outbound hunter hoặc theo Tag hunter: `1.Data → 2.Verified → 3.Potential`.
6. Đảm bảo cùng ID hiển thị ở **hai** Kanban; kéo Deal đó sang `5.Connected` bên Pipeline và xác nhận vẫn còn ở `3.Potential` bên Data Funnel.
7. Thử kéo ngược từ Potential; phải nhận thông báo từ chối nhưng các thay đổi trước vẫn còn.
8. Đối chiếu Deal cũ có Tag hunter (không được xuất hiện chỉ vì Tag), các Deal cũ đã từng bàn giao (chỉ khôi phục nếu có chứng cứ `completed_at`).
9. Kiểm tra quyền User/Administrator, CRM-001 badges, nút New và MM Approval không bị thay đổi.

**Giới hạn kiểm thử:** Các bài kiểm thử Python ngoại tuyến sử dụng giả lập ORM và kiểm tra cấu trúc, không thể thay thế bước cài đặt và chạy thực tế trên Odoo 19 + PostgreSQL.
