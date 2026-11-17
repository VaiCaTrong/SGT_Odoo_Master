# CRM-002 · Update_010 (19.0.1.6.3) — gồm Update_007 + 008 + 009

> Update_008 sửa lỗi nâng cấp `AttributeError: 'Char' object has no attribute 'ondelete'` (xoá các dòng selection cũ của `funnel.code` trong pre-script). Nội dung chức năng giữ nguyên Update_007.
> Update_010: đổi tên hiển thị phễu "Outbound hunter" → "Outbound Hunter" (tag và mã `hunter` giữ chữ thường; không ghi đè nếu admin đã tự đổi tên).
> Update_009: sidebar kiểu phẳng (không viền, tiêu đề in đậm, phễu con thụt vào); 2 nút cuối ghi tiếng Anh **Permissions / Settings**, không xuống hàng (màn hẹp thì xếp chồng nguyên nút).


## Có gì mới
1. **Sidebar**: logo nhỏ, nút thu/mở (« »), mọi nút có viền, chỉ còn 2 nút **Phân quyền** và **Cài đặt**. Nhóm hiển thị cố định: Data Funnel · Sale · Match Making Campaign.
2. **Data Funnel**: Admin tạo phễu nhỏ mới ở *Cài đặt* (3 cột cố định 1.Data / 2.Verified / 3.Potential). Không tạo được phễu lớn.
3. **Sale** (cố định): phễu **New** và **Renew**, mỗi phễu có sẵn cột `1.Data`; Admin tự thêm cột ở *Cài đặt › phễu › Stage*.
4. **Match Making Campaign**: giữ nguyên (cột = Stage của CRM Pipeline), không có phễu con.
5. **Phân quyền**: danh sách mọi phễu (kể cả New/Renew và phễu mới) × Department. Quyền xem Deal của Sale vẫn do Odoo quyết định.
6. **Luật bàn giao** (Cài đặt › phễu › nút “Luật bàn giao”, hoặc menu CRM › Cấu hình › *CRM-002 Luật bàn giao*): chọn phễu + cột nguồn → phễu + cột đích. Hai luật mặc định:
   - Data Funnel `3.Potential` → Match Making `1.Opportunity` (như cũ, mỗi phễu Data một luật).
   - Match Making `6.Approved Match Making` → New `1.Data`.
   Nút **Áp dụng cho Deal đang có** bàn giao toàn bộ Deal đang nằm ở cột nguồn (tối đa 500 Deal/lần bấm).

## Quy tắc bàn giao
- Dùng **chính Deal đó** (không copy) ⇒ log note, chatter, hoạt động, Tag, Salesperson được giữ nguyên.
- Mỗi luật chạy 1 lần/Deal, không kéo Deal lùi (Match Making chỉ đi tới theo thứ tự Stage; Sale bỏ qua nếu Deal đã ở phễu đó).
- Không chạy dây chuyền (Deal vừa được luật chuyển không kích luật khác).
- Tên Stage khớp **chính xác** (`1.Opportunity`, `6.Approved Match Making`, `1.Data`), không bỏ số, không đoán.
- Lỗi ở Data Funnel ⇒ thao tác kéo bị huỷ và báo lỗi; lỗi ở Match Making/Sale chỉ ghi log, không chặn người dùng (bấm “Áp dụng” để thử lại).

## Dữ liệu thêm (đã được duyệt)
- Model: `sgt.crm002.funnel.stage`, `sgt.crm002.handoff.rule`.
- Field: `sgt.crm002.funnel.group_key`, `crm.lead.sgt_crm002_sale_funnel_id`, `crm.lead.sgt_crm002_sale_stage_id`.
- Không có field liên quan CRM-005.

## Nâng cấp từ Update_006
Pre-script điền `group_key` (mã `mm` → Match Making, còn lại → Data Funnel); post-script tạo cột mặc định và 2 luật mặc định nếu tìm thấy Stage CRM đúng tên. **Không tìm thấy ⇒ bỏ qua luật đó và ghi cảnh báo** (Admin tự tạo luật trong Cài đặt).

## Giới hạn đã biết
- Cột Data Funnel cố định 3 cột (gắn với `sgt_crm002_step`); chỉ phễu Sale thêm/sửa cột tự do.
- Phễu Sale mới mặc định chỉ Administrator thấy; cấp Department ở *Phân quyền*.
- Deal chỉ vào Data Funnel lúc tạo (theo Tag/Source), không có luật đích Data Funnel.
