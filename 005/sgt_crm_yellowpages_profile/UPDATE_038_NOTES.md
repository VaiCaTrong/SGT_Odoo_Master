# CRM-005 Update_038 — Spacing between cards in each Opportunity Kanban column

## Request
- Separate Deal cards vertically **16px** in the same Opportunity Stage column.
- Do not change internal card padding, contents, columns, logo, scrolling company title, or click-to-open behavior.
- Implement in **CRM-005 only**, not CRM-002 or manual Odoo UI edits.

## Changes from Update_037
1. `static/src/css/kanban_company_logo.css`: added scoped CSS for the actual Odoo Kanban record wrapper:

   ```css
   .o_opportunity_kanban .o_kanban_group .o_kanban_record {
       margin-bottom: 16px !important;
   }
   ```

   This is intentional: changing `<t t-name="card" class="mb-3">` alone in the Kanban XML did not affect the user's live spacing. The template is not the record wrapper.
2. `__manifest__.py`: increment version from `19.0.1.36.0` to `19.0.1.37.0`; the CSS was already included in `web.assets_backend`.
3. `README.md`, this note and offline tests: documentation and regression checks.

**No changes** to views, Python fields, models, RPC, migrations, security, JavaScript, company logo behavior, gallery/lightbox, CRM-002, or Extension. The user's Studio/UI Kanban XML edits remain outside this ZIP; do not overwrite them.

## Verify on staging Odoo 19 before production
1. Back up database and module Update_037; install/upgrade Update_038.
2. Force reload browser / rebuild backend assets if needed; ensure updated `kanban_company_logo.css` is loaded.
3. In CRM Opportunity Kanban with multiple Deal cards per Stage, measure the vertical space: each card must be visually separated, around **16px** additional bottom margin.
4. Confirm the gap does not affect card contents or horizontal column widths. Check a folded column and mobile layout.
5. Hover a long company name from any part of a card: text still scrolls. Click the company name/logo: form still opens. Confirm Kanban remains view-only.
6. If the spacing still looks unchanged, inspect the *rendered* card in DevTools and verify its `margin-bottom` computed style and whether the current Opportunity Kanban DOM uses `.o_kanban_group .o_kanban_record`. Check asset cache before changing any other code.

**Verification status:** static/offline checks only; current Odoo staging or production runtime not accessible. The exact effective spacing depends on Odoo's built-in gap and the installed theme; no runtime layout guarantee is claimed.
