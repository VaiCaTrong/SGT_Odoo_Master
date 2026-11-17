# CRM-002 Update_030 — Hiển thị số Deal trên thanh màu ở các phễu mới

## Nền và phạm vi
- Chỉnh **trực tiếp trên CRM-002 Update_029** người dùng cung cấp; không lấy Update_025 cũ.
- Data Funnel / Sale Funnel dùng `kanbanView` → template `web.ColumnProgress`.
- Pipeline CRM cũ dùng `crmKanbanView` → template `crm.ColumnProgress`.
- Update_029 đã chỉ có số đếm trong `crm.ColumnProgress`, nên phễu mới không thấy số.

## Thay đổi
1. `static/src/xml/column_progress.xml`: giữ nguyên extension của `crm.ColumnProgress`, bổ sung extension tương ứng cho `web.ColumnProgress` với bộ lọc bucket `fresh/warn/late`. Mỗi đoạn màu hiển thị `bar.count`, tổng bên phải thanh hiển thị `props.group.count`.
2. `__manifest__.py`: 19.0.1.25.0 → 19.0.1.26.0 để Odoo nâng cấp assets.
3. `tests/test_update016_age_guard.py`: cập nhật kiểm tra hai renderer; thêm `tests/test_update030_progress_labels.py` bảo vệ nguồn thanh tuổi Deal và cấu trúc xpaths.

## Giữ nguyên
- Không đổi Odoo model, SQL, ACL, data funnel, chuyển stage, hay Kanban cards.
- Không đổi `age_bell.scss` vì style `.sgt002-seg-count` và `.sgt002-bar-total` đã tồn tại và áp dụng với cả hai renderer.
- Không ảnh hưởng các progressbar không có các giá trị bucket `fresh`, `warn`, `late`.

## Cài đặt
1. Sao lưu database và thư mục addon hiện tại.
2. Thay đúng addon `sgt_crm_campaign` (CRM-002), không phải CRM-005.
3. Restart Odoo, Upgrade CRM-002, Ctrl+Shift+R / xoá asset cache nếu cần.
4. Kiểm tra Data Funnel (Data / Verified / Potential), Sale Funnel (New / Renew), Pipeline CRM cũ và Match Making. So sánh số đoạn màu và tổng cột theo dữ liệu thực.

## Kiểm thử
- 277 unittest hoàn tất: **276 thành công, 1 bỏ qua** (bài quét yêu cầu file Odoo Production).
- Một test mock CRM-002 Update_026 cần mô phỏng thư viện `psycopg2` trong môi trường sandbox không có PostgreSQL; stub chỉ được dùng khi test, **không** được đưa vào module ZIP.
- Tất cả XML đều parse được, tất cả Python compile, JavaScript đã kiểm tra cú pháp.
- Chưa có Odoo Production runtime trong sandbox; số liệu và giao diện Production cần được xác nhận sau upgrade.
