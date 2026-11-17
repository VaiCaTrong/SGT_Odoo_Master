# CRM-002 Update_015 (19.0.1.11.0) — Log chuyển stage/bàn giao, thanh stage theo phễu, sidebar, admin không gắn My Pipeline

## Yêu cầu (user 2026-10-27 13:49–14:01, chốt cuối "admin thì không cần tự động My Pipeline, user vẫn gắn như bình thường")
1. Kéo/chuyển stage trong phễu phải để lại log note trong Chatter.
2. Bàn giao Data Funnel › 3.Potential → Match Making không thấy ghi gì (lỗi của Update_014).
3. Deal ở phễu Data nhưng thanh stage trên form hiện stage Match Making; bấm vào thanh phải chuyển được stage.
4. Logo + chữ XINYANG canh giữa trong thanh phễu bên trái.
5. Sale nằm dưới Match Making trong thanh phễu.
6. Admin bấm Match Making không tự gắn My Pipeline; user thường vẫn gắn.

## Làm gì
1. **Log chuyển stage**: mỗi lần Deal đổi cột trong Data Funnel (qua kéo thẻ, bấm thanh stage hoặc service) hoặc Sale, Chatter có Log note "🔀 Chuyển stage trong phễu X: A → B". Không ghi khi không đổi (lặp lại, kéo ngược bị từ chối). Là Log note, không gửi thông báo; lỗi ghi chỉ log, không chặn việc chuyển.
2. **Bàn giao Data → Match Making**: Deal phễu Data đã đứng sẵn ở stage CRM 1.Opportunity nên luật không có gì để chuyển và Update_014 không ghi. Từ Update_015 luật có nguồn là phễu Data vẫn ghi note bàn giao, thêm dòng "Kết quả: Deal đã đứng sẵn ở cột đích nên không đổi stage; Deal nay hiện trong phễu đích" (hoặc "đã chuyển Deal sang cột đích"). Luật nguồn Match Making/Sale vẫn chỉ ghi khi Deal thật sự chuyển.
3. **Thanh stage trên form** (view `view_crm002_lead_form_funnel_bar`, kế thừa form CRM chuẩn):
   - Deal đang ở phễu Data, chưa Potential: thanh 1.Data › 2.Verified › 3.Potential (bấm được).
   - Mở Deal từ trang phễu Sale (context `sgt_crm002_funnel_group = sale`): thanh các stage của phễu Sale đó (bấm được).
   - Còn lại (Match Making, Deal đã Potential/bàn giao): thanh stage CRM chuẩn như cũ.
   - Bấm trên thanh đi qua đúng `write()` của CRM-002 như kéo thẻ: không kéo ngược sau Potential, bàn giao tự chạy, ghi Chatter.
4. **Sidebar**: logo + XINYANG canh giữa, nút « ở mép phải (CSS). Thanh thu gọn không đổi.
5. **Thứ tự sidebar**: Data Funnel → Match Making Campaign → Sale. Thứ tự phễu dự phòng khi mở CRM của user không có quyền Match Making không đổi (Data trước Sale).
6. **My Pipeline**: Administrator mở Match Making (nút sidebar `native_pipeline.js` và menu CRM/My Pipeline qua `landing_action`) không còn tự gắn My Pipeline. User thường giữ nguyên My Pipeline mặc định. Đây là sửa 1 đoạn nhỏ trong file JS sẵn có, không thêm file JS mới.

## Không đổi
Không thêm field/model/JS mới. Match Making (Pipeline chuẩn), khóa quyền Update_012, List và 6 nút Update_013/014, CRM-005, tab "History stage change" của addon khác.

## Test Demo 2
1. Kéo 1 Deal Data → Verified → Potential trong Outbound Hunter: mỗi lần có note 🔀; sang Potential có thêm note 🔁 "Bàn giao Deal" với dòng Kết quả.
2. Mở Deal đang ở Data/Verified: thanh stage là 1.Data › 2.Verified › 3.Potential, không còn 1.Opportunity…5.Match Making. Bấm 3.Potential: Deal chuyển và bàn giao; sau đó thanh về stage CRM.
3. Mở Deal từ phễu New/Renew: thanh stage Sale, bấm đổi được; mở cùng Deal từ Match Making: thanh stage CRM.
4. Sidebar: logo + XINYANG ở giữa; thứ tự Data Funnel, Match Making Campaign, Sale.
5. Admin bấm Match Making: ô tìm kiếm không có "My Pipeline". Tài khoản thường (có quyền Match Making): có "My Pipeline".

## Giới hạn / chưa kiểm chứng ngoài Odoo thật
- Form dùng `context.get(...)` trong modifier và `add=` cho `invisible` của thanh stage chuẩn: nếu Odoo 19 từ chối khi Upgrade, gửi thông báo lỗi để chỉnh.
- Thanh theo phễu Sale chỉ hiện khi mở Deal từ trang phễu Sale; mở từ link trực tiếp thì thấy thanh stage CRM.
- Deal đã chuyển trước bản này không có note.
## Rollback
Cài lại Update_014 (không đổi dữ liệu; các note đã ghi vẫn nằm trong Chatter).
