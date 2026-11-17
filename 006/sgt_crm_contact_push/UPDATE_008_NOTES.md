# CRM-006 Update_008 — đồng bộ Lat/Lon không thêm field Contact

Nguồn: Update_006 được người dùng xác nhận hoạt động ổn định. Không kế thừa `models/res_partner.py` của Update_007.

## Quy tắc

- CRM-005 Update_054 là nguồn tọa độ, kiểm tra `x_yp_geo_status` (`estimated`/`manual`), `x_yp_geo_precision` và địa chỉ có chữ ký không đổi trước khi chép.
- Tọa độ được chép **sau** khi cập nhật Address, để tránh `res.partner.write` reset tọa độ. Cả Company cha và Person được xử lý khi có liên kết.
- Khi **Create Contact** kích hoạt tự đồng bộ lần đầu: chỉ chép nếu Contact chưa có tọa độ hoặc đã cùng tọa độ; giữ nguyên cặp khác có sẵn, kể cả khi Odoo reset sau ghi Address (khôi phục và ghi cảnh báo cần rà soát vị trí theo địa chỉ mới).
- Khi chủ động bấm **Cập nhật Contact**: tọa độ CRM-005 sẽ thay thế tọa độ khác trên Contact (và Company cha) vì người dùng đã yêu cầu đồng bộ. Nếu Contact có tọa độ thủ công cần bảo vệ, không bấm Cập nhật Contact trước khi rà soát.
- Nếu CRM-005 chưa có tọa độ hợp lệ, bảo vệ tọa độ đã có trên Contact trong luồng Create; với nút thủ công chỉ dùng định vị Odoo như Update_006 khi cần. Không tạo tọa độ giả.
- Không thêm model hoặc field trên `res.partner`, không tự tạo Contact, không sửa addon tạo Contact cũ hoặc CRM-007.

## Khắc phục lỗi UndefinedColumn của Update_007

Lỗi `res_partner.x_sgt_crm006_geo_last_key does not exist` xảy ra khi Python đã được nạp nhưng module chưa hoàn tất Upgrade tạo cột. Bản này **không dùng cột đó**.

1. Sao lưu database `xinyang` và addons hiện tại; bảo đảm CRM-005 Update_054 đã hoạt động.
2. Thay trọn thư mục `sgt_crm_contact_push` bằng Update_008, KHÔNG merge chồng lên Update_007: `models/res_partner.py` cũ phải được bỏ khỏi filesystem.
3. Restart toàn bộ tiến trình Odoo (web và cron) để bỏ field của Update_007 khỏi Registry đang chạy.
4. Kiểm tra Logs không còn `x_sgt_crm006_geo_last_key`, mở được Apps. Upgrade module `sgt_crm_contact_push` (version `19.0.1.7.0`) trên staging/clone trước.
5. Kiểm tra Create Contact, Cập nhật Contact và GPS cho Company / Person; lần nhấn nút thủ công có thể ghi đè GPS cũ trên Contact.
6. Sau nghiệm thu mới áp dụng Production. Không tự thêm cột SQL, không Uninstall.

**Giới hạn:** Không thể đồng thời bảo vệ mọi GPS Contact thủ công và cho phép ghi đè tự động tọa độ CRM-005 thay đổi nhiều lần nếu không lưu metadata về nguồn gốc ở đâu đó. Update_008 chọn bảo vệ ở luồng tự động và cho phép ghi đè có chủ đích ở nút thủ công.
