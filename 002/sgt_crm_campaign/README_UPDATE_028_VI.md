# CRM-002 Update_028 (19.0.1.24.0) — sửa trang trống của tài khoản không có quyền phễu (không còn Access Error)

## Lỗi (user báo 02/11 15:33, Demo 2, ảnh chụp)
Tài khoản Sales = **No** bấm CRM thì hiện hộp **Access Error: You are not allowed to access 'Lead' (crm.lead) records**, và phía sau vẫn thấy các Deal. Mong muốn: không có quyền thì **hiện trống**.

## Nguyên nhân
- Trang trống của Update_011 là một Kanban `crm.lead` với điều kiện `id = 0`. Odoo kiểm **quyền truy cập model trước**, rồi mới áp điều kiện; tài khoản Sales = No không có quyền đọc `crm.lead` (chỉ nhóm Own Documents Only và Administrator có), nên báo lỗi dù điều kiện không lấy Deal nào.
- Các Deal thấy phía sau hộp lỗi **không phải do máy chủ trả cho tài khoản này**: đó là màn hình cũ Odoo giữ nguyên trên trình duyệt khi màn hình mới tải lỗi.
- Lỗi này có từ Update_011, nhưng chỉ lộ ra khi có tài khoản không có quyền Sales (Update_027 làm rõ ra).

## Đã đổi (chỉ 2 nơi, không field/model/menu/ACL/cron/JS mới)
- `views/landing.xml`: bỏ view `view_crm002_noaccess_kanban` (model `crm.lead`, kế thừa Kanban CRM); thêm view `view_crm002_noaccess_company_kanban` trên model **`res.company`** (mọi nhân viên nội bộ đều đọc được theo ACL gốc `access_res_company_employee`), vẫn dùng `js_class="sgt_crm002_intake"` nên có thanh bên CRM-002, `create="0"`. Odoo tự xoá view cũ khi Upgrade vì file không còn định nghĩa nó.
- `models/service.py::_no_access_action`: trả về action `res.company`, điều kiện `id = 0`, dòng chữ "Bạn chưa được phân quyền phễu nào" như cũ; bỏ các khoá context riêng của `crm.lead`.
- Không còn chạm vào `crm.lead` ở đường này, nên **không đọc Deal nào**.

## Ai thấy gì (không đổi so với Update_027)
- Sales = No: thanh bên "Không có phễu được cấp quyền", trang trống, **không báo lỗi**.
- Own Documents Only thuộc phòng không có phễu nào (ví dụ Administration): cùng trang trống.
- Các mức còn lại: như Update_027.

## Giới hạn (Odoo gốc, không sửa được nếu không dùng JS hoặc cấp thêm quyền)
Nếu tài khoản Sales = No tự mở **link trực tiếp** của Pipeline gốc (ví dụ `/odoo/action-...` của `crm.crm_lead_action_pipeline`) hoặc gõ F5 khi đang ở trang đó, Odoo vẫn báo lỗi quyền gốc vì action đó chạy trên `crm.lead`. Menu CRM của tài khoản này đã bị Odoo ẩn nên bình thường không đi vào đó. Muốn trống cả trường hợp này phải cấp thêm một quyền đọc rỗng cho `crm.lead` (chưa làm, cần user duyệt).

## Đã test
- Offline: **261 test xanh** (251 cũ + 10 mới ở `tests/test_update028_blank_page.py`). Test chạy CODE THẬT của `landing_action` và `_no_access_action` với môi trường giả **ném lỗi nếu có ai đụng `crm.lead`** (giống tài khoản Sales = No).
- Cố ý làm hỏng mã 8 kiểu (action về lại `crm.lead`, view về lại `crm.lead`, trả lại tên view cũ, bỏ thẻ `card`, thêm một lần đọc `crm.lead`, trả lại khoá context `crm.lead`, bỏ `js_class`, bỏ `create="0"`): cả 8 đều có test đỏ.
- **Chưa chạy trên Odoo thật**: Odoo 19 có hiển thị Kanban `res.company` trống kèm thanh bên và dòng chữ không; Upgrade có xoá view cũ không.

## Cài đặt
1. Backup Demo 2. Cài CRM-002 Update_028 lên Update_027 (hoặc cũ hơn; có `sales_team` trong depends từ Update_011). Upgrade module, restart Odoo.
2. Rollback: cài lại Update_027 (không đổi dữ liệu).

## Bài test trên Demo 2 (thay bài 1 của Update_027)
| # | Làm | Kỳ vọng |
|---|---|---|
| 1 | U1 (Sales = No) F5 rồi bấm CRM (hoặc link phễu trong thanh bên) | Trang **trống**, chữ "Bạn chưa được phân quyền phễu nào", thanh bên "Không có phễu được cấp quyền"; **không có hộp Access Error**; không còn Deal nào phía sau |
| 2 | U4 (Own Documents Only, Administration) vào CRM | Cùng trang trống như bài 1 |
| 3 | U2 (Own Documents Only, Kinh doanh (MMC)) vào CRM | Như bài 2 của Update_027 (vẫn thấy 3 phễu; không bị ảnh hưởng) |
| 4 | Đổi U1 sang Own Documents Only → F5 | Thấy phễu theo Department; đổi lại No → F5 → trang trống |
