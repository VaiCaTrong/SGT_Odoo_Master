# CRM-005 Update_068 — Box "MM Approval" + nút đỏ Phê Duyệt & Tạo MM ngay trên form Deal

Nền: Update_067 (19.0.1.66.0). Manifest: **19.0.1.67.0**. Không field/cột mới, không migration.
**Phụ thuộc mới: addon `SGT MM Approval` (`crm_mm_approval_bridge`, v19.0.1.0.24)** phải nằm trong thư mục addons; nâng cấp 005 sẽ tự cài nó nếu chưa cài.

## Làm gì
- Box ngang (viền trái đỏ, huy hiệu SGT, chữ "MM Approval", **không có dòng chú thích**) nằm ngay trên tên Deal, nút đỏ **Phê Duyệt & Tạo MM** ở đầu bên phải.
- Chỉ hiện khi: người dùng thuộc nhóm *SGT MM Approver* (Administrator tự có) VÀ Deal đang ở stage nằm trong "CRM stages visible in MM Approval" (cấu hình = `5.Match Making`) VÀ chưa duyệt VÀ là Opportunity. Trong menu cũ "SGT MM Approval" chỉ hiện thanh cũ (không hai thanh chồng nhau).
- Bấm nút: chạy đúng hàm duyệt cũ của addon phê duyệt (kiểm quyền, tạo thẻ MM bên Odoo SGT, đồng bộ chatter/field, ghi Deal ID/tên deal, chuyển sang stage "Won" đã cấu hình). Xong hiện **thông báo xanh lá** "Phê duyệt thành công. Đã tạo Match Making (MM ID n) và chuyển deal sang <stage>." rồi form tự làm mới (stage, Deal ID, box biến mất). Lỗi: hộp lỗi như cũ, deal không chuyển cột.
- Administrator (nhóm Settings) kéo theo *SGT MM Approval Manager* (gồm Approver): vào được cấu hình và duyệt.
- Cấp quyền cho từng người: Settings > Users > tab Access Rights > mục "SGT MM Approval" chọn *Approver* (hoặc *Manager*).

## Phải làm sau khi cài (một lần)
Menu SGT MM Approval > Settings (hoặc nếu đã ẩn bằng 011 thì Odoo Settings > MM Approval > Active): "CRM stages visible in MM Approval" = `5.Match Making`; "Won Stage After MM Approval" = `6.Approved Match Making`; điền Remote URL / DB / user / mật khẩu SGT, Fixed Contact 1 ID, CRM Customer ID Field = `x_getfly_id`; bấm Test Connection.

## Lưu ý
- Nhóm Approver kéo theo quyền "xem tất cả lead" của CRM: người được cấp quyền duyệt thấy mọi Deal.
- Deal sang `6.Approved Match Making` sau khi duyệt sẽ chạy luật bàn giao CRM-002 (nếu có).
- Kéo thẻ thẳng sang cột 6 không qua duyệt: chưa chặn.
- File mới: `views/mm_approve_box.xml`, `security/mm_admin_implied.xml`, `models/mm_approval_button.py`, `static/src/css/mm_approve_box.css`, `tests/test_update068_contract.py`. `models/crm_lead.py` không đổi.
