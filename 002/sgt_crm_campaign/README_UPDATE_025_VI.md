# CRM-002 Update_025 (19.0.1.21.0) — bỏ chặn cột 5, ô thiếu tự đỏ ở cột 5/6, thêm Evidence

Yêu cầu user 2026-10-31 08:32–08:38 (mô phỏng E1–E4), duyệt 08:50 ("Oke nhé, hãy cập nhật"):
- **Bỏ chức năng chặn chuyển vào `5.Match Making` / `6.Approved Match Making`** (Update_016–024): không còn hộp lỗi "Không thể chuyển sang ...". Kéo thẻ, bấm thanh stage, import đều chuyển được dù thiếu dữ liệu.
- **Chuông giữ nguyên**: đỏ kèm số khi thiếu, xanh khi đủ (Kanban, List, form).
- **Evidence là mục thứ 7** của danh sách thiếu: Deal chưa có ảnh trong box Evidence (CRM-005 Update_032, field `x_yp_evidence_html`) bị tính là thiếu. Kiểm mềm: không cài CRM-005 thì không tính, CRM-002 KHÔNG phụ thuộc CRM-005.
- **Tự đỏ**: mở Deal đang ở cột 5 hoặc 6 → mọi ô thiếu (Contact, Email, Phone, Source, VN Odoo ID, Address) và box Evidence tự viền đỏ, không cần bấm chuông. Điền ô / dán ảnh xong thì ô đó hết đỏ ngay. Ở cột khác: bấm chuông mới đỏ (như cũ).

Kỹ thuật:
- `models/crm_lead.py`: xoá `_sgt_crm002_check_stage_requirements` và lời gọi trong `write`; `_compute_sgt_crm002_missing` thêm Evidence (có ảnh = Html chứa `<img`); field mới KHÔNG lưu `sgt_crm002_gate` (Boolean tính, True khi stage là 5/6) — duyệt 08:50, không thêm cột DB.
- `models/timing.py`: `EVIDENCE_FIELD`, `evidence_missing()`, `in_gate_stage()`.
- `views/lead_age_bell.xml` (form): span `sgt002-gate-on` (chỉ có khi ở cột 5/6), cờ `sgt002-miss-evidence` (CSS quyết định có đếm hay không).
- `static/src/scss/age_bell.scss`: viền đỏ khi `:has(.sgt002-gate-on)` hoặc bấm chuông; box `.sgt_yp_evbox` không có ảnh = đỏ; số trên chuông đếm cả Evidence. Không JS, không API, không cron.

Lưu ý:
- Sau khi dán ảnh nhưng CHƯA Lưu: box hết đỏ và số chuông giảm ngay; nếu Evidence là mục thiếu duy nhất thì chuông có thể hiện "0" đỏ cho tới khi Lưu (Lưu xong chuông xanh).
- Kanban/List: chuông đỏ có thêm "Evidence" trong danh sách khi rê chuột / cột Data.
- Cài **CRM-005 Update_032 trước**, rồi CRM-002 Update_025 (cài ngược lại vẫn chạy, chỉ là Evidence chưa được tính cho tới khi có CRM-005).

Test: `test_update016_age_guard.py` (thêm `Update025Tests` 8 test chạy code thật của 2 hàm compute + test view/SCSS; bỏ test chặn cũ); 9 file xanh; Sass biên dịch OK; Playwright với CSS thật của cả 2 addon: cột 4 không đỏ, cột 5 tự đỏ ô Phone + box Evidence (chuông 2), dán ảnh → box hết đỏ (chuông 1), bấm chuông ở cột 4 vẫn đỏ. CHƯA chạy trên Odoo thật (Demo 2).
