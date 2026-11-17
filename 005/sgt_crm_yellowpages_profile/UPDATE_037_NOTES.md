# CRM-005 Update_037 — Kanban company name font and card-wide marquee

## Scope

- Base: Update_036 / `19.0.1.35.0`.
- Manifest: `19.0.1.36.0`.
- Kanban company name: 20px desktop / 18px at `max-width: 600px`, bold weight 700.
- Hover over **any part of the Opportunity Kanban record** starts the pre-existing marquee for the company name **only when it overflows**; leaving the record stops the animation and resets the horizontal offset. Moving between elements inside the same record does not restart it.
- All company-name/logo clicks still open the Deal form through `type="open"`.
- Preserves native accessibility `prefers-reduced-motion`; direct-hover marquee behavior on other CRM-005 fields is unchanged.
- Does not modify field definitions, database, permissions, CRM-002, gallery/lightbox, logo selection, or Kanban read-only behavior.

## Files changed relative to Update_036

- `__manifest__.py` — version increment only.
- `static/src/css/kanban_company_logo.css` — company-name font sizes, comment.
- `static/src/js/sgt_marquee.js` — scoped delegated card hover and card-leave reset; keeps legacy form behavior.
- `views/crm_yp_lead_kanban.xml` — comments only; no structural changes to view.
- `README.md`, `UPDATE_037_NOTES.md`, and offline test files.

## Install and verification

1. Back up DB and Update_036; upgrade module on a staging Odoo 19 instance.
2. On Kanban hover over logo, notes, footer, whitespace and company name, verify long company name scrolls; short name remains still.
3. Move pointer between elements inside the same card: animation must continue. Move outside: it resets.
4. Verify all company logo fallbacks, clicking logo/name to open Deal, stage/card edit remains disabled, and full Deal edits are unchanged.
5. Check narrow mobile screen, multiple cards, reduced-motion preference and legacy Yellow Pages form marquee.

**Important:** Local static tests cannot validate the current server's customized Kanban view or production asset cache. No production deployment performed.
