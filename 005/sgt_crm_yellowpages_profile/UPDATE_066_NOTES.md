# CRM-005 Update_066 — Image Gallery: chọn nhiều ảnh để xóa hàng loạt (chỉ chế độ debug)

Nền: Update_065 (19.0.1.64.0). Manifest: 19.0.1.65.0. Không field/cột mới, không migration, không đổi view XML.

## Yêu cầu (user 14/11 21:39)
Khi bật debug, mỗi ảnh Gallery có nút × xóa từng ảnh. Muốn bấm chọn nhiều ảnh rồi xóa hàng loạt.
Phạm vi đã chốt: **chỉ Image Gallery** (không Partners, không Evidence).

## Cách dùng (chỉ khi bật debug, giống nút × hiện nay)
1. Trên Deal, phía trên Image Gallery có thanh **☐ Select images**. Bấm vào để vào chế độ chọn.
2. Trong chế độ chọn: nút × ẩn, mỗi ảnh có ô vuông ở góc. Bấm ảnh để tick / bỏ tick; **Shift+bấm** tick cả dãy từ ảnh vừa chọn gần nhất.
3. Thanh hiện: `N selected`, **Select all (tổng)**, **Clear**, **🗑 Delete selected (N)** (đỏ, mờ khi N = 0), **Done**.
4. Bấm Delete selected → hộp xác nhận "Delete the N selected pictures… cannot be undone" → xác nhận mới xóa, rồi trang tải lại.
- Người dùng không bật debug: không thấy thanh, không thấy ×, bấm ảnh vẫn mở khung xem ảnh như cũ.
- Ngoài chế độ chọn: nút × xóa từng ảnh và khung xem ảnh (lightbox) giữ nguyên.

## Máy chủ
`crm.lead.action_crm005_delete_gallery_images(indexes, source_prefixes, expected_count)`:
- Cần quyền **sửa** Deal (`check_access('write')`) — debug chỉ để hiện nút, quyền thật do máy chủ giữ.
- Kiểm: 2 danh sách cùng độ dài, 1–500 ảnh, chỉ số là số nguyên ≥ 0 không trùng (không nhận bool/chuỗi/số thực), dấu vân tay ≤ 128 ký tự, tổng ảnh khớp
  `expected_count`, chỉ số không vượt tổng, và **từng** ảnh khớp 128 ký tự đầu của `src`. Sai bất kỳ điều gì: báo lỗi, **không ghi gì**.
- Xóa mọi ảnh đã chọn rồi **ghi một lần duy nhất**. Trả về số ảnh đã xóa.
- Dùng chung hàm `_crm005_remove_gallery_node` với xóa từng ảnh (tách ra từ code cũ, hành vi không đổi): xóa cả `<figure>` khi figure chỉ chứa ảnh đó,
  dọn các `p/div/span/a` rỗng, giữ chữ/chú thích khác.

## Giao diện (`gallery_manage.js/.xml`, SCSS)
- Gallery có thể nặng nhiều MB: kết quả xử lý HTML được nhớ lại (cùng HTML ⇒ cùng đối tượng), tick ảnh chỉ đổi class trên DOM, **không** phân tích lại HTML.
- Thanh là thẻ `<section>` con trực tiếp của gốc field (CSS gallery làm phẳng `p/div/span/a`, nên không dùng các thẻ đó).
- CSS chế độ chọn dùng `.sgt_yp_select_mode …` không đòi tổ tiên `.sgt_yp_gallery`, vì gốc field mang cả hai class.

## Lỗi tự bắt được khi test trình duyệt thật (đã sửa trước khi giao)
1. Getter của template OWL chạy trên ngữ cảnh kế thừa component: gán `this._memo = …` trong getter chỉ tạo bản sao tạm ⇒ "Select all" ra 0 và HTML bị phân tích lại mỗi lần vẽ. Sửa: `Object.assign(this._memo, …)`.
2. CSS `.sgt_yp_gallery .sgt_yp_select_mode …` không khớp vì gốc field vừa là `.sgt_yp_gallery` vừa là `.sgt_yp_select_mode` ⇒ nút × không ẩn, ô tick không hiện. Sửa selector.

## Kiểm thử (offline, KHÔNG chạy Odoo 19 thật)
- `tests/test_update066_bulk_delete.py` (17): chạy **hàm thật** trên fake ORM trả `Markup`: xóa nhiều trong 1 lần ghi, thứ tự chỉ số bất kỳ, xóa hết, ảnh trong `<p>`, figure 2 ảnh,
  kết quả bằng xóa lẻ lần lượt, không escape Markup, từ chối (không quyền, sai tổng, sai vân tay 1 ảnh, vượt chỉ số, 13 kiểu payload sai, quá 500, HTML rỗng) và luôn không ghi.
- `tests/test_update066_contract.py` (11): chỉ debug, `<section>` con trực tiếp, nút `.stop`, payload RPC, không gọi RPC trước khi xác nhận, memo không gán lại, CSS không đòi tổ tiên, 8 field như cũ, giới hạn 500 của giao diện = máy chủ (chọn quá 500 thì báo, không gọi RPC).
- Mutation phía máy chủ: 7/7 kiểu làm hỏng (bỏ quyền ghi, bỏ vân tay, bỏ kiểm tổng, bỏ kiểm trùng, bỏ giới hạn 500, nhận bool, ghi 2 lần) đều có test đỏ.
- Chromium thật + OWL 2 + JS/XML thật + SCSS biên dịch thật (script `pg_gallery_select_test.py`, 41 kiểm tra): không debug không có gì mới và lightbox vẫn mở; debug có thanh; vào/thoát chế độ chọn; tick, bỏ tick, Shift+bấm dãy, Select all, Clear; không mở lightbox trong chế độ chọn; DOM không bị chèn lại; payload `[id], [0,2,5], vân tay, tổng`; không gửi gì trước khi xác nhận; RPC lỗi giữ nguyên lựa chọn và thử lại được; Done; Gallery rỗng không có thanh; không lỗi console. Mutation (gán lại memo) bị bắt.
- `test_update062_compact_footer` ghim hash `models/crm_lead.py` — đã ghim lại theo file mới. Các test cũ khác giữ kết quả y hệt Update_065 (test kanban cần `/mnt/data/...` fail ở cả bản gốc, có từ trước).

**Chưa chạy trên Odoo 19 thật:** hộp xác nhận thật, sanitizer Html, quyền theo user thật.
