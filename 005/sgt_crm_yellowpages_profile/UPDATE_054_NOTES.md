# CRM-005 Update_054 — Progressive Geolocation + Original Screenshot UI

## Goal
- Geocode CRM Deals through **Odoo native `base.geocoder`**, without Create Contact or Google API integration.
- Progressive fallback: detailed address -> simplified street -> ward/neighborhood -> city -> province/state. A country-only location is never accepted.
- Store the tier in a NEW backend field: `crm.lead.x_yp_geo_precision` (`address`, `neighborhood`, `city`, `region`, `manual`), and retain existing status/date/signature fields. Every provider result is unverified unless checked by a human. Do **not** map `address` to a "verified" guarantee.
- Preserve manual GPS values and prevent even button-initiated replacement unless both manually entered values have been cleared and saved.
- Extension creates/updates with new address -> queue via existing CRM-005 cron 5 deals per run; no network calls in the import request.
- UI: keep full-width light-blue geolocation box screenshot: heading `Geolocation · CRM Deal`, Latitude, Longitude beneath, one `Get Coordinates` button top right. No status/help/Find on Map in UI. Backend Find on Map action retained for compatibility.

## Upgrade
1. Backup database / addon. Replace entire folder `sgt_crm_yellowpages_profile` with the new package.
2. Restart ALL Odoo workers (the module declares a new Python field) **before** Upgrade.
3. Apps -> Upgrade `sgt_crm_yellowpages_profile`, refresh web assets (Ctrl+Shift+R).
4. Test: ARC Bình Dương Deal with complete address; Get Coordinates; check `x_yp_geo_precision` with developer mode. Verify a nearby area estimate is *not* called an exact company pin.
5. Test: manually entered coordinates, change address from Extension, successful/failed geocoder, provider outage, no existing Contact.
6. Dashboard must treat `region`/`city`/`neighborhood` as approximate pins. Map backfill needs an independent Admin trigger; Update_054 does not retroactively queue all old Deals.

## Caveats
- Odoo geocoding provider data may not resolve any address; no address can be guaranteed.
- Mock/offline tests do not verify production provider configuration or live accuracy.
- `x_yp_geo_precision` is not shown in the box per requested layout, but remains available via ORM to Dashboard/reporting.
- CRM-005 model still requires `base_geolocalize` dependency, does not alter CRM-006/007 or Contacts.
