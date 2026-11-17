# CRM-002 Update_014 (19.0.1.10.0) — Ghi lịch sử bàn giao vào Chatter + cột Stage đúng của phễu trong List

## Yêu cầu (user 2026-10-27 11:20 / 13:32, "triển 002" 13:38)
1. List của phễu Data hiện cột Stage chuẩn "1.Opportunity" trong khi nhóm là 1.Data/2.Verified/3.Potential.
2. Khi stage thực hiện bàn giao Deal, phải ghi lại lịch sử bàn giao cạnh lịch sử chuyển stage.
(User chưa trả lời 2 câu hỏi nhỏ; đã chọn theo đề xuất: ghi ở **Chatter**; **thay hẳn** cột Stage chuẩn bằng stage phễu.)

## 1. Lịch sử bàn giao (Chatter)
Mỗi lần luật bàn giao chuyển một Deal, `sgt.crm002.handoff.rule._apply_to()` ghi một **Log note** vào Chatter của chính Deal đó:
- Từ: `<Phễu> › <Cột>` · Sang: `<Phễu> › <Cột>` · Luật: tóm tắt luật · Thực hiện bởi: tên người dùng · cách kích hoạt (tự động khi Deal vào cột nguồn, hoặc áp dụng thủ công bằng nút "Áp dụng cho Deal đang có").
- Là Log note (không gửi thông báo cho người theo dõi). Giờ và người ghi do Chatter hiển thị như các dòng khác.
- Chỉ ghi khi Deal thực sự được chuyển (không ghi khi đã ở đích hoặc luật không chạy). Lỗi khi ghi Chatter chỉ ghi vào log máy chủ, không chặn việc bàn giao.
- Một chỗ ghi duy nhất nên mọi đường bàn giao (kéo thẻ Match Making, chuyển Potential, nút áp dụng luật) đều có dòng ghi.

## 2. List của phễu
Data Funnel và Sale (New/Renew) dùng List riêng = List cơ hội chuẩn của Odoo (mọi cột và phần mở rộng của addon khác giữ nguyên), chỉ thay cột Stage chuẩn bằng stage phễu: Data = `sgt_crm002_step` (Data/Verified/Potential), Sale = `sgt_crm002_sale_stage_id`.

## Không đổi
Không thêm field/model/JS. Match Making (Pipeline chuẩn), khóa quyền, landing, Kanban, Pivot/Graph/Calendar/Activity (Update_013) giữ nguyên. Không đụng tab "History stage change" của addon khác và không đụng CRM-005.

## Test Demo 2
1. Tạo/đưa 1 Deal vào Data Funnel › 3.Potential (có luật sang Match Making): mở Deal, Chatter có note "🔁 Bàn giao Deal (CRM-002)" với Từ/Sang/Luật/Thực hiện bởi.
2. Kéo Deal Match Making sang cột nguồn của luật sang Sale: có note tương ứng.
3. Cài luật mới, bấm "Áp dụng cho Deal đang có": mỗi Deal có note "áp dụng thủ công".
4. Mở lại cột đích hoặc chạy lại: không có note thứ hai.
5. List Data Funnel: cột Stage hiện Data/Verified/Potential, không còn "1.Opportunity"; List Sale hiện stage Sale.

## Giới hạn
- Deal đã bàn giao trước Update_014 không có note (không ghi bổ sung).
- Chưa chạy trên Odoo thật: xpath thay cột `stage_id` của List chuẩn (nếu addon khác đã sửa/xoá cột này, Upgrade có thể báo lỗi view), Chatter ghi bằng quyền hệ thống.
## Rollback
Cài lại Update_013 (không đổi dữ liệu; các note đã ghi vẫn nằm trong Chatter).
