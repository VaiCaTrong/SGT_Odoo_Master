# CRM-005 V01 Update_061 — Safe additive Kanban links

## Source and intent
Built directly from CRM-005 Update_059, NOT from the failed Update_060.
Manifest: `19.0.1.60.0`. No database columns or migrations.

## Changes
- Restore native Kanban color picker by removing the CRM-005 XPath which removed `kanban_color_picker`, and enable `edit=true` so palette can write. Keep `delete=false`, `quick_create=false`, `records_draggable=true`, `create=true`, and prevent moving/editing stage columns.
- ONE additive XPath to anchor to existing Kanban card `footer`, adding Source and context-sensitive links: Website, Facebook, Trang Vang, Zalo, and a rights-checked Documents folder button. Does not remove/replace historical Facebook or Website elements via XPath.
- Read-only Source; CSS hides only historic tags, priority, activity label, location, Facebook line and group-post ID from opportunity cards. This is a **presentation** change, not deletion of stored data.
- Documents: RPC checks read access and effective folder-view permission before showing the icon. The click calls existing Documents-008 Explorer action; it does not create folders. Compatible with `crm_lead_ids` for shared MST folders and legacy `lead_id`.
- External URLs are validated for scheme and correct provider hosts before `href` is assigned; invalid links remain hidden. Browser opens valid links in new tab.
- Preserve the original Kanban footer containing the salesperson avatar, existing Ctrl/Cmd/middle-click logic, Get Coordinates and persisted geolocation (Update_056), image Gallery, folder creation from Create Contact and all existing CRM fields.
- Phone country-code normalization remains in Extension, NOT here.

## Release caution
- The Production base view may differ from the 2026-10-11 Scan. Offline XPath simulation DOES NOT prove the live Upgrade succeeds.
- `edit=true` is required for Odoo native color picker; it may make default Edit entry visible if Odoo changes menu markup. CSS suppression is best-effort, not an ACL. Users still need actual ORM `write` privileges to change colors.
- Hide/show presentation depends on the live Odoo DOM/CSS. If older rows remain visible after upgrade, confirm Odoo asset rebuild and actual DOM; avoid adding fragile XPath replacements.
- Inspect view inheritance chain and perform Odoo Upgrade on a staging clone before Production.

## Upgrade
1. Backup database `xinyang` and current CRM-005 addon.
2. Restore/prepare working baseline Update_059 if Update_060 is causing a blocked Pipeline.
3. Replace the complete `sgt_crm_yellowpages_profile` addon folder with Update_061 (do not overlay Update_060 files).
4. Restart Odoo; Upgrade `sgt_crm_yellowpages_profile` on staging. Clear frontend assets with Ctrl+Shift+R.
5. Validate: Pipeline opens; 3-dot color menu saves; Source, link buttons, documents permissions; Salesforce avatar remains bottom-right; normal/modified clicks, card drag, New; Geolocation, Gallery and Documents.
6. Only then deploy to Production in a maintenance window.

## Rollback
Use backup and restore Update_059 code, restart, upgrade module to reapply its previous view definitions. Do not uninstall or delete deal data.

## Offline regression fixture
`tests/fixtures/odoo_scan_opportunity_base.xml` is a copy of the historical scanned Kanban XML, included only for portable tests, NOT as an Odoo data/view install.
