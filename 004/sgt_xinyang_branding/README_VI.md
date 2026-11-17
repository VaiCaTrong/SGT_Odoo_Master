# UI-004 — XINYANG Backend Branding V01

## Mục đích
- Đổi màu chủ đạo backend Odoo 19 thành xanh #0061BD; dùng đỏ #E51922 như tông thương hiệu dự trữ/điểm nhấn, không đổi màu cảnh báo.
- Thay tên công ty hiện trên góc phải navbar bằng **đúng logo đầy đủ Xinyang (XY + 新扬 + ®)**.
- Giữ nguyên dropdown Odoo `web.SwitchCompanyMenu`, cơ chế đa công ty, button và tên `res.company` thật. Tooltip và tên thực tế cho screenreader không bị mất.
- Không tác động Website/Portal (asset chỉ nằm trong `web.assets_backend`).
- Không ghi dữ liệu `res.company`, không tạo model/field, không sửa quyền, CSS không thay card Kanban/CRM-001/MM Approval.

## Cài đặt trên Xinyang Demo 2
1. Backup database trước khi cài addon mới.
2. Giải nén ZIP, sao chép thư mục `sgt_xinyang_branding` vào addons_path.
3. Restart Odoo. Apps → Update Apps List → tìm **XINYANG | UI-004 Backend Branding** → Install.
4. Hard refresh Ctrl+Shift+R hoặc mở `?debug=assets`; xác nhận màu navbar/nút New và logo tại vị trí tên công ty.
5. Kiểm tra menu chuyển công ty bằng tài khoản có >=2 công ty (nếu hệ thống chỉ có 1 company, nút có thể disabled mặc định Odoo).
6. Kiểm tra CRM, Employees, Discuss, MM Approval, Dashboard. Kiểm tra website công khai không đổi.

## Ghi chú
- Logo nguồn dọc, nên ở navbar 46px phần chữ 新扬 sẽ nhỏ. Asset `xinyang_full_logo.png` là ảnh gốc được cắt khoảng trắng bên ngoài, không xóa dấu ® hay chữ. `xinyang_original.png` là ảnh gốc không chỉnh sửa.
- Nếu đang có một theme backend khác, cần xem thứ tự override SCSS khi kiểm tra thực tế.
- Gỡ addon trả các asset/view template về hành vi gốc của Odoo sau restart/cập nhật bundle; KHÔNG chỉnh `res.company.logo` hoặc `res.company.name`.
- Chưa được kiểm chứng install/runtime trên xinyangdemo2.sge.vn; đây là gói offline để thử trên staging.
