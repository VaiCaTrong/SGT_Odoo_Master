# CRM-002 Update_020 (19.0.1.16.0) — sửa tooltip chuông hiện sai chữ

Lỗi (2026-10-28 14:38): rê chuột vào chuông thấy "Dữ liệu" thay vì danh sách trường thiếu. Nguyên nhân: icon `<i fa-bell>` có `title="Dữ liệu"` đè `title` của thẻ cha. Sửa: bỏ `title` trên 4 icon, giữ `role`/`aria-label`.
