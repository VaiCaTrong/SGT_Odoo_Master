# CRM-005 Update_033: Image Gallery individual deletion

- Based directly on user-supplied Update_032 package.
- In Image Gallery, individual delete (×) buttons appear only with Odoo Developer Mode enabled (`?debug=1`/`?debug=assets`).
- Confirmation dialog required. Backend removes only the selected image from `crm.lead.x_yp_gallery_html`, without mounting the large HTML editor; reloads after save.
- Server enforces `crm.lead` write access and record rules; frontend Developer Mode is not an authorization boundary.
- Blocks deleting stale image positions if the gallery's image count or selected image source prefix has changed.
- Partners, Evidence, logo, introductions and other fields are unchanged.
- Upgrade module to load the updated view and JS/XML/CSS web assets. Hard refresh browser after upgrade.
- Needs acceptance testing in actual Odoo 19 environment: open Deal > Developer Mode > delete one Image Gallery picture > confirm > inspect remaining images > reload. Verify no control without Developer Mode and no write permission access.
