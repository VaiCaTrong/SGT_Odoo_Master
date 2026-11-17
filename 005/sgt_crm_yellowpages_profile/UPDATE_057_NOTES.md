# CRM-005 Update_057 — Compact Geolocation / Copy / Google Maps

Base: CRM-005 Update_056, manifest 19.0.1.56.0.

## User-facing change
- Replace the full-width two-row light-blue Geolocation card with a compact, content-width, responsive single-row bar beneath Address.
- Keep Latitude and Longitude editable, and preserve the existing Get Coordinates server button.
- Add Copy to copy `latitude, longitude` (e.g. `20.8497977, 106.6621584`).
- Add Google Maps to open `https://www.google.com/maps/search/?api=1&query=<lat>,<lon>` in a new tab.
- Copy and Google Maps are disabled when both coordinates are 0 or values are outside the valid coordinate range.
- The Google Maps URL is opened only on a deliberate user click and reveals the displayed coordinates to Google.

## No change
- No change to models, Cron, Odoo geocoding, automatic Extension-triggered location updates, last-known-good coordinate preservation from Update_056, Contact synchronization, Documents or Gallery.
- No new ORM field or database migration; only XML, SCSS, static OWL widget and asset manifest.

## Upgrade / smoke test
1. Back up database and existing addon; replace entire `sgt_crm_yellowpages_profile` folder and restart all Odoo workers.
2. Upgrade addon via Apps; hard refresh web assets.
3. Open a Deal with saved Lat/Lon: ensure Copy gives `lat, lon`; Map opens exactly that point, in a new tab.
4. On Lat/Lon = 0 and 0, Copy/Google Maps are disabled; Get Coordinates still works.
5. Edit Lat/Lon manually and save; ensure values persist. Test an Extension Address update and failed geocoder retry: Update_056 last-known-good behavior must persist.
6. Check on narrow screen, and inspect browser console and Odoo server logs.

Offline tests do not prove behavior on Production; stage before deployment.
