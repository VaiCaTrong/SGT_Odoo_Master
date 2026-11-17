# CRM-002 Update_022 (19.0.1.18.0) — chuông form: hiện SỐ, đưa lên trên tiêu đề

Báo lỗi (2026-10-28 15:45): tooltip tên trường bị bóp hẹp/cắt, chuông bị ribbon WON che.
- Bỏ hẳn tooltip tên trường. Chuông đỏ chỉ hiện số trường còn thiếu (đếm bằng CSS counter trên các span cờ `.sgt002-miss`, chỉ tồn tại khi trường trống nên số cập nhật ngay khi nhập). Bấm chuông vẫn làm viền đỏ các ô trống.
- Chuông nằm trên một dòng riêng PHÍA TRÊN tên Deal (xpath `before` div đầu của `oe_title`), không còn ở đầu phải dòng tiêu đề nơi ribbon Won/Lost đè lên.
- Chuông xanh (đủ dữ liệu) vị trí tương tự. Không JS, không field mới. Test: `test_update022_form_bell_is_a_number_above_the_title`; đã thử CSS counter trên Chromium (0/3 trường).
