# Documents-008 Update_007 — 2026-11-09

- Admin-only Lock / Unlock Folder trong menu chuột phải, giữ `is_locked`, chặn xóa trực tiếp, trash, permanent, cron purge và xóa gián tiếp qua tổ tiên. Không khóa upload/sửa nội dung.
- CRM Infor được cấu hình theo Folder ID ở Settings. Khi lưu, đặt root Public/View, company không giới hạn, quyền tạo folder con chuyên dụng cho Documents User; không cho người thường sửa/xóa root.
- CRM tạo folder theo `crm.lead.x_yp_tax_code` đã lưu; một MST một folder trực tiếp dưới CRM root; liên kết nhiều Deal bằng `crm_lead_ids` và vẫn giữ `lead_id` cũ.
- Không tự cấp quyền truy cập folder của Salesperson khác: khi MST trùng mà người gọi không có Edit, chặn và hướng dẫn Admin chia sẻ.
- CRM Infor Public/View được mở cho mọi tài khoản nội bộ `base.group_user` bằng ACL/Record Rules chỉ giới hạn tại cây CRM; Portal và folder legacy ngoài CRM không được mở. Không tự gán Documents User.
- Không tự di chuyển, đổi tên hay chia sẻ folder cũ; cấu hình CRM root cần được Admin lưu lại sau khi nâng cấp.

- Đặc biệt: CRM Infor Public/View là quyền của root, không giới hạn mức chia sẻ View/Edit/Full của từng folder MST con. Mỗi folder con vẫn cần chính sách riêng; root không trở thành Editable/Deletable.
