# CRM-005 Update_036 — Company name emphasis, hover marquee, Kanban view-only

**Base:** CRM-005 Update_035 (`19.0.1.34.0`). **New version:** `19.0.1.35.0`.

## Changes

- Company name next to the logo uses **16px / weight 700** (15px on narrow screens) in a single line. If the name does not fit, the **existing** `sgt_marquee.js` slides the text on hover and resets when leaving. No duplicate animation script or new backend calls; respects reduced-motion settings.
- Logo and company name are in a native Odoo `<a type="open">` so clicking the row opens the same Deal's form view. Other normal card clicks continue to use Odoo's default behavior.
- Opportunity **Kanban UI only** is configured for viewing and navigation: no quick-create/create, edit/delete actions in Kanban, dragging cards/stages, or editing stage columns. Color picker is removed from the Kanban card menu. The interactive activity clock is replaced with a passive status label; activities can be managed in the Deal form. Editing **inside the Deal form** and server ACL/Record Rules are unchanged.
- Keeps logo priority `x_yp_logo_upload` → `x_image` → building placeholder; existing JS image-load error fallback retained. Company-name missing state is shown as **Chưa có tên công ty**.
- Does not modify CRM-002, other addons, models or database schema, Chrome extension, Gallery/Lightbox, or form view.

## Important interpretation

"Kanban chỉ để xem" is implemented at the **view layer**, not by revoking a user's CRM write permissions. Some standard Odoo widgets remaining on the card (e.g., avatar/priority/properties) need *real Odoo UI testing* to confirm view-level `edit="false"` prevents all inline writes in this Odoo installation. No claim of API-level read-only is made: users with ordinary rights can still edit in the form, other views or RPC.

## File changes compared with Update_035

- `__manifest__.py` — version increment.
- `views/crm_yp_lead_kanban.xml` — readonly Kanban attributes, native open link, marquee class, remove Kanban color picker.
- `static/src/css/kanban_company_logo.css` — font, hover/focus and scrolling layout.
- `tests/test_update035_kanban_logo_offline.py` — inheritance tests adapted to the extended view, version baseline relaxed.
- `tests/test_update036_kanban_readonly_marquee_offline.py` — new regression assertions.
- `UPDATE_036_NOTES.md` — this file.

## Deployment QA / known constraints

1. **Back up DB and Update_035 ZIP.** Install/test first on staging.
2. Verify the current `crm.crm_case_kanban_view_leads` still has the `x_company` company row and the `menu` color picker; historical scan dated 2026-10-11 passes offline XPath only.
3. Upgrade `sgt_crm_yellowpages_profile`, regenerate web assets, force-refresh.
4. Confirm long names scroll left/right ONLY on hover (short names remain still), title is bold, logo fallback, click from logo/name/card opens same Deal form; form remains editable per existing rights.
5. Confirm stage drag, quick-create, edit/delete from Kanban, column modifications and color picker are disabled. **Test priority stars, passive activity status, assignee avatar and other third-party widgets interactively.** If a widget still writes, it requires a narrowly scoped additional Kanban widget restriction; do not assume `edit=false` is a security boundary.
6. Test mobile layout and existing CRM-005 Image Gallery/Lightbox/Developer Mode deletion.
7. An unrelated `crm_lead.argo_crm_folder_id` missing column can still block loading Kanban. Resolve DB/schema mismatch separately if present.

**Test scope:** offline XML, scanned XPath, manifest and assets only; NOT Odoo staging/production runtime.
