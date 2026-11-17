# Company Information / CRM Information (addon argo_documents) — Odoo 19

**Technical module:** `argo_documents` (single module; no `gearea_documents` dependency).
**Version:** `19.0.1.2.0` — Clipboard UX RC2 + phân quyền xem thư mục theo phòng ban / người dùng (Update_001), 2026-11-05.

## Current features
- Explorer: folders, drag/drop external files, files upload/download, note and document creation, ZIP export, search, trash.
- RC2 clipboard improvements: paste files/screenshots from the operating system (Ctrl+V inside Explorer), copy one selected image as PNG to the system clipboard for applications supporting image paste (e.g., some Zalo/email clients). Button **Chép ảnh ra ngoài** and image context-menu action.
- Existing Explorer internal copy/cut/paste still works and is **not** the same as copying a system file to the OS clipboard.
- If the receiving application does not accept clipboard images, use **Tải xuống** and attach/upload the file normally.
- Clipboard API requires HTTPS, browser user gesture and platform permission/support. Remote application-specific paste is **not verified**. Copying arbitrary DOCX/PDF files as desktop clipboard file objects is **not implemented**.
- Copy image reads an attachment using its existing same-origin Odoo `/web/content` route; no public sharing URL and no new HTTP endpoint are introduced. Browser clipboard is user-triggered. PNG conversion preserves pixels but not necessarily image metadata/EXIF.
- RC2 itself adds no data model/ACL. **Update_001 (19.0.1.2.0) does change the schema and the record rules**, see the next section.

## Update_001 — quyền xem thư mục theo phòng ban hoặc từng người (19.0.1.2.0)
Cách dùng: chuột phải thư mục → **Quyền xem…** (hoặc nút "Quyền xem" ở bảng chi tiết) → **Giới hạn** → tích **phòng ban** và/hoặc **người dùng** → Lưu. **Mọi người** xóa giới hạn.
- Phòng ban lấy từ `hr.department`; thành viên là nhân viên (`hr.employee`) **đang hoạt động, có tài khoản Odoo** trong đúng phòng ban đó. **Không tính phòng ban con** (cùng cách với CRM-002). Muốn cả nhánh thì tích cả các phòng ban con.
- Người được xem = người chọn riêng + thành viên các phòng ban đã tích. Nhân viên chuyển phòng/nghỉ việc (archive) mất quyền ngay sau khi Odoo tính lại.
- Thư mục con không tự chọn thì **kế thừa** từ thư mục cha; thư mục con tự chọn thì **thay** (không cộng) quyền của cha.
- Phòng ban chưa có nhân viên nào có tài khoản: thư mục vẫn **bị giới hạn** (chỉ quản lý kho thấy). Hộp thoại có cảnh báo vàng trong trường hợp này.
- Người tạo thư mục (không phải quản lý) lưu quyền mà mình không nằm trong đó thì hệ thống **tự thêm người tạo** để khỏi tự khóa mình. Quản lý kho luôn thấy tất cả.
- File trong thư mục bị giới hạn: chặn cả khi mở link `/web/content/...` (quyền file đi theo record rule của tài liệu).
- Thay đổi kỹ thuật: depends thêm `hr`; trường mới `allowed_department_ids` (M2M, bảng `argo_document_folder_allowed_dept_rel`) và `effective_restricted` (boolean lưu, có index); `effective_user_ids` thành trường lưu có tính lại. Hai record rule (thư mục, tài liệu) dùng `effective_restricted` thay cho "danh sách người rỗng = mở". `explorer_set_access(folder_id, user_ids, department_ids=None)` vẫn gọi được kiểu cũ 2 tham số (xóa phòng ban).
- Nâng cấp: Odoo tự tạo cột/bảng mới và tính lại các trường lưu cho thư mục cũ. Thư mục cũ có chọn người vẫn giữ nguyên quyền; thư mục không chọn gì vẫn mở cho mọi người.
- Chưa chạy trên Odoo thật. Xem file `TEST_REPORT` đi kèm và bài test Demo 2.

## Test status
- Static syntax and mock unit tests are passed for selected cases only. Odoo 19 runtime/asset compilation/clipboard permissions and cross-app behavior have NOT been independently tested.
- Installed RC1 on ARGO Demo is user-confirmed and Explorer UI render was read-only observed; RC2 is NOT deployed.
- The Odoo container on SGT Addon Manager Node3 hosts the `argo` and `argodemo` databases together. Restart is shared-instance and must be impact-assessed separately. Never auto-restart during RC2 testing.

## Future development, PROPOSED/NEEDS REVIEW
- Team/Department ACL: define resource owner, Sales Team vs Department semantics, cross-team share, administrators, multi-team users, relation-based source-record rights; inspect actual `crm.team` and `hr.department` availability and membership model before creating fields/rules. Never substitute client-only filtering for ORM+attachment/HTTP authorization.
- CRM (`crm.lead`), Contacts (`res.partner`) and Calendar (`calendar.event`) integration via record-specific Documents & Notes smart actions, contextual uploads, secured single/multiple links, meeting notes and version/audit policy. Links do not yet create native attachments/chatter messages.
- Approval and real-customer/MM evidence protection must be specified before enabling organizational sharing/public links. Do not modify business MM stages or approval rules as side effects.

## Upstream provenance / license
This addon is adapted from the user-supplied Gearea documents addon (manifest `19.0.2.0.0`, declared `LGPL-3`). It does **not** install Gearea, but retains substantial adapted code. Preserve its upstream attribution and applicable license terms (see `COPYING`) and verify original redistribution rights before third-party or commercial distribution.

## Rollout
1. Confirm a recoverable backup (database, filestore, addon directory) and shared-container restart impact.
2. Test in Demo with synthetic files and test users only.
3. Upload RC2 ZIP under the approved addon directory; verify extracted files and checksum; upgrade the existing `argo_documents` module in the Demo Apps list after change approval; handle any service restart as a separately authorized operation.
4. Smoke test drop, paste, copy, download, note persistence and negative ACL/attachment access. Do not assume tests pass based on static inspection.

## Update_003 — Quyền theo thư mục

Chính sách quyền mới: Private, User/Department, Public nội bộ; View/Edit/Full. Root folder chỉ Admin hoặc Root Creator tạo. Chủ folder mới mặc định Edit; phân quyền được quản lý bởi Admin hoặc Share Manager đã có Full. Các folder cũ giữ `legacy` để rà soát, không được tự động chuyển đổi. Xem `CHANGELOG_UPDATE_003.md` và `docs/UPDATE_003_DEPLOY.md` trước khi nâng cấp.


## Update_010 — Cập nhật ảnh lên CRM (19.0.1.10.0)
Xem `CHANGELOG_UPDATE_010.md`. Nút xanh + mục menu chuột phải (cả cây thư mục), hộp chọn Deal; ghi Gallery qua CRM-005 Update_064.
