# CRM-005 Update_051 — Compact Geolocation + Visible Result (11/11/2026)

## Root cause and scope
- Update_050 constrained each Float widget to 8.2rem even in read mode, leaving blank space and stretching the row.
- The Get Coordinates button used a short-lived notification with `next: reload` for both success and failure; with a non-matching address, the UI can appear unchanged (Lat/Lon remain 0).
- This is **not** evidence that every failed lookup is a click-handler bug. Provider/network errors, unmatched postal addresses, or an unconfigured provider can produce no coordinates. No Production logs were available to prove the exact cause for ARC Bình Dương.

## Changes
1. CSS only on `.sgt_yp_geoloc_*`: read-only values use their intrinsic width; in edit mode inputs have a bounded width; button sits immediately next to numbers, and row wraps on narrow devices. No large box, status caption or instructions in the form.
2. Manual Get Coordinates: success returns native `reload` action; failure returns a persistent English warning notification **without reload**; provider error differentiated from zero results. No fake latitude/longitude.
3. Query: full street + street2 + zip/city/state/country, then (if city or ZIP supplied) one retry with street + street2 + state/country, never city-only fallback.
4. Preserves existing cron behavior, status fields, automatic Extension-triggered queue, manual-coordinate safeguard, New, Kanban drag, Documents and Gallery.

## Deployment / Test
- Update all addon files; **restart Odoo processes before Upgrade**; Upgrade `sgt_crm_yellowpages_profile`; Ctrl+Shift+R.
- Test a Deal already known to have coordinates, a precise address, an unknown address, missing street and a provider failure. A no-match **must show a persistent warning**, not silently leave zero.
- If provider consistently returns no matches, inspect Odoo Settings > Geolocation and server logs. The software cannot guarantee a coordinate for every address.
- Tests are offline/mocked; Production acceptance testing is still necessary.
