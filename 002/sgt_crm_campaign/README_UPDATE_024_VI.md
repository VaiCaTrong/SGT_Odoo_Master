# CRM-002 Update_024 (19.0.1.20.0) — số lượng Deal ở mép phải sidebar phễu

Yêu cầu (user 2026-10-28 15:36 mô phỏng, nhắc lại 16:11 "với yêu cầu hiện số bên phễu này đâu"):
- Mỗi phễu con hiện số Deal ở mép phải; phễu cha hiện tổng các phễu con (Data Funnel = Outbound Hunter + Inbound Pool + Outbound Data + Inbound GB; Sale = New + Renew; Match Making Campaign = Match Making, đếm 1 lần).
- Đếm đúng tập Deal mà bảng của phễu đó hiện: Data = `sgt_crm002_funnel_id` + bước data/verified/potential; Sale = `sgt_crm002_sale_funnel_id`; Match Making = CRM Pipeline (`type = opportunity`). Đếm bằng quyền của chính user (không sudo trên crm.lead); không lọc theo nhân viên đang chọn ở SALESPERSON (số = cả phễu).
- Số được tính mỗi lần mở một phễu / tải lại trang (hàm `bootstrap`); không tự nhảy khi kéo deal.
- Thay đổi: `models/service.py` (`_funnel_count_domain`, `_funnel_counts`, `count` trong `bootstrap`), `native_pipeline.xml`, `workspace.scss`. Không field / JS / API / cron mới. Sidebar thu nhỏ không hiện số.
Test: `SidebarCounts` (6 test: cha = tổng con, MM đếm 1 lần, domain đúng, AccessError = 0, template + CSS).
