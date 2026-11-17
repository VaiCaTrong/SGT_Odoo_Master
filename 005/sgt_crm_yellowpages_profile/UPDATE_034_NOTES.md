# CRM-005 Update_034 — Fullscreen Product Image Gallery

**Base:** customer-provided `sgt_crm_yellowpages_profile_CRM-005_V01_Update_033(1).zip`.
**Module:** `sgt_crm_yellowpages_profile`; manifest `19.0.1.32.0` → `19.0.1.33.0`.
**Scope:** Only the Image Gallery readonly OWL field widget and its CSS. No new models/fields/ORM API/permissions/migrations.

## New (without Developer Mode)
- Click an image in **Image Gallery** to open a large dark, viewport-sized lightbox showing the whole picture (uncropped, original image source).
- Close using × / Esc / click dark background. Prev/next with onscreen arrows or keyboard Left/Right.
- Zoom controls − / +, reset, double-click zoom. Optional filmstrip for selecting another photo. Supports desktop and mobile responsive widths.
- Clicking images nested in links opens the preview rather than navigating away from the Deal.
- Viewer reads existing `x_yp_gallery_html` already on the page. No Odoo calls, edits, image copying into new fields, or writes occur during preview.

## Preserved
- `Image Gallery` remains `readonly="1"`; no Odoo HTML editor is mounted.
- Developer Mode-only delete ×, confirm dialog, original server-authorized `action_crm005_delete_gallery_image` and stale-gallery image checks are unchanged.
- The 4:3 gallery card layout, Partners gallery, Evidence box, Company Logo, import pipeline, fields, Stage/Funnel and all other addons are unchanged.
- No change to existing update migration scripts, data models or security.

## Change inventory
- `__manifest__.py`: version increment only.
- `static/src/js/gallery_manage.js`: add viewer presentation alongside Update_033 widget and preserve deletion.
- `static/src/scss/yellowpages_profile.scss`: append scoped viewer styles; existing SCSS rules unchanged.
- `tests/test_update034_lightbox_offline.py`: add offline source/regression checks.
- `tests/test_update007_offline.py`, `tests/test_update010_layout.py`: repair stale version assertions that predate Update_032/033 (tests only).
- `UPDATE_034_NOTES.md`: release and validation guidance.

## Install / rollback
1. Backup module and database, then upgrade the **existing** addon from this ZIP on an Odoo 19 staging copy first; retain its folder name `sgt_crm_yellowpages_profile`.
2. Upgrade the module through Odoo Apps (or standard `-u sgt_crm_yellowpages_profile` deployment process) so the backend asset bundle is rebuilt. Hard-reload the browser; `?debug=assets` if asset caching prevents new JS loading.
3. Check a Deal with multiple gallery pictures: click thumbnails, navigate, zoom, close; ensure the entire photo appears without cropping. Test mobile size and pictures wrapped in anchors.
4. With Developer Mode ON, verify the independent Delete × and successful server persistence; confirm the × does not appear otherwise. Recheck Partners, Evidence, logo and importing via Chrome extension.
5. Rollback requires restoring the prior addon ZIP and database backup if module upgrade affected data; do not merely downgrade the manifest number. This change itself adds no migration and performs no preview write.

## QA status
- JavaScript syntax and Python compile checks, XML parse, offline unit tests: see accompanying delivery report.
- Odoo 19 live/staging and Chrome Extension integration: **not executed here**, must validate before production.
- This ZIP is an **installable addon package**, not a claim that any production server was modified.
