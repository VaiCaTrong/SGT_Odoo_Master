# CRM-005 Update_053 — Diagnose geolocation failures and find exact location manually

Date: 2026-11-11. Based on Update_052, full addon update, Odoo 19.

## Cause and scope
For the ARC Binh Duong record, the provider returns no valid result for the precise industrial lot address. This is not proof the address is wrong. Odoo 19 base.geocoder may return None for valid addresses that are not indexed in the selected service. There is no reliable way to guarantee an exact business location using that service alone.

## Changes
- Keep existing compact Lat/Lon box and automatic / manual geolocation logic unchanged.
- On Get Coordinates failure, keep a sticky diagnostic warning and include the configured provider name when available, followed by steps to find/verify the address manually.
- Add small **Find on Map** action alongside Get Coordinates. It opens Google Maps search by company name + Deal address, in a new tab. Only the user's explicit click shares those search terms with Google. No Google API key is needed for searching manually.
- The action neither creates a Contact nor changes coordinates. User can choose the precise pin and copy latitude/longitude into existing editable Lat/Lon fields, then save. Existing write() logic marks those values manual, safe from auto-overwrite.
- Never auto-store city/industrial-park centroid coordinates as the company's exact location.

## Limits
- Without a valid match from the configured Odoo provider, Get Coordinates still cannot auto-fill data. For improved automatic accuracy, consider configuring the existing Google Maps geocoding provider and its required key/billing in Odoo Settings. This is a separate server configuration, not an addon bug.
- Not tested against actual Odoo Production, provider keys, Odoo server network, or ARC exact geo-coordinate.

## Deploy
1. Backup Xinyang DB and current addon.
2. Replace the whole sgt_crm_yellowpages_profile addon. Restart all Odoo processes, Upgrade the module, hard reload browser.
3. Get Coordinates on a known working Deal and ARC; ARC no match should show provider and Find on Map instructions, no fake coordinates.
4. Use Find on Map to locate the correct business pin, copy GPS coordinates into Lat/Lon and Save. Change address later should mark manual location for review, not overwrite.
5. Verify Extension imports, cron, Kanban drag/New, Docs and Gallery.
