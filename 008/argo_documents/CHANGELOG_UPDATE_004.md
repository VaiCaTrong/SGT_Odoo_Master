# Update_004 — Fix RPC_ERROR in folder permissions

## Lỗi được khắc phục
- Mở Phân quyền gọi `argo.document.folder.explorer_departments()`, dẫn đến `ValueError: Cannot convert hr.department.complete_name to SQL because it is not stored`.
- Nguyên nhân: `_departments_domain_search()` dùng `order='complete_name'` trong Odoo 19; field `hr.department.complete_name` tính toán nhưng không lưu trong database trên server đang triển khai.

## Bản vá tối thiểu
- Thay SQL ordering thành `order='name, id'` (field lưu được trong database).
- Danh sách lựa chọn phòng ban vẫn được sắp xếp theo `complete_name` ở Python sau khi đọc, giữ nguyên tính dễ hiểu của đường dẫn phòng ban.
- Không đổi domain giới hạn company, phép kiểm tra quyền, quyền View/Edit/Full, hoặc dữ liệu Documents và liên kết CRM.
- Manifest: `19.0.1.4.0`; nền Update_003.

## Giới hạn xác minh
- Đã kiểm tra offline: cú pháp Python/JS, XML, điều kiện không còn SQL sort theo `hr.department.complete_name`.
- Chưa thể chạy Odoo 19 thật; phải nghiệm thu trên Staging trước khi áp Production.
