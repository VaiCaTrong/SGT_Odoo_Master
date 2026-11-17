# CRM-005 Update_041 — Fix Owl error opening Deal

## Problem / verified source-level root cause

Update_039 registered the Documents field widget as a bare Owl class. The Odoo 19
`web.Field` template mounts `field.component`; a bare class registry entry has no
`component` property. Consequently the CRM Deal form crashed at `Field.template`
with `TypeError: Cannot read properties of undefined (reading 'name')`.
Update_040 changed the bound CRM field without correcting the registry entry.

## Fix

`static/src/js/documents_panel.js`: register the Documents widget as a field
configuration object with `component` and `supportedTypes`, identical in pattern
with the already-working `sgt_gallery_manage` widget. No changes to field
storage, CRM form XML, Documents-008 model/APIs/ACL or upload logic.

Manifest: 19.0.1.40.0. Source base: CRM-005 Update_040.

## Testing

- JavaScript syntax (`node --check`) and Python syntax.
- XML parsing.
- Regression checks for field registry component configuration and full ZIP.
- Exact file comparison against Update_040 (aside from this fix, version and docs).
- **Not tested on live Odoo 19**: verify on staging before production.

## Deployment

1. Keep Documents-008 at the previously installed version; no upgrade needed.
2. Back up the deployed CRM-005 addon and Odoo database.
3. Replace `sgt_crm_yellowpages_profile`, restart/reload assets, upgrade module.
4. Hard refresh (Ctrl+Shift+R) or use `?debug=assets` to bypass stale JS.
5. Open a Deal; confirm Documents panel loads and legacy Image Gallery/other fields work.
6. Confirm Create Documents, existing folder, upload, Open in Documents with a test Deal.
7. If browser still shows the same error, inspect debug-assets + verify the latest JS bundle contains registration `component: Crm005DocumentsPanel`.

## Rollback

Revert CRM-005 code to backed-up version and upgrade module; database was not
changed by this fix.
