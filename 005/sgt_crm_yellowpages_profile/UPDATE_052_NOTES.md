# CRM-005 Update_052 — Compact Box + ZIP-aware Geocoding Query (11/11/2026)

## Goal
- Restore a small border box around Lat/Lon + **Get Coordinates**, with no heading, status text, hint or large blank area. Responsive wrap on narrow screens.
- Preserve Update_047 original first-pass geocoder service (`base.geocoder`) and the successful flow. Keep Update_051 helpful sticky warning on no-match and reload after success.
- In the **API query only**, ignore non-numeric content accidentally in the ZIP field for Vietnamese addresses. Do not modify the Deal's stored ZIP or any Contact.
- Keep Update_051 second street-preserving query without city/ZIP when a provider returns no match. Never resort to city-only centroid (can be misleading for B2B map).

## ARC Bình Dương case
- Example form screenshot shows ZIP containing a city name, and the Sóng Thần 2 industrial park moved administratively from Bình Dương to Ho Chi Minh City. A provider may lack the new address; even without malformed ZIP, a no-match is possible.
- Do not assume this patch guarantees a coordinate for the exact warehouse. Do not insert park-centre coordinates into the Deal automatically.
- For full accuracy, verify the address/location against a trusted map source and enter verified lat/lon manually if the provider cannot resolve it.

## Deployment
1. Backup DB and previous addon.
2. Replace addon with Update_052, restart all Odoo services/workers, Upgrade CRM-005 and hard-refresh assets.
3. Test a known working Deal, then ARC Bình Dương. Confirm field ZIP is unchanged by lookup, status on failure persists, manual coords preserved.
4. If ARC still has no results, inspect provider settings, real query and response in server logs (without logging credentials); validate address. Do not keep retrying hundreds of times.

## Verification limits
- Offline Python unit tests, XML parse, ZIP CRC only; no live provider/Odoo database integration was performed.
