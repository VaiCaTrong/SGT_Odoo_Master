# CRM-002 Update_029 (19.0.1.25.0) — app CRM luôn hiện icon với mọi nhân viên nội bộ; Sales = No bấm vào ra trang trống

## Yêu cầu (user, 02/11 ~15:50, Demo 2)
"Thay vì ẩn luôn cả CRM khi không có quyền thì tôi muốn vẫn để đó nhưng bấm vào CRM thì không có dữ liệu."

## Nguyên nhân (Odoo gốc ẩn cả app)
- Menu gốc **CRM** (`crm.crm_menu_root`) chỉ cho nhóm Sales: Own Documents Only và Administrator. Tài khoản Sales = No không thuộc nhóm nào nên Odoo bỏ luôn icon CRM; Update_028 làm trang trống đúng rồi nhưng không có đường vào.
- Odoo 19 chỉ hiện một thư mục menu khi bên dưới có menu hành động mà người dùng mở được, và menu gốc không có hành động riêng thì không được tính. Nên chỉ thêm nhóm vào menu gốc là chưa đủ.
- Phát hiện thêm: server action `action_crm002_landing` (từ Update_011) không khai nhóm, nên Odoo 19 đòi quyền **ghi** trên `crm.team` (chỉ Sales Administrator có) mới chạy được. Action gốc của Odoo (`crm.action_your_pipeline`) có nhóm `base.group_user`.

## Đã đổi (chỉ `views/landing.xml` + version, không field/model/ACL/cron/JS mới)
1. `action_crm002_landing`: thêm `group_ids = base.group_user` (mọi nhân viên nội bộ chạy được, giống action gốc).
2. `crm.crm_menu_root`: **thêm** `base.group_user` vào nhóm (giữ nguyên nhóm gốc) và gán **hành động riêng = action trang đích** (model `crm.team`, mọi nhân viên nội bộ đọc được). Bấm icon CRM sẽ chạy `landing_action`: có phễu thì vào phễu, không có thì ra trang trống của Update_028.
3. `crm.crm_menu_sales` (thư mục "Sales" chứa My Pipeline, My Activities, Teams, Customers): đặt lại nhóm = Own Documents Only + Administrator như cũ. Không có bước này thì tài khoản Sales = No thấy thêm Teams và Customers.
4. `__manifest__.py`: version 19.0.1.25.0.

## Ai thấy gì
| Tài khoản | Icon CRM | Bấm vào | Menu con |
|---|---|---|---|
| Sales = No | **Có** | Trang trống, "Bạn chưa được phân quyền phễu nào", không Access Error | Không có |
| Role Administrator, Sales = No | **Có** | Xem "Lưu ý" bên dưới | Không có |
| Own Documents Only, All Documents, Administrator | Có (như cũ) | Như Update_027 | **Y hệt trước Update_029** |

Bật Leads trong Settings của CRM cũng không mở menu Leads cho Sales = No (menu đó chạy trên `crm.lead`).

## Lưu ý và giới hạn (cần biết trước khi test)
- **Mọi nhân viên nội bộ giờ thấy icon CRM** (kể cả người chưa từng dùng CRM). Đây là đúng ý yêu cầu.
- Đổi Sales của một tài khoản xong phải **F5 (tốt nhất Ctrl+F5)**; menu và màn hình cũ được trình duyệt giữ.
- Role Administrator mà **Sales = No**: bấm CRM sẽ vào Pipeline gốc và Odoo báo lỗi quyền `crm.lead`. Cách xử lý: đặt Sales = Administrator cho tài khoản đó (theo thiết kế Update_027 chỉ Role Administrator mới thấy 2 nút lọc trùng).
- Link trực tiếp của Pipeline gốc vẫn báo lỗi quyền gốc với Sales = No (giống Update_028).
- Nâng cấp module `crm` (`-u crm`) có thể ghi lại nhóm menu về mặc định; nếu icon CRM biến mất với Sales = No sau khi nâng cấp `crm`, Upgrade lại `sgt_crm_campaign`.
- **Chưa chạy trên Odoo thật.** Chưa kiểm: web client Odoo 19 có mở hành động gắn ở menu gốc đúng ý không; menu gốc có tính hành động riêng khi lọc hiển thị không.
- Lỗi "3 thông báo chồng lên nhau" user báo lúc 15:42 **chưa sửa** vì chưa biết nội dung thông báo; cần ảnh chụp hoặc chữ trong thông báo.

## Đã test
- Offline: **275 test xanh** (261 cũ + 14 mới ở `tests/test_update029_menu.py`), 1 test bỏ qua như mọi bản trước (cần file `odoo_views.csv` của Scan thật).
- Test mới chạy lại **thuật toán lọc menu của Odoo 19** (đọc từ mã nguồn GitHub 19.0) trên cây menu CRM gốc, cộng các ghi đè lấy thẳng từ `landing.xml`. Kết quả: Sales = No chỉ còn menu gốc; mọi mức Sales còn lại giữ **đúng** tập menu cũ.
- Cố ý làm hỏng mã 9 kiểu (bỏ nhóm ở menu gốc; thay vì thêm lại thay thế nhóm gốc; bỏ hành động menu gốc; bỏ nhóm ở server action; mở lại thư mục Sales; thêm `base.group_user` vào thư mục Sales; bỏ ghi đè thư mục Sales; trả My Pipeline về action gốc; quên đổi version): cả 9 đều có test đỏ.

## Cài đặt
1. Backup Demo 2. Cài CRM-002 Update_029 lên Update_028 (hoặc cũ hơn). Upgrade module, restart Odoo.
2. Rollback: cài lại Update_028, Upgrade (không đổi dữ liệu). Nếu icon CRM vẫn còn sau rollback thì Upgrade module `crm` hoặc xoá `base.group_user` khỏi menu CRM trong Settings > Technical > Menu Items.

## Bài test trên Demo 2
| # | Làm | Kỳ vọng |
|---|---|---|
| 1 | U1 (Sales = No) Ctrl+F5 | Icon **CRM còn hiện** ở màn hình app |
| 2 | U1 bấm CRM | Trang trống, chữ "Bạn chưa được phân quyền phễu nào", thanh bên "Không có phễu được cấp quyền"; **không có hộp lỗi**, không Deal nào |
| 3 | U1 trong CRM nhìn thanh menu trên | **Không có** My Pipeline / Teams / Customers / Reporting / Configuration |
| 4 | U2 (Own Documents Only, Kinh doanh) vào CRM | Như Update_027: 3 phễu, menu con y như trước |
| 5 | Admin (Sales Administrator) vào CRM | Như trước, đủ menu Configuration |
| 6 | Đổi U1 sang Own Documents Only → Ctrl+F5 | Thấy menu con và phễu theo Department; đổi lại No → Ctrl+F5 → trang trống |
