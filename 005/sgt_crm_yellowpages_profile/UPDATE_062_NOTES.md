# CRM-005 Update_062 — Kanban footer compact (14/11/2026)

## Nền cập nhật
Dựa trên CRM-005 Update_061 (`19.0.1.60.0`); phát hành `19.0.1.61.0`.

## Thay đổi chính
- Đưa Source vào **footer gốc** của Kanban, giữ ở **bên trái**.
- Giữ nguyên widget thông báo/chuông (`rotting_days`) và avatar Salesperson (`user_id`) của Odoo ở **bên phải**, ngang hàng Source.
- Đặt hàng Website / Facebook / Trang Vàng / Zalo / Documents **ngay dưới** hàng Source, căn trái; tự ẩn các liên kết chưa có dữ liệu/quyền.
- Thu gọn khoảng cách, bỏ nhóm trống Priority/Activity ở footer đã bị ẩn từ Update_061.
- Không thay đổi cách xử lý khi nhấp icon, điều hướng Ctrl/Cmd + Click, kéo Deal, nút New hoặc phân quyền.

## Phạm vi kỹ thuật
- `views/crm_yp_lead_kanban.xml`: thêm một class vào footer gốc qua XPath; chèn Source `position=inside`; chèn shortcuts `position=after`. Không thay thế/xóa footer hoặc các khối Facebook/Website trong view cha.
- `static/src/css/kanban_safe_links.css`: CSS scoped vào `.o_opportunity_kanban`/`.sgt_crm005_compact_footer` để căn trái/phải và thu khoảng trống.
- `__manifest__.py`: nâng phiên bản.
- Các file `models/*.py`, các JS, Geolocation, Documents, Gallery giữ nguyên byte so với Update_061 (không thêm field, không có migration).

## Kết quả kiểm tra offline
- Python unittest: 157 bài; 122 đạt, 35 bỏ qua do môi trường/test cũ. 0 thất bại.
- XML parse: hợp lệ. XPath kiểm trên scan cơ sở và biến thể không có khối Facebook/Website cũ: đạt.
- Chromium mock (không phải giao diện Production): Source và chuông/avatar cùng hàng, icon nằm hàng dưới, thẻ gọn.
- Chưa kiểm thử Upgrade và hành vi trên Odoo xinyang.sge.vn. Cần staging/clone trước Production.

## Nâng cấp và nghiệm thu
1. Sao lưu DB `xinyang` và thư mục CRM-005 hiện tại.
2. Thay **toàn bộ** module `sgt_crm_yellowpages_profile` bằng gói này (không giải nén chồng).
3. Restart Odoo, Upgrade module, làm mới asset trình duyệt (`Ctrl+Shift+R`).
4. Kiểm tra Deal đủ link và Deal ít link: Source nằm trái, icon chuông + Salesperson nằm phải **ngang Source**, link nằm dưới bên trái.
5. Kiểm tra menu ba chấm/chọn màu, click thường, Ctrl/Cmd+Click, New, drag/drop, Documents permissions, Zalo, Website/Facebook/Trang Vàng, Geolocation và Gallery.
6. Nếu view Production có thay đổi chưa được bao phủ, khôi phục Update_061 hoặc bản stable phù hợp và Upgrade lại; không Uninstall module.
