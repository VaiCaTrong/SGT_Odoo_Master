"""Update 095 - XINYANG MAP "Potential Map" mode.

Uses the SAME Contact snapshot as the old XINYANG HEAT MAP (contact_heatmap_033.contact_map: one Company = one point,
partner_latitude / partner_longitude, current Deals of stage "5.Match Making" and "6.Approved Match Making"),
and only reshapes it into the record format of the XINYANG MAP page. Read only; no geocoding, no extra Odoo call
beyond what the old map already did, no new field.
"""
from __future__ import annotations

import time
from typing import Any

from .address import normalize_address, province_from_address
from .contact_map import ContactMapError, contact_map
from .deal_map import MM_PIPELINE_ID, MM_PIPELINE_NAME, WON_COLOR

ODOO_WEB_BASE_URL = ""

PIPELINE_ID = 3_000_000
PIPELINE_NAME = "MATCH MAKING"
# Same colours as the old map: yellow = Match Making, green = Approved Match Making, teal = both.
GROUPS = {
    "mm": (3_000_001, "5.Match Making", "#eab308"),
    "approved": (3_000_002, "6.Approved Match Making", "#16a34a"),
    "both": (3_000_003, "Cả 5.MM và 6.Approved", "#0b9e91"),
}


def _kind(mm: int, approved: int) -> str:
    return "both" if mm > 0 and approved > 0 else "approved" if approved > 0 else "mm"


def build_potential(snapshot: dict[str, Any]) -> dict[str, Any]:
    stage = snapshot.get("stage") or {}
    if not stage.get("available"):
        raise ContactMapError(str(stage.get("reason") or "Chưa xác minh được Stage CRM qua tài khoản hiện tại."))
    records: list[dict[str, Any]] = []
    for point in snapshot.get("points", []):
        mm, approved = point.get("mm_deals") or 0, point.get("approved_deals") or 0
        if mm <= 0 and approved <= 0:
            continue
        sid, sname, _color = GROUPS[_kind(mm, approved)]
        address = ", ".join(x for x in (point.get("city"), point.get("country")) if x)
        records.append({
            "id": int(point["id"]), "kind": "partner", "name": point.get("name") or f"Contact #{point['id']}",
            "company": point.get("name") or "", "contact": "", "phone": "", "mobile": "", "email": "",
            "address": normalize_address(address) if address else "", "province": province_from_address(address) or point.get("city") or "", "district": "",
            "event": "", "event_location": "", "expo": "", "salesperson": "", "pipeline": PIPELINE_NAME, "stage": sname,
            "pipeline_id": PIPELINE_ID, "stage_id": sid, "origin_id": 0, "tags": [],
            "lat": point["lat"], "lng": point["lon"], "geo_status": "mapped", "geo_status_raw": "", "geo_provider": "",
            "formatted_address": "", "geo_place_id": "", "geo_precision": "",
            "mm_deals": int(mm), "approved_deals": int(approved), "contacts": int(point.get("contacts") or 1),
            "archived": bool(point.get("archived")), "country": point.get("country") or "",
        })
    records.sort(key=lambda r: (-(r["mm_deals"] + r["approved_deals"]), r["name"].casefold()))
    stages = [{"id": sid, "name": name, "pipeline_id": PIPELINE_ID, "pipeline": PIPELINE_NAME, "is_won": key == "approved", "color": color}
              for key, (sid, name, color) in GROUPS.items()]
    return {
        "mode": "potential", "records": records,
        "status": {"state": "ok", "total": len(records), "mapped": len(records), "unmapped": 0,
                   "last_sync": None, "cache_seconds": 360,
                   "mm_contacts": stage.get("mm_contacts"), "approved_contacts": stage.get("approved_contacts"),
                   "both_contacts": stage.get("both_contacts"), "matched_deals": stage.get("matched_deals"),
                   "contacts_on_map": snapshot.get("mapped")},
        "config": {"odoo_url": ODOO_WEB_BASE_URL, "maptiles_key": "", "address_field": "partner_latitude/partner_longitude"},
        "stages": stages, "pipelines": [{"id": PIPELINE_ID, "name": PIPELINE_NAME}],
    }


def xinyang_potential(gateway, session, *, force: bool = False) -> dict[str, Any]:
    payload = build_potential(contact_map(gateway, session, force=force))
    payload["status"]["last_sync"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    return payload


# ---- Update 096: "Toàn bộ dữ liệu" = every Deal + the MM / Approved Contacts of the old map -------------------------------------
CONTACT_ID_BASE = 1_000_000_000      # record id of a Contact point = base + Contact id (never collides with a Deal id)
MM_STAGE_NAMES = {"mm": "5.Match Making", "approved": "6.Approved Match Making"}


def merge_contacts(deals: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the Deal payload plus one point for every MM / Approved Contact that no mapped Deal already shows.

    A Contact is skipped when a Deal with coordinates belongs to it (the Company point or one of its Contacts), so one
    customer is one point. Added points use the Deals' own MATCH MAKING stages (both -> 6.Approved Match Making)."""
    stage = snapshot.get("stage") or {}
    if not stage.get("available"):
        raise ContactMapError(str(stage.get("reason") or "Chưa xác minh được Stage CRM."))
    stages = [dict(s) for s in deals.get("stages", [])]
    pipelines = [dict(p) for p in deals.get("pipelines", [])]
    by_name = {s["name"]: s for s in stages if s.get("pipeline_id") == MM_PIPELINE_ID}
    for kind, name in MM_STAGE_NAMES.items():
        if name not in by_name:
            sid, _label, color = GROUPS[kind]
            row = {"id": sid, "name": name, "pipeline_id": MM_PIPELINE_ID, "pipeline": MM_PIPELINE_NAME, "is_won": kind == "approved",
                   "color": WON_COLOR if kind == "approved" else color}
            stages.append(row)
            by_name[name] = row
    if not any(p.get("id") == MM_PIPELINE_ID for p in pipelines):
        pipelines.append({"id": MM_PIPELINE_ID, "name": MM_PIPELINE_NAME})
    shown = {int(r["partner_id"]) for r in deals.get("records", []) if r.get("geo_status") == "mapped" and r.get("partner_id")}
    added: list[dict[str, Any]] = []
    for point in snapshot.get("points", []):
        mm, approved = point.get("mm_deals") or 0, point.get("approved_deals") or 0
        if mm <= 0 and approved <= 0:
            continue
        ids = {int(point["id"])} | {int(m["id"]) for m in point.get("members", []) if isinstance(m.get("id"), int)}
        if ids & shown:
            continue
        row = by_name[MM_STAGE_NAMES["approved" if approved > 0 else "mm"]]
        address = ", ".join(x for x in (point.get("city"), point.get("country")) if x)
        added.append({
            "id": CONTACT_ID_BASE + int(point["id"]), "pid": int(point["id"]), "kind": "partner", "name": point.get("name") or f"Contact #{point['id']}",
            "company": point.get("name") or "", "contact": "", "phone": "", "mobile": "", "email": "",
            "address": normalize_address(address) if address else "", "province": province_from_address(address) or point.get("city") or "",
            "district": "", "event": "", "event_location": "", "expo": "", "salesperson": "", "pipeline": MM_PIPELINE_NAME, "stage": row["name"],
            "pipeline_id": MM_PIPELINE_ID, "stage_id": row["id"], "origin_id": 0, "partner_id": int(point["id"]), "tags": [],
            "lat": point["lat"], "lng": point["lon"], "geo_status": "mapped", "geo_status_raw": "", "geo_provider": "",
            "formatted_address": "", "geo_place_id": "", "geo_precision": "",
            "mm_deals": int(mm), "approved_deals": int(approved), "contacts": int(point.get("contacts") or 1),
            "archived": bool(point.get("archived")), "country": point.get("country") or "",
        })
    # Update 099: stages added above must still follow 1,2,3,… (number at the start of the name)
    from .deal_map import _stage_number
    slots = [i for i, st in enumerate(stages) if st.get("pipeline_id") == MM_PIPELINE_ID]
    ordered = sorted((stages[i] for i in slots), key=lambda st: _stage_number(st.get("name", "")))
    for i, st in zip(slots, ordered):
        stages[i] = st
    records = list(deals.get("records", [])) + added
    status = dict(deals.get("status", {}))
    status.update({"contact_added": len(added), "total": len(records), "mapped": int(status.get("mapped", 0)) + len(added)})
    return {**deals, "records": records, "stages": stages, "pipelines": pipelines, "status": status}


__all__ = ["xinyang_potential", "build_potential", "merge_contacts", "GROUPS"]
