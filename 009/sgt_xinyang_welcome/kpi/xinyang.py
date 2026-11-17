"""KPIs read from THIS Odoo (Xinyang CRM): Data · KH tiềm năng, Match Making, Approved Match Making.

Ported from the Management Dashboard (``prospects_xinyang`` / ``funnels_022`` / ``mm_xinyang`` / ``approved_mm_xinyang``).
Every call goes through ``OdooEnvGateway`` = the signed-in user's own environment, so access rights and record rules of the
CRM apply: a Sales user only counts the Deals they may see. Read only; a value that cannot be verified is reported as an
error / "chưa xác minh", never as a guessed zero.

* Data · KH tiềm năng: Deals FIRST handed over INTO Match Making › 1.Opportunity (CRM-002 log note "Bàn giao Deal (CRM-002)",
  "Sang: <Match Making> › 1.Opportunity", date = mail.message.date, once per Deal).
* Match Making / Approved Match Making: Deals CURRENTLY in stage "5.Match Making" / "6.Approved Match Making", dated by the
  earliest Chatter tracking of ``stage_id`` from ANOTHER stage into it. Deals without such tracking are not counted and are
  reported separately (``unverified_count``).
"""
from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from . import evidence as ev
from .period import HCM, Period, delta

LEAD = "crm.lead"
STAGE = "crm.stage"
MESSAGE = "mail.message"
TRACK = "mail.tracking.value"
FIELD = "ir.model.fields"

FUNNEL = "sgt_crm002_funnel_id"
STEP = "sgt_crm002_step"
SALE_FUNNEL = "sgt_crm002_sale_funnel_id"
OPPORTUNITY_LABEL = "1.Opportunity"
HANDOFF_MARK = "Bàn giao Deal (CRM-002)"
ARROW = " › "

# The two stages were renamed in place more than once; Chatter keeps the name that existed when the Deal moved.
STAGES = {
    "mm": {"names": ("5.Match Making", "8.Match Making"), "aliases": ("5.MM", "8.Match Making", "5.Match Making"),
           "label": "Match Making"},
    "approved": {"names": ("6.Approved Match Making", "9.Approved Match Making"),
                 "aliases": ("6.Approved Match Making", "9.Approved Match Making"), "label": "Approved Match Making"},
}
# CRM fields shown for each Deal of the Match Making page. Only fields that exist in this database are read (nothing is created).
DETAIL_FIELDS = ("partner_name", "contact_name", "function", "email_from", "website", "street", "city", "state_id", "country_id",
                 "source_id", "tag_ids", "description", "create_date", "sgt_crm002_sale_funnel_id", "sgt_crm002_funnel_id",
                 "x_url_zalo_group", "x_mm_approved_at", "x_mm_approved_by", ev.FIELD_EVIDENCE)
DETAIL_BATCH = 50
HISTORIC_WON_STAGE_ID = 4        # the old "Won" label is accepted only for the stage that really is crm.stage 4

MAX_NOTES = 5000
MAX_LEADS = 10000
MAX_TRACK_ROWS = 50000
NOTE_BATCH = 200
LEAD_BATCH = 100
TRACK_PAGE = 300
CACHE_SECONDS = 60


class KpiError(ValueError):
    """The number cannot be verified; the message is shown to the user."""


# ---- small helpers -----------------------------------------------------------------------------------------------
def rel_id(value: Any) -> int | None:
    if isinstance(value, (list, tuple)) and value:
        value = value[0]
    return value if type(value) is int and value > 0 else None


def rel_name(value: Any) -> str:
    return str(value[1]) if isinstance(value, (list, tuple)) and len(value) > 1 and value[1] else ""


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise KpiError("Bản ghi lịch sử thiếu ngày giờ.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KpiError("Ngày giờ lịch sử Odoo không hợp lệ.") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local_text(value: Any) -> str:
    try:
        return parse_utc(value).astimezone(HCM).strftime("%Y-%m-%d %H:%M")
    except KpiError:
        return ""


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _odoo_error(exc: Exception, what: str) -> KpiError:
    return KpiError(f"{what}: {exc}")


def _call(gateway, session, model, method, args, kwargs=None, what="Odoo"):
    from ..heatmap.adapter import OdooError
    try:
        return gateway.call(session, model, method, args, kwargs or {})
    except OdooError as exc:
        raise KpiError(f"{what}: {exc}") from exc


def _lead_url(lead_id: int) -> str:
    return f"/odoo/crm/{lead_id}"


# ---- tiny per-user cache (the heavy history scans) ------------------------------------------------------------------
_CACHE: dict[tuple, tuple[float, Any]] = {}
_LOCK = threading.Lock()


def cached(key: tuple, force: bool, build):
    now = time.monotonic()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and not force and now - hit[0] < CACHE_SECONDS:
            return hit[1], True
    value = build()
    with _LOCK:
        if len(_CACHE) > 500:
            _CACHE.clear()
        _CACHE[key] = (time.monotonic(), value)
    return value, False


def forget_all():
    with _LOCK:
        _CACHE.clear()


# ---- Data · KH tiềm năng ----------------------------------------------------------------------------------------------
_TAG = re.compile(r"<[^>]+>")
_BREAK = re.compile(r"(?i)</(?:li|p|div)>|<br\s*/?>")


def parse_handoff(body: Any) -> dict[str, str] | None:
    """One CRM-002 hand-over log note -> from/to funnel and column; None when it is not a complete hand-over note."""
    if not isinstance(body, str) or HANDOFF_MARK not in _html.unescape(_TAG.sub("", body)):
        return None
    info: dict[str, str] = {}
    text = _html.unescape(_TAG.sub("", _BREAK.sub("\n", body)))
    for line in (ln.strip() for ln in text.splitlines()):
        for key, name in (("Từ:", "from"), ("Sang:", "to"), ("Thực hiện bởi:", "by")):
            if line.startswith(key):
                info[name] = line[len(key):].strip()
    if not info.get("from") or not info.get("to"):
        return None

    def split(value: str) -> tuple[str, str]:
        head, _, tail = value.partition(ARROW)
        return head.strip(), tail.strip()

    from_funnel, from_column = split(info["from"])
    to_funnel, to_column = split(info["to"])
    return {"from_funnel": from_funnel, "from_column": from_column, "to_funnel": to_funnel,
            "to_column": to_column, "by": info.get("by", "").split(" · ")[0].strip()}


def _handoff_base() -> list:
    return [("model", "=", LEAD), ("message_type", "=", "comment"), ("body", "ilike", HANDOFF_MARK)]


def _read_notes(gateway, session, domain) -> list[dict]:
    count = _call(gateway, session, MESSAGE, "search_count", [domain], what="Không đếm được log note bàn giao")
    if type(count) is not int or count < 0 or count > MAX_NOTES:
        raise KpiError("Quá nhiều log note bàn giao trong phạm vi. Hãy chọn kỳ ngắn hơn.")
    rows: list[dict] = []
    last = 0
    while len(rows) < count:
        block = _call(gateway, session, MESSAGE, "search_read", [domain + [("id", ">", last)]],
                      {"fields": ["id", "res_id", "date", "author_id", "body"], "order": "id asc", "limit": NOTE_BATCH},
                      what="Không đọc được log note bàn giao")
        if not isinstance(block, list) or not block or len(block) > NOTE_BATCH:
            raise KpiError("Log note bàn giao chưa được truy xuất đầy đủ.")
        for row in block:
            mid = rel_id(row.get("id"))
            if mid is None or mid <= last:
                raise KpiError("Thứ tự log note bàn giao không hợp lệ.")
            last = mid
            rows.append(row)
    return rows


def _funnel_names(history, session, field: str) -> set[str]:
    """Names of the funnels that really hold Deals in ``field`` (names only: no Deal, no count is shown)."""
    rows = _call(history, session, LEAD, "read_group", [[(field, "!=", False)], [field], [field]],
                 {"lazy": False, "limit": 500, "orderby": field}, what="Không đọc được tên phễu")
    if not isinstance(rows, list):
        raise KpiError("Odoo read_group trả dữ liệu không hợp lệ.")
    return {rel_name(r.get(field)) for r in rows if rel_name(r.get(field))}


def _has_field(gateway, session, name: str, kind: str) -> bool:
    try:
        meta = gateway.fields_get(session, LEAD, [name])
    except Exception:  # noqa: BLE001
        return False
    return (meta or {}).get(name, {}).get("type") == kind


def handed_to_opportunity(gateway, history, session, period: Period) -> dict[str, Any]:
    """Deals FIRST handed over to Match Making › 1.Opportunity inside ``period`` (all time when it is All Time)."""
    have = _call(gateway, session, MESSAGE, "search_count", [_handoff_base()], what="Không đọc được log note bàn giao")
    if type(have) is not int or have <= 0:
        return {"verified": False, "entries": {}, "reason":
                f'Odoo chưa có log note "{HANDOFF_MARK}" nên chưa xác minh được Deal bàn giao sang Match Making.'}
    window = list(_handoff_base())
    bounds = period.utc_bounds()
    if bounds:
        window += [("date", ">=", bounds[0]), ("date", "<", bounds[1])]
    excluded = _funnel_names(history, session, FUNNEL) if _has_field(gateway, session, FUNNEL, "many2one") else set()
    if _has_field(gateway, session, SALE_FUNNEL, "many2one"):
        excluded |= _funnel_names(history, session, SALE_FUNNEL)

    def matches(p: dict) -> bool:
        return p["to_column"] == OPPORTUNITY_LABEL and bool(p["to_funnel"]) and p["to_funnel"] not in excluded

    notes = []
    for row in _read_notes(gateway, session, window):
        parsed = parse_handoff(row.get("body"))
        lead_id = rel_id(row.get("res_id"))
        if parsed and lead_id and isinstance(row.get("date"), str) and matches(parsed):
            notes.append({"lead_id": lead_id, "raw": row["date"], "actor": rel_name(row.get("author_id")) or parsed["by"],
                          "parsed": parsed})
    notes.sort(key=lambda n: (n["raw"], n["lead_id"]))
    entries: dict[int, dict[str, str]] = {}
    for n in notes:
        entries.setdefault(n["lead_id"], {"at": local_text(n["raw"]), "actor": n["actor"],
                                          "from_funnel": n["parsed"]["from_funnel"], "from_column": n["parsed"]["from_column"]})
    ids = sorted(entries)
    if bounds and ids:      # a Deal counts only in the period of its FIRST hand-over
        already: set[int] = set()
        for block in _chunks(ids, NOTE_BATCH):
            for row in _read_notes(gateway, session, _handoff_base() + [("res_id", "in", block), ("date", "<", bounds[0])]):
                parsed = parse_handoff(row.get("body"))
                lead_id = rel_id(row.get("res_id"))
                if parsed and lead_id and matches(parsed):
                    already.add(lead_id)
        ids = [i for i in ids if i not in already]
    if ids:                 # the Deal still exists and this user may see it (record rules)
        kept = set()
        for block in _chunks(ids, 500):
            found = _call(gateway, session, LEAD, "search_read", [[("id", "in", block)]],
                          {"fields": ["id"], "limit": len(block) + 1}, what="Không đọc được Deal")
            kept |= {rel_id(r.get("id")) for r in found}
        ids = [i for i in ids if i in kept]
    return {"verified": True, "entries": {i: entries[i] for i in ids}, "reason": None}


def prospects(gateway, history, session, period: Period, page: int = 1, page_size: int = 25, force: bool = False) -> dict[str, Any]:
    if not (1 <= page <= 100000 and 1 <= page_size <= 100):
        raise KpiError("Phân trang không hợp lệ.")
    token = session.token

    def one(p: Period):
        value, _ = cached((token, "prospects", p.kind, str(p.start), str(p.end)), force,
                          lambda: handed_to_opportunity(gateway, history, session, p))
        return value

    now = one(period)
    base = {"kpi": "data", "source": "xinyang", "available": now["verified"], "reason": now["reason"],
            "target": f"Match Making › {OPPORTUNITY_LABEL}",
            "basis": f'Log note "{HANDOFF_MARK}" (Sang: Match Making › {OPPORTUNITY_LABEL}) · mail.message.date, bàn giao đầu tiên của Deal',
            **period.as_dict()}
    if not now["verified"]:
        return {**base, "total": None, "previous": None, "delta": delta(0, None), "rows": [], "page": 1, "page_count": 0}
    entries = now["entries"]
    total = len(entries)
    prev_period = period.previous()
    previous = None
    if prev_period is not None:
        before = one(prev_period)
        previous = len(before["entries"]) if before["verified"] else None
    ordered = sorted(entries, key=lambda i: (entries[i]["at"], i), reverse=True)
    page_count = (total + page_size - 1) // page_size
    rows: list[dict] = []
    if page <= page_count:
        ids = ordered[(page - 1) * page_size:page * page_size]
        leads = _call(gateway, session, LEAD, "search_read", [[("id", "in", ids)]],
                      {"fields": ["id", "name", "user_id", "create_date", "stage_id"], "limit": len(ids)}, what="Không đọc được Deal")
        by_id = {rel_id(r.get("id")): r for r in leads}
        for lid in ids:
            lead = by_id.get(lid)
            if lead is None:
                continue
            hand = entries[lid]
            rows.append({"lead_id": lid, "name": str(lead.get("name") or "(Chưa đặt tên)"),
                         "from": ARROW.join(x for x in (hand.get("from_funnel"), hand.get("from_column")) if x) or "Chưa xác định",
                         "handed_by": hand.get("actor") or "Chưa xác định", "handed_at": hand.get("at") or "",
                         "salesperson": rel_name(lead.get("user_id")) or "—", "created_at": local_text(lead.get("create_date")),
                         "stage": rel_name(lead.get("stage_id")) or "—", "odoo_url": _lead_url(lid)})
    extra = new_data_leads(gateway, session, period, previous_period=prev_period)
    return {**base, "total": total, "previous": previous, "delta": delta(total, previous),
            "page": page, "page_size": page_size, "page_count": page_count, "rows": rows, "new_leads": extra}


def new_data_leads(gateway, session, period: Period, previous_period: Period | None = None) -> dict[str, Any]:
    """Secondary figure: Deals added to the small Data funnels (CRM-002) in the period. Never stops the main KPI."""
    if not (_has_field(gateway, session, FUNNEL, "many2one") and _has_field(gateway, session, STEP, "selection")):
        return {"available": False, "reason": f"Odoo chưa có field phễu CRM-002 ({FUNNEL}, {STEP}).", "total": None}
    try:
        domain: list = [(FUNNEL, "!=", False)]
        bounds = period.utc_bounds()
        if bounds:
            domain += [("create_date", ">=", bounds[0]), ("create_date", "<", bounds[1])]
        total = _call(gateway, session, LEAD, "search_count", [domain], what="Không đếm được Lead mới")
        prev = None
        if previous_period is not None:
            pb = previous_period.utc_bounds()
            prev = _call(gateway, session, LEAD, "search_count",
                         [[(FUNNEL, "!=", False), ("create_date", ">=", pb[0]), ("create_date", "<", pb[1])]], what="Không đếm được Lead mới")
        return {"available": True, "reason": None, "total": total, "previous": prev, "delta": delta(total, prev),
                "basis": f"crm.lead.create_date + {FUNNEL}"}
    except KpiError as exc:
        return {"available": False, "reason": str(exc), "total": None}


# ---- Match Making / Approved Match Making -----------------------------------------------------------------------------
def _resolve_stage(gateway, session, kind: str) -> tuple[int, str, tuple[str, ...]]:
    cfg = STAGES[kind]
    rows = _call(gateway, session, STAGE, "search_read", [[("name", "in", list(cfg["names"]))]],
                 {"fields": ["id", "name"], "limit": 5}, what=f"Không đọc được Stage {cfg['label']}")
    if len(rows) != 1 or rows[0].get("name") not in cfg["names"] or not rel_id(rows[0].get("id")):
        raise KpiError("Không xác minh được một Stage duy nhất có tên chính xác " + " hoặc ".join(cfg["names"]) + ".")
    stage_id = rel_id(rows[0]["id"])
    aliases = tuple(cfg["aliases"]) + (("Won",) if kind == "approved" and stage_id == HISTORIC_WON_STAGE_ID else ())
    return stage_id, rows[0]["name"], aliases


def _stage_field_id(history, session) -> int:
    rows = _call(history, session, FIELD, "search_read", [[("model", "=", LEAD), ("name", "=", "stage_id")]],
                 {"fields": ["id"], "limit": 3}, what="Không đọc được ir.model.fields (cần để đọc lịch sử Stage)")
    if len(rows) != 1 or not rel_id(rows[0].get("id")):
        raise KpiError("Không xác minh được field crm.lead.stage_id trong ir.model.fields.")
    return rel_id(rows[0]["id"])


def _current_leads(gateway, session, stage_id: int) -> list[dict]:
    domain = [("stage_id", "=", stage_id)]
    total = _call(gateway, session, LEAD, "search_count", [domain], what="Không đếm được Deal trong Stage")
    if type(total) is not int or total < 0 or total > MAX_LEADS:
        raise KpiError("Số Deal trong Stage vượt giới hạn an toàn hoặc không hợp lệ.")
    rows: list[dict] = []
    last = 0
    while len(rows) < total:
        batch = _call(gateway, session, LEAD, "search_read", [domain + [("id", ">", last)]],
                      {"fields": ["id", "name", "phone", "user_id", "stage_id"], "order": "id asc", "limit": LEAD_BATCH},
                      what="Không đọc được Deal trong Stage")
        if not isinstance(batch, list) or not batch or len(batch) > LEAD_BATCH:
            raise KpiError("Odoo trả thiếu Deal trong Stage khi phân trang.")
        for row in batch:
            ident = rel_id(row.get("id"))
            if ident is None or ident <= last or rel_id(row.get("stage_id")) != stage_id:
                raise KpiError("Danh sách Deal có ID/Stage không đồng nhất.")
            last = ident
            rows.append(row)
    if _call(gateway, session, LEAD, "search_count", [domain], what="Không đếm được Deal trong Stage") != total:
        raise KpiError("Danh sách Deal thay đổi khi đọc; vui lòng làm mới.")
    return rows


def _first_entries(history, session, lead_ids: list[int], field_id: int, aliases: tuple[str, ...]) -> dict[int, datetime]:
    """Earliest Chatter ``stage_id`` tracking from ANOTHER stage into the stage, per Deal (direct indexed reads, fully paged)."""
    found: dict[int, datetime] = {}
    total_messages = total_tracks = 0
    for lead_batch in _chunks(lead_ids, LEAD_BATCH):
        lead_set = set(lead_batch)
        last_message = 0
        while True:
            messages = _call(history, session, MESSAGE, "search_read",
                             [[("model", "=", LEAD), ("res_id", "in", lead_batch), ("tracking_value_ids", "!=", False),
                               ("id", ">", last_message)]],
                             {"fields": ["id", "model", "res_id", "date"], "order": "id asc", "limit": TRACK_PAGE},
                             what="Không đọc được Chatter của Deal")
            if not isinstance(messages, list) or len(messages) > TRACK_PAGE:
                raise KpiError("Chatter trả về trang dữ liệu không hợp lệ.")
            total_messages += len(messages)
            if total_messages > MAX_TRACK_ROWS:
                raise KpiError("Chatter vượt giới hạn an toàn; không hiển thị số liệu cắt cụt.")
            by_message: dict[int, tuple[int, Any]] = {}
            for msg in messages:
                mid, lid = rel_id(msg.get("id")), rel_id(msg.get("res_id"))
                if mid is None or mid <= last_message or lid not in lead_set or msg.get("model") != LEAD or mid in by_message:
                    raise KpiError("Chatter không thuộc Deal đang kiểm tra.")
                last_message = mid
                by_message[mid] = (lid, msg.get("date"))
            message_ids = list(by_message)
            last_track = 0
            while message_ids:
                tracks = _call(history, session, TRACK, "search_read",
                               [[("mail_message_id", "in", message_ids), ("field_id", "=", field_id),
                                 ("new_value_char", "in", list(aliases)), ("id", ">", last_track)]],
                               {"fields": ["id", "field_id", "old_value_char", "new_value_char", "mail_message_id"],
                                "order": "id asc", "limit": TRACK_PAGE}, what="Không đọc được Tracking Stage")
                if not isinstance(tracks, list) or len(tracks) > TRACK_PAGE:
                    raise KpiError("Tracking Stage trả trang không hợp lệ.")
                total_tracks += len(tracks)
                if total_tracks > MAX_TRACK_ROWS:
                    raise KpiError("Tracking Stage vượt giới hạn; không đếm thiếu.")
                for track in tracks:
                    tid, mid = rel_id(track.get("id")), rel_id(track.get("mail_message_id"))
                    new = str(track.get("new_value_char") or "").strip()
                    if tid is None or tid <= last_track or mid not in by_message or rel_id(track.get("field_id")) != field_id or new not in aliases:
                        raise KpiError("Tracking Stage không khớp Chatter nguồn.")
                    last_track = tid
                    old = str(track.get("old_value_char") or "").strip()
                    if not old or old in aliases:       # created directly in the stage, or only renamed
                        continue
                    lid, stamp = by_message[mid]
                    when = parse_utc(stamp)
                    if lid not in found or when < found[lid]:
                        found[lid] = when
                if len(tracks) < TRACK_PAGE:
                    break
            if len(messages) < TRACK_PAGE:
                break
    return found


def stage_history(gateway, history, session, kind: str) -> dict[str, Any]:
    """Whole-history scan for the Deals currently in the stage (period independent, so it is cached per user)."""
    stage_id, stage_name, aliases = _resolve_stage(gateway, session, kind)
    field_id = _stage_field_id(history, session)
    leads = _current_leads(gateway, session, stage_id)
    first = _first_entries(history, session, [r["id"] for r in leads], field_id, aliases)
    if leads and not first:
        raise KpiError(f"Có Deal đang ở {stage_name} nhưng không tìm thấy Tracking Stage nào chuyển vào. "
                       "Cần xác minh tên Stage trong Chatter và quyền đọc mail.tracking.value.")
    events = sorted(({"lead_id": lid, "dt": dt} for lid, dt in first.items()), key=lambda e: (e["dt"], e["lead_id"]), reverse=True)
    return {"stage_id": stage_id, "stage_name": stage_name, "events": events, "details": {r["id"]: r for r in leads},
            "unverified": len(leads) - len(first)}


# ---- Deal details for the Match Making page (Update_019) -------------------------------------------------------------
class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in ("br", "p", "div", "li"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1


def plain_text(value: Any, limit: int = 280) -> str:
    """HTML (the CRM description) -> short plain text; the page only ever shows it as text."""
    if not isinstance(value, str) or not value.strip():
        return ""
    parser = _Text()
    try:
        parser.feed(value[:60000])
    except Exception:  # noqa: BLE001 - malformed HTML must not break the list
        return ""
    text = " ".join("".join(parser.parts).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def safe_zalo(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    v = value.strip()
    if not v or len(v) > 1800 or any(c.isspace() for c in v):
        return ""
    u = urlsplit(v)
    host = (u.hostname or "").lower()
    ok = u.scheme == "https" and (host == "zalo.me" or host.endswith(".zalo.me")) and u.username is None and u.password is None
    return v if ok else ""


def safe_web(value: Any) -> str:
    """Website of the company as a link only when it is a plain http(s) address."""
    if not isinstance(value, str):
        return ""
    v = value.strip()
    if not v or len(v) > 300 or any(c.isspace() for c in v):
        return ""
    if "://" not in v:
        v = "https://" + v
    u = urlsplit(v)
    ok = u.scheme in ("http", "https") and bool(u.hostname) and "." in u.hostname and u.username is None and u.password is None
    return v if ok else ""


def _address(lead: dict) -> str:
    return ", ".join(x for x in (str(lead.get("street") or "").strip(), str(lead.get("city") or "").strip(),
                                 rel_name(lead.get("state_id")), rel_name(lead.get("country_id"))) if x)


def deal_details(gateway, session, ids: list[int], base_host: str | None = None) -> dict[int, dict]:
    """CRM information + Evidence image list of the Deals on the page, read with the user's own rights."""
    if not ids:
        return {}
    try:
        present = set(gateway.fields_get(session, LEAD, list(DETAIL_FIELDS)))
    except Exception as exc:  # noqa: BLE001
        raise _odoo_error(exc, "Không đọc được danh sách trường CRM") from exc
    fields = [f for f in DETAIL_FIELDS if f in present]
    data: dict[int, dict] = {}
    for block in _chunks(ids, DETAIL_BATCH):
        rows = _call(gateway, session, LEAD, "read", [block], {"fields": ["id", *fields]}, what="Không đọc được thông tin Deal")
        if not isinstance(rows, list):
            raise KpiError("Odoo trả thông tin Deal không hợp lệ.")
        for row in rows:
            ident = rel_id(row.get("id"))
            if ident in block:
                data[ident] = row
    tag_ids = sorted({t for r in data.values() for t in (r.get("tag_ids") or []) if isinstance(t, int)})
    tag_names: dict[int, str] = {}
    if tag_ids and "tag_ids" in present:
        try:
            for t in gateway.call(session, "crm.tag", "read", [tag_ids], {"fields": ["id", "name"]}):
                tag_names[t["id"]] = str(t.get("name") or "").strip()
        except Exception:  # noqa: BLE001 - tags are optional decoration
            tag_names = {}
    out: dict[int, dict] = {}
    for ident, r in data.items():
        usable, found, note = ev.summarize(r.get(ev.FIELD_EVIDENCE), base_host) if ev.FIELD_EVIDENCE in present else ([], 0, "Không tìm thấy trường Evidence trong Odoo; chưa thể xác minh ảnh.")
        funnel = rel_name(r.get("sgt_crm002_sale_funnel_id")) or rel_name(r.get("sgt_crm002_funnel_id"))
        out[ident] = {
            "company": str(r.get("partner_name") or "").strip(), "contact": str(r.get("contact_name") or "").strip(),
            "function": str(r.get("function") or "").strip(), "email": str(r.get("email_from") or "").strip(),
            "website": safe_web(r.get("website")), "address": _address(r), "source": rel_name(r.get("source_id")),
            "tags": [tag_names[t] for t in (r.get("tag_ids") or []) if tag_names.get(t)], "funnel": funnel,
            "note": plain_text(r.get("description")), "zalo_url": safe_zalo(r.get("x_url_zalo_group")),
            "created": local_text(r.get("create_date")) if r.get("create_date") else "",
            "approved_at": local_text(r.get("x_mm_approved_at")) if r.get("x_mm_approved_at") else "",
            "approved_by": rel_name(r.get("x_mm_approved_by")),
            "evidence_found": found, "evidence_note": note,
            "evidence": [{"thumb": f"/sgt_home/kpi/evidence?lead={ident}&i={i}&size=thumb",
                          "large": f"/sgt_home/kpi/evidence?lead={ident}&i={i}&size=large"} for i in usable],
        }
    return out


def mm_all_report(gateway, history, session, period: Period, page: int = 1, page_size: int = 25, force: bool = False,
                  column: str = "all", detail: bool = False, base_host: str | None = None) -> dict[str, Any]:
    """Match Making page (Update_019b): column 5 (Match Making) and column 6 (Approved Match Making) in ONE list.

    Each column keeps the Dashboard's own cohort rule (Deals currently in the stage, dated by their first tracked entry into it);
    a Deal sits in one stage only, so the two cohorts never overlap and the combined total is simply their sum.
    """
    if column not in ("all", "mm", "approved") or not (1 <= page <= 100000 and 1 <= page_size <= 100):
        raise KpiError("Tham số không hợp lệ.")
    hists = {k: cached((session.token, "stage", k), force, lambda k=k: stage_history(gateway, history, session, k))[0]
             for k in ("mm", "approved")}

    def pick(p: Period, k: str) -> list[dict]:
        b = p.utc_bounds()
        if not b:
            return hists[k]["events"]
        lo, hi = parse_utc(b[0]), parse_utc(b[1])
        return [e for e in hists[k]["events"] if lo <= e["dt"] < hi]

    cur = {k: pick(period, k) for k in hists}
    prev_period = period.previous()
    prev = {k: (len(pick(prev_period, k)) if prev_period is not None else None) for k in hists}
    previous = None if prev_period is None else prev["mm"] + prev["approved"]
    wanted = ("mm", "approved") if column == "all" else (column,)
    merged = sorted(({**e, "column": k} for k in wanted for e in cur[k]), key=lambda e: (e["dt"], e["lead_id"]), reverse=True)
    total_all = len(cur["mm"]) + len(cur["approved"])
    chosen = merged[(page - 1) * page_size:page * page_size]
    more = deal_details(gateway, session, [e["lead_id"] for e in chosen], base_host) if detail else {}
    rows = []
    for e in chosen:
        lead = hists[e["column"]]["details"][e["lead_id"]]
        row = {"lead_id": e["lead_id"], "column": e["column"], "at": e["dt"].astimezone(HCM).strftime("%Y-%m-%d %H:%M"),
               "name": str(lead.get("name") or "").strip(), "phone": str(lead.get("phone") or "").strip(),
               "salesperson": rel_name(lead.get("user_id")) or "—", "stage": rel_name(lead.get("stage_id")),
               "odoo_url": _lead_url(e["lead_id"])}
        if detail:
            row.update(more.get(e["lead_id"], {"evidence": [], "evidence_found": 0, "evidence_note": "Không đọc được thông tin bổ sung của Deal này."}))
        rows.append(row)
    n = len(merged)
    return {"kpi": "mm_all", "source": "xinyang", "available": True, "reason": None, "column": column,
            "stages": {"mm": hists["mm"]["stage_name"], "approved": hists["approved"]["stage_name"]},
            "basis": "Chatter Tracking stage_id (mail.message.date) · lần vào Stage đầu tiên của Deal đang ở cột 5 hoặc cột 6",
            "total": total_all, "mm_total": len(cur["mm"]), "approved_total": len(cur["approved"]),
            "previous": previous, "delta": delta(total_all, previous),
            "current_stage_deals": len(hists["mm"]["details"]) + len(hists["approved"]["details"]),
            "unverified_count": hists["mm"]["unverified"] + hists["approved"]["unverified"],
            "shown": n, "page": page, "page_size": page_size, "page_count": (n + page_size - 1) // page_size, "rows": rows,
            **period.as_dict()}


def stage_report(gateway, history, session, kind: str, period: Period, page: int = 1, page_size: int = 25, force: bool = False,
                 detail: bool = False, base_host: str | None = None) -> dict[str, Any]:
    if kind not in STAGES or not (1 <= page <= 100000 and 1 <= page_size <= 100):
        raise KpiError("Tham số không hợp lệ.")
    hist, was_cached = cached((session.token, "stage", kind), force, lambda: stage_history(gateway, history, session, kind))

    def pick(p: Period) -> list[dict]:
        b = p.utc_bounds()
        if not b:
            return hist["events"]
        lo, hi = parse_utc(b[0]), parse_utc(b[1])
        return [e for e in hist["events"] if lo <= e["dt"] < hi]

    events = pick(period)
    prev_period = period.previous()
    previous = len(pick(prev_period)) if prev_period is not None else None
    total = len(events)
    chosen = events[(page - 1) * page_size:page * page_size]
    more = deal_details(gateway, session, [e["lead_id"] for e in chosen], base_host) if detail else {}
    rows = []
    for e in chosen:
        lead = hist["details"][e["lead_id"]]
        row = {"lead_id": e["lead_id"], "at": e["dt"].astimezone(HCM).strftime("%Y-%m-%d %H:%M"),
               "name": str(lead.get("name") or "").strip(), "phone": str(lead.get("phone") or "").strip(),
               "salesperson": rel_name(lead.get("user_id")) or "—", "stage": rel_name(lead.get("stage_id")),
               "odoo_url": _lead_url(e["lead_id"])}
        if detail:
            row.update(more.get(e["lead_id"], {"evidence": [], "evidence_found": 0, "evidence_note": "Không đọc được thông tin bổ sung của Deal này."}))
        rows.append(row)
    return {"kpi": "mm" if kind == "mm" else "approved_mm", "source": "xinyang", "available": True, "reason": None,
            "target_stage": hist["stage_name"], "target_stage_id": hist["stage_id"],
            "basis": "Chatter Tracking stage_id (mail.message.date) · lần vào Stage đầu tiên của Deal đang ở Stage",
            "total": total, "previous": previous, "delta": delta(total, previous),
            "current_stage_deals": len(hist["details"]), "unverified_count": hist["unverified"],
            "page": page, "page_size": page_size, "page_count": (total + page_size - 1) // page_size, "rows": rows,
            "cached": was_cached, **period.as_dict()}
