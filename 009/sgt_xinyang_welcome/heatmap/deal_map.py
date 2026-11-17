"""Update 094: XINYANG MAP (customer map ported from the Gearea Report Dashboard v4.16.0).

One CRM Deal = one point. Read only: the Deals are read with the logged-in user's own Odoo Xinyang session (record rules apply),
no write, no geocoding, no new connector. Coordinates are the ones already stored on the Deal by CRM-005 (x_yp_latitude / x_yp_longitude).

Update 098: ONE pipeline only. Every active Deal belongs to the big funnel "MATCH MAKING" and its stage is the CRM stage_id
(1.Opportunity ... 8.Mark Lost), exactly as the Odoo Match Making funnel counts it. The CRM-002 Data / Sale funnels
(Outbound Hunter, Inbound Pool, New) are NOT split out any more, so the Dashboard total = the Odoo Match Making total.
"""
from __future__ import annotations

import math
import threading
import time
from datetime import datetime, timezone
from typing import Any

from .adapter import OdooGateway, OdooSession
from .address import district_from_address, normalize_address, province_from_address
from .contact_map import ContactMapError

ODOO_WEB_BASE_URL = ""   # the controller puts the real origin into config.odoo_url (links to the Deal / Contact forms)

MAP_CACHE_SECONDS = 300
BATCH = 2000
LAT, LNG = "x_yp_latitude", "x_yp_longitude"
FUNNEL, STEP = "sgt_crm002_funnel_id", "sgt_crm002_step"
SALE_FUNNEL, SALE_STAGE = "sgt_crm002_sale_funnel_id", "sgt_crm002_sale_stage_id"
POTENTIAL_LABEL = "3.Potential"
MM_PIPELINE_ID, MM_PIPELINE_NAME = 900001, "MATCH MAKING"
SALE_PIPE_BASE, STEP_BASE, SALE_STAGE_BASE = 800000, 1_000_000, 2_000_000
WON_STAGES = {"6.approved match making", "9.approved match making"}
FAILED_STATUSES = {"failed", "error", "not_found", "unmapped", "no_result"}
REQUIRED = {"name", "stage_id", LAT, LNG}
OPTIONAL = ["partner_id", "partner_name", "contact_name", "phone", "x_phone", "mobile", "email_from", "user_id", "tag_ids",
            "x_expo", "x_event", "x_event_location", "street", "street2", "city", "state_id", "country_id",
            "x_yp_geo_status", "x_yp_geo_precision", "x_yp_geo_updated_at"]

# cold -> hot by position inside a pipeline; the Won stage is always green (same palette as Gearea)
FUNNEL_PALETTE = ("#94A3B8", "#3B82F6", "#06B6D4", "#F59E0B", "#E11D48", "#7C5CC4", "#0F9EAA", "#C98A12", "#64748B", "#B45309")
WON_COLOR = "#16A34A"

_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def _rel(value: Any) -> str:
    return str(value[1] or "") if isinstance(value, (list, tuple)) and len(value) >= 2 else ""


def _id(value: Any) -> int:
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], int) and not isinstance(value[0], bool):
        return value[0]
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return _rel(value)
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def _coord(value: Any):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _gps(row: dict) -> tuple[float | None, float | None, str]:
    lat, lng = _coord(row.get(LAT)), _coord(row.get(LNG))
    if (lat is None or lat == 0) and (lng is None or lng == 0):
        return None, None, "missing"          # an empty Odoo Float is 0.0
    if lat is None or lng is None:
        return None, None, "partial"
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None, None, "invalid"
    return lat, lng, "valid"


def _address(row: dict) -> str:
    parts = [_text(row.get(k)) for k in ("street", "street2", "city", "state_id", "country_id")]
    return normalize_address(", ".join(p for p in parts if p))


def _stage_number(name: str) -> int:
    """Leading number of a stage name ("3.Interacted" -> 3); 999 when the name has none."""
    digits = ""
    for ch in (name or "").strip():
        if ch.isdigit():
            digits += ch
        else:
            break
    return int(digits) if digits else 999


def _stage_sequences(gateway: OdooGateway, session: OdooSession, stage_ids: list[int]) -> dict[int, int]:
    """Update 099: real crm.stage.sequence (read only). Optional: any error just means the name numbers are used."""
    out: dict[int, int] = {}
    ids = [i for i in stage_ids if isinstance(i, int) and i > 0]
    if not ids:
        return out
    try:
        for r in gateway.call(session, "crm.stage", "read", [ids], {"fields": ["sequence"]}) or []:
            if isinstance(r, dict) and isinstance(r.get("id"), int) and isinstance(r.get("sequence"), int) and not isinstance(r.get("sequence"), bool):
                out[r["id"]] = r["sequence"]
    except Exception:  # noqa: BLE001 - ordering falls back to the number in the stage name
        return {}
    return out


def stage_meta(stage_rows: list[dict], pipe_order: dict[int, int]) -> tuple[list[dict], list[dict]]:
    """[{id,name,pipeline_id,pipeline,is_won,color}] ordered by pipeline then sequence, plus [{id,name}] pipelines (same shape as Gearea)."""
    pipes: dict[int, dict] = {}
    for s in stage_rows:
        pid = _id(s.get("pipeline_id"))
        if pid and pid not in pipes:
            pipes[pid] = {"id": pid, "name": _rel(s.get("pipeline_id")), "seq": pipe_order.get(pid, 10_000 + len(pipes))}
    by_pipe: dict[int, list[dict]] = {}
    for s in stage_rows:
        by_pipe.setdefault(_id(s.get("pipeline_id")), []).append(s)
    position: dict[int, int] = {}
    for rows in by_pipe.values():
        idx = 0
        for s in sorted(rows, key=lambda x: (x.get("sequence") or 0, x["id"])):
            if not s.get("is_won"):
                position[s["id"]] = idx
                idx += 1
    out = []
    for s in sorted(stage_rows, key=lambda x: (pipes.get(_id(x.get("pipeline_id")), {}).get("seq", 999), x.get("sequence") or 0, x["id"])):
        pid = _id(s.get("pipeline_id"))
        out.append({"id": s["id"], "name": _text(s.get("name")), "pipeline_id": pid, "pipeline": pipes.get(pid, {}).get("name", ""),
                    "is_won": bool(s.get("is_won")),
                    "color": WON_COLOR if s.get("is_won") else FUNNEL_PALETTE[position.get(s["id"], 0) % len(FUNNEL_PALETTE)]})
    return out, [{"id": p["id"], "name": p["name"]} for p in sorted(pipes.values(), key=lambda p: p["seq"])]


def _place(row: dict, step_labels: dict[str, tuple[int, str]]) -> tuple[int, str, int, str, int, bool]:
    """-> (pipeline_id, pipeline name, stage id, stage name, sequence, is_won). Update 098: always the Match Making funnel."""
    stage = row.get("stage_id")
    name = _rel(stage)
    return MM_PIPELINE_ID, MM_PIPELINE_NAME, _id(stage), name, 0, name.strip().casefold() in WON_STAGES


# CRM-005 (Update 054) x_yp_geo_precision: how exact the stored coordinate is. Only "address" and "manual" are point-like;
# the others are the centre of an area and must not be read as the company's exact position.
PRECISION = {"address": ("Địa chỉ", False), "neighborhood": ("Phường/xã (ước lượng)", True), "city": ("Thành phố (ước lượng)", True),
             "region": ("Tỉnh/thành (ước lượng)", True), "manual": ("Nhập tay", False)}
PARTNER_FIELDS = ("partner_latitude", "partner_longitude", "street", "street2", "city", "state_id", "country_id", "commercial_partner_id")
CONTACT_SOURCE = "Contact"


def _partner_geo(gateway: OdooGateway, session: OdooSession, rows: list[dict]) -> tuple[dict[int, dict], str]:
    """Update 096: {partner id: {"coords": (lat, lng) | None, "address": str}} for the Contacts of the Deals (read only).

    A Deal that has no coordinates of its own borrows its Contact's partner_latitude/longitude (or its Company's).
    Any failure only disables the borrowing: the Deals themselves still show."""
    ids = sorted({_id(r.get("partner_id")) for r in rows if _id(r.get("partner_id"))})
    if not ids:
        return {}, ""
    try:
        available = set(gateway.fields(session, "res.partner"))
        if not {"partner_latitude", "partner_longitude"} <= available:
            return {}, "res.partner chưa có partner_latitude/partner_longitude"
        fields = [f for f in PARTNER_FIELDS if f in available]
        data: dict[int, dict] = {}

        def read(batch: list[int]) -> None:
            for pos in range(0, len(batch), 500):
                for p in gateway.call(session, "res.partner", "read", [batch[pos:pos + 500]], {"fields": fields, "context": {"active_test": False}}):
                    data[int(p["id"])] = p

        def point(p: dict):
            lat, lng, issue = _gps({LAT: p.get("partner_latitude"), LNG: p.get("partner_longitude")})
            return (lat, lng) if issue == "valid" else None

        read(ids)
        parents = sorted({_id(p.get("commercial_partner_id")) for p in data.values() if not point(p)} - {0} - set(data))
        read(parents)
        out: dict[int, dict] = {}
        for pid in ids:
            p = data.get(pid)
            if not p:
                continue
            parent = data.get(_id(p.get("commercial_partner_id")))
            chain = [p] + ([parent] if parent and parent is not p else [])
            hit = next((c for c in chain if point(c)), None)
            out[pid] = {"coords": point(hit) if hit else None, "address": next((a for a in (_address(c) for c in chain) if a), "")}
        return out, ""
    except Exception as exc:  # noqa: BLE001 - optional enrichment
        return {}, str(exc)[:200]


def _record(row: dict, tags: dict[int, str], step_labels: dict[str, tuple[int, str]], partner_geo: dict[int, dict] | None = None) -> tuple[dict, dict] | None:
    lat, lng, issue = _gps(row)
    address = _address(row)
    source = ""
    borrowed = (partner_geo or {}).get(_id(row.get("partner_id")))
    if issue == "missing" and borrowed and borrowed["coords"]:      # no coordinates on the Deal -> the Contact's
        (lat, lng), issue, source = borrowed["coords"], "valid", CONTACT_SOURCE
    if not address and borrowed and borrowed["address"]:
        address = borrowed["address"]
    if not address and issue == "valid":
        address = f"{lat:.6f}, {lng:.6f}"
    raw = "Tọa độ lấy từ Contact (partner_latitude / partner_longitude)" if source else _text(row.get("x_yp_geo_status"))
    precision, approx = ("", False)
    if source:
        precision, approx = "Contact", True          # the Contact's point, not the Deal's own address
    elif issue == "valid":
        precision, approx = PRECISION.get(_text(row.get("x_yp_geo_precision")).strip().lower(), ("", False))
    if issue == "valid":
        status = "mapped"
    elif issue in ("invalid", "partial"):
        status = "invalid"
    elif raw.strip().lower() in FAILED_STATUSES:
        status = "unmapped"
    else:
        status = "pending"
    pid, pname, sid, sname, seq, won = _place(row, step_labels)
    partner = row.get("partner_id")
    record = {
        "id": int(row["id"]), "name": _text(row.get("name")),
        "company": _rel(partner) or _text(row.get("partner_name")) or _text(row.get("name")),
        "contact": _text(row.get("contact_name")) or _rel(partner),
        "phone": _text(row.get("phone")) or _text(row.get("x_phone")), "mobile": _text(row.get("mobile")),
        "email": _text(row.get("email_from")), "address": address,
        "province": province_from_address(address), "district": district_from_address(address),
        "event": _text(row.get("x_event")), "event_location": _text(row.get("x_event_location")),
        "expo": _text(row.get("x_expo")), "salesperson": _rel(row.get("user_id")),
        "pipeline": pname, "stage": sname, "pipeline_id": pid, "stage_id": sid, "origin_id": 0, "partner_id": _id(partner),
        "tags": [tags.get(t, f"Tag #{t}") for t in (row.get("tag_ids") or []) if isinstance(t, int)],
        "lat": lat, "lng": lng, "geo_status": status, "geo_status_raw": raw, "geo_provider": precision,
        "formatted_address": "", "geo_place_id": "", "geo_precision": precision, "geo_approx": approx, "geo_updated_at": "" if source else _text(row.get("x_yp_geo_updated_at")),
    }
    stage_row = {"id": sid, "name": sname, "sequence": seq, "is_won": won, "pipeline_id": [pid, pname]}
    return record, stage_row


def _step_labels(gateway: OdooGateway, session: OdooSession, available: set[str]) -> dict[str, tuple[int, str]]:
    """selection key -> (position, label) of sgt_crm002_step, from the real field definition."""
    if STEP not in available:
        return {}
    try:
        meta = gateway.fields_get(session, "crm.lead", [STEP]).get(STEP) or {}
    except Exception:  # noqa: BLE001 - the step is optional: without it Data funnel Deals fall back to Match Making stage
        return {}
    selection = meta.get("selection")
    if not isinstance(selection, list):
        return {}
    return {str(key): (pos, str(label)) for pos, (key, label) in enumerate(item for item in selection if isinstance(item, (list, tuple)) and len(item) == 2)}


def build_payload(gateway: OdooGateway, session: OdooSession) -> dict[str, Any]:
    available = set(gateway.fields(session, "crm.lead"))
    missing = sorted(REQUIRED - available)
    if missing:
        raise ContactMapError("Xinyang Odoo chưa có field " + ", ".join(missing) + " — cần cập nhật CRM-005 (Update 047).")
    fields = sorted(REQUIRED) + [f for f in OPTIONAL if f in available]
    domain: list[Any] = []   # Update 096: every active Deal, with or without an address (the place may come from its Contact)
    total = gateway.call(session, "crm.lead", "search_count", [domain])
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ContactMapError("Odoo trả số Deal CRM không hợp lệ.")
    rows: list[dict] = []
    last_id = 0
    while len(rows) < total:
        page = gateway.call(session, "crm.lead", "search_read", [domain + [["id", ">", last_id]]],
                            {"fields": fields, "limit": BATCH, "order": "id asc"})
        if not isinstance(page, list) or not page:
            break
        rows.extend(page)
        last_id = max(int(r["id"]) for r in page)
        if len(page) < BATCH:
            break
    if len({r["id"] for r in rows}) != len(rows):
        raise ContactMapError("ID Deal CRM bị trùng trong lần đọc, hãy bấm Đọc lại.")
    tag_ids = sorted({t for r in rows for t in (r.get("tag_ids") or []) if isinstance(t, int)})
    tags: dict[int, str] = {}
    for pos in range(0, len(tag_ids), 500):
        try:
            for tag in gateway.call(session, "crm.tag", "read", [tag_ids[pos:pos + 500]], {"fields": ["name"]}):
                tags[tag["id"]] = tag.get("name") or ""
        except Exception:  # noqa: BLE001 - tag names are optional
            break
    step_labels: dict[str, tuple[int, str]] = {}   # Update 098: the Data / Sale funnel split is gone, only Match Making remains
    partner_geo, partner_error = _partner_geo(gateway, session, rows)
    records, stage_rows, seen = [], [], set()
    for row in rows:
        built = _record(row, tags, step_labels, partner_geo)
        if not built:
            continue
        record, stage_row = built
        records.append(record)
        if stage_row["id"] and stage_row["id"] not in seen:
            seen.add(stage_row["id"])
            stage_rows.append(stage_row)
    seqs = _stage_sequences(gateway, session, [s["id"] for s in stage_rows])
    for s in stage_rows:
        # order: number in the stage name first ("1.Opportunity" … "8.Mark Lost"), then Odoo's own sequence, then id
        s["sequence"] = _stage_number(s["name"]) * 100000 + seqs.get(s["id"], 0)
    records.sort(key=lambda r: r["id"], reverse=True)
    # pipeline order: Data funnels, then Match Making, then Sale funnels
    order = {p: i for i, p in enumerate(sorted({_id(s["pipeline_id"]) for s in stage_rows},
                                              key=lambda p: (2 if p >= SALE_PIPE_BASE and p != MM_PIPELINE_ID else 1 if p == MM_PIPELINE_ID else 0, p)))}
    stages, pipelines = stage_meta(stage_rows, order)
    mapped = sum(1 for r in records if r["geo_status"] == "mapped")
    return {
        "records": records,
        "status": {"state": "ok", "total": len(records), "mapped": mapped, "unmapped": len(records) - mapped,
                   "borrowed": sum(1 for r in records if r["geo_provider"] == CONTACT_SOURCE), "approx": sum(1 for r in records if r.get("geo_approx") and r["geo_status"] == "mapped"), "contact_geo_error": partner_error,
                   "last_sync": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cache_seconds": MAP_CACHE_SECONDS},
        "config": {"odoo_url": ODOO_WEB_BASE_URL, "maptiles_key": "", "address_field": "street/street2/city/state_id/country_id"},
        "stages": stages, "pipelines": pipelines,
    }


def xinyang_map(gateway: OdooGateway, session: OdooSession, *, force: bool = False) -> dict[str, Any]:
    key = session.token   # database + user: two databases in one worker never share a snapshot
    now = time.time()
    with _lock:
        hit = _cache.get(key)
    if hit and not force and now - hit[0] < MAP_CACHE_SECONDS:
        return hit[1]
    payload = build_payload(gateway, session)
    with _lock:
        _cache[key] = (now, payload)
    return payload


def forget_xinyang_map() -> None:
    with _lock:
        _cache.clear()


# Update 101: company logo of a Deal (read only, one record, only when the detail box opens; never in the map snapshot).
# CRM-005: x_yp_logo_upload (Binary, manual upload) wins over x_image (Char, data-URI written by the Extension), same as the Odoo form.
LOGO_FIELDS = ("x_yp_logo_upload", "x_image")
MAX_LOGO_CHARS = 700_000


def _logo_uri(raw: Any) -> str:
    import base64
    import binascii
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_LOGO_CHARS:
        return ""
    text = raw.strip()
    if text.lower().startswith("data:"):
        head, _, body = text.partition(",")
        if ";base64" not in head.lower():
            return ""
        text = body
    try:
        binary = base64.b64decode(text, validate=True)
    except (ValueError, binascii.Error):
        return ""
    if binary.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif binary.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif binary.startswith(b"GIF8"):
        mime = "image/gif"
    elif binary.startswith(b"RIFF") and binary[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        return ""                     # not an image (e.g. old import text "RawData_00_Images/…")
    return "data:" + mime + ";base64," + text


def lead_logo(gateway: OdooGateway, session: OdooSession, lead_id: int) -> dict[str, Any]:
    if isinstance(lead_id, bool) or not isinstance(lead_id, int) or lead_id <= 0:
        raise ContactMapError("ID Deal không hợp lệ.")
    available = [f for f in LOGO_FIELDS if f in set(gateway.fields(session, "crm.lead"))]
    if not available:
        return {"logo": "", "source": ""}
    rows = gateway.call(session, "crm.lead", "read", [[lead_id], available], {"context": {"active_test": False}})
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ContactMapError("Không tìm thấy Deal hoặc không có quyền xem.")
    for field in available:
        uri = _logo_uri(rows[0].get(field))
        if uri:
            return {"logo": uri, "source": field}
    return {"logo": "", "source": ""}


__all__ = ["xinyang_map", "build_payload", "stage_meta", "forget_xinyang_map", "lead_logo"]
