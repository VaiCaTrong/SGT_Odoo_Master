# CRM-005 Update_035 — Company logo on Opportunity Kanban

**Base:** CRM-005 Update_034, manifest 19.0.1.33.0. New manifest: 19.0.1.34.0.

## Scope
- Adds ONLY a child view of `crm.crm_case_kanban_view_leads` to replace the **company line** (`x_company`) in the existing Xinyang Kanban card. The rest of the card is preserved.
- Fixed 52×52 logo left of company name; 44×44 on narrow displays; contain fit keeps the complete logo visible.
- Logo priority: `x_yp_logo_upload` (binary attachment), then `x_image` (URL supplied by the extension), then a neutral building icon. A load error also falls back to the building icon.
- No new ORM fields, no data migrations, no permission changes, no backend RPC, no changes to other modules.
- Does not modify CRM-002, the extension, Gallery, Lightbox or Deal form.

## Files changed / added
- `__manifest__.py`: bumps version, loads Kanban inherited view and two small assets.
- `views/crm_yp_lead_kanban.xml`: **new**, extends the company row in the opportunity card.
- `static/src/css/kanban_company_logo.css`: **new**, scoped styles.
- `static/src/js/kanban_company_logo_fallback.js`: **new**, no RPC; handles broken image URLs via capturing `error` events.

## Deployment and preflight
1. Back up database + current addon ZIP.
2. On a staging clone, inspect **Settings > Technical > User Interface > Views** for `crm.crm_case_kanban_view_leads`. The XML customization requires a `t-name="card"` template with the `x_company` field in a `div` (as in the Xinyang scan of 2026-10-11). If this node has since changed, adapt the XPath to the live view BEFORE upgrading; do not blindly install.
3. Make sure the previous issue about the missing `crm_lead.argo_crm_folder_id` column has been resolved; it can still block loading the Kanban independently.
4. Upgrade only `sgt_crm_yellowpages_profile`, rebuild web assets and hard-refresh the browser.
5. Verify manual upload logo, extension URL fallback, missing/broken logo fallback, resize, opening a card, dragging between stages, Salesperson, Tags, Stage, and group counters.
6. Validate the inherited view with Odoo's view registry on staging; this package has **not** been tested against the current production registry.

## Important limitations
- The scan is historical (2026-10-11); the actual Kanban view may have changed. This is tested offline against the scanned view, not production.
- The replacement targets the company row only, not the whole card. No other field or behavior should change.
- If an uploaded binary is truthy but the linked attachment cannot be loaded, an icon is shown instead; we do not fetch remote `x_image` in that case.
