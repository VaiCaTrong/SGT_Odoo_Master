# CRM-002 Update_021 (19.0.1.17.0) — tooltip chuông form không bị cắt + bỏ ô "Nd" thừa trên thẻ Kanban

Báo lỗi (2026-10-28 14:45, 2 ảnh):
1. Form: tooltip của chuông (hộp đen "Thiếu dữ liệu: ...") mở sang phải nên bị mép phải của form cắt, chỉ thấy "Thi". Sửa: tooltip mở sang TRÁI (`right: 0`), xuống dòng được (`max-width: 280px`, `white-space: normal`).
2. Kanban: ô "11d" thừa trên thẻ (thanh màu của cột đã thể hiện số ngày). Đã bỏ ô này khỏi thẻ; chuông giữ nguyên. Đồng thời xoá luật CSS global `.sgt002-age` (thêm ở Update_016) vì trùng tên class với nhãn ngày sẵn có trong màn hình workspace (`static/src/xml/workspace.xml`) và làm nhãn đó đổi kiểu. List vẫn có cột ngày + tô dòng.
Test: `test_update021_no_age_badge_on_card_and_no_global_age_class`.
