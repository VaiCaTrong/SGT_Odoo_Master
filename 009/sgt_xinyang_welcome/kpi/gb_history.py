"""Read-only SGT GB Submit Publishing History aggregation for Project XINYANG (copied from the Management Dashboard, unchanged rules).

Adapted from ARGO's GB Logs read_group strategy, WITHOUT changing Xinyang
CRM, sending credentials to browsers, or writing to SGT Summary wizards.
Unknown statuses/details, incomplete grouping, ambiguous models/projects and
access failures all fail closed; never present unverifiable counts as KPI.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

LOG_MODEL_LABEL = "GB Submit Publishing History"
MAX_GROUPS = 1200


def _utc_bounds(start: date, end: date) -> tuple[str, str]:
    """Return [start HCMC midnight, next-day midnight) in UTC for Odoo Datetime."""
    local = ZoneInfo("Asia/Ho_Chi_Minh")
    left = datetime.combine(start, time.min, tzinfo=local).astimezone(timezone.utc)
    right = datetime.combine(end + timedelta(days=1), time.min, tzinfo=local).astimezone(timezone.utc)
    fmt = "%Y-%m-%d %H:%M:%S"
    return left.strftime(fmt), right.strftime(fmt)


def _selection_code(meta: dict[str, Any], label: str) -> str | None:
    choices = meta.get("selection")
    if not isinstance(choices, (list, tuple)):
        return None
    matched = set()
    for choice in choices:
        if not isinstance(choice, (list, tuple)) or len(choice) != 2:
            return None
        code, name = choice
        if not isinstance(code, str) or not isinstance(name, str):
            return None
        if code.strip().casefold() == label.casefold() or name.strip().casefold() == label.casefold():
            matched.add(code)
    return next(iter(matched)) if len(matched) == 1 else None


def _group_count(row: dict[str, Any]) -> int:
    from .sgt import GbError
    number = row.get("__count", row.get("id_count"))
    if type(number) is not int or number < 0:
        raise GbError("GB Logs trả về số bản ghi không hợp lệ; không công bố KPI.")
    return number


def _classified_counts(groups: list[dict[str, Any]], published: str, failed: str) -> tuple[int, int, int, int]:
    """Partition complete native Odoo read_group rows (not guessed from labels)."""
    from .sgt import GbError
    total = approved = rejected = unchecked = 0
    for group in groups:
        if not isinstance(group, dict) or "status" not in group or "detail" not in group:
            raise GbError("GB Logs thiếu thông tin Status/Detail trong một nhóm.")
        n = _group_count(group)
        total += n
        status, detail = group["status"], group["detail"]
        if status == failed:
            rejected += n
        elif status == published and isinstance(detail, str) and detail.strip().casefold() == "ok":
            approved += n
        elif status == published and detail in (False, None, ""):
            unchecked += n
        elif n:
            raise GbError("GB Logs có trạng thái/Detail chưa có quy tắc KPI xác minh. Cần đối chiếu Summary trước khi hiển thị.")
    if total != approved + rejected + unchecked:
        raise GbError("Các trạng thái GB Logs không tạo thành bộ KPI đầy đủ.")
    return total, approved, rejected, unchecked


def _targeted_counts(service, domain: list, published: str, failed: str) -> tuple[int, int, int, int]:
    """Scalable read-only fallback for large group cardinality / All Time."""
    from .sgt import GbError, _integer
    def count(extra: list) -> int:
        return _integer(service._call(service._log_model, "search_count", [domain + extra]), "search_count")
    total = count([])
    approved = count([["status", "=", published], ["detail", "=ilike", "OK"]])
    rejected = count([["status", "=", failed]])
    unchecked = count([["status", "=", published], "|", ["detail", "=", False], ["detail", "=", ""]])
    if approved + rejected + unchecked != total:
        raise GbError("Không thể phân loại đủ GB Logs thành Approved / Failed / Uncheck; không hiển thị số liệu có nguy cơ sai lệch.")
    return total, approved, rejected, unchecked


def fetch_history(service, period: str, start: date | None, end: date | None) -> dict[str, Any]:
    """Read SGT Odoo Logs by exact project and posted date; never write data."""
    from .sgt import GbError
    if (start is None) != (end is None) or (start and end and end < start):
        raise GbError("Khoảng ngày GB Logs không hợp lệ.")

    # Project resolution is shared with Update 001 (strict exact single match).
    project_id = service._project()
    model = service._discover_history_model()
    metadata = service._call(model, "fields_get", [],
                             {"attributes": ["type", "relation", "selection", "store"]})
    if not isinstance(metadata, dict):
        raise GbError("Không đọc được metadata GB Publishing History từ SGT.")
    expected = {"posted_at": "datetime", "project_id": "many2one", "status": "selection", "detail": "char"}
    for field, typ in expected.items():
        desc = metadata.get(field)
        if not isinstance(desc, dict) or desc.get("type") != typ or desc.get("store") is False:
            raise GbError(f"GB Publishing History thiếu field lưu trữ {field} ({typ}).")
    if metadata["project_id"].get("relation") != "sgt.social.destination":
        raise GbError("Relation project_id GB Logs không đúng sgt.social.destination.")
    published = _selection_code(metadata["status"], "Published")
    failed = _selection_code(metadata["status"], "Failed")
    if not published or not failed or published == failed:
        raise GbError("Chưa xác định duy nhất giá trị kỹ thuật Published và Failed của GB Logs; cần xác minh Selection Options.")

    domain: list = [["project_id", "=", project_id]]
    if start and end:
        left, right = _utc_bounds(start, end)
        domain += [["posted_at", ">=", left], ["posted_at", "<", right]]

    # ARGO strategy: native read_group on Status + Detail with Posted At date
    # domain. Never fetch individual posts or leak URLs/user information.
    # For All Time, use indexed search_count to avoid enormous group results.
    service._log_model = model
    if start is None:
        counts = _targeted_counts(service, domain, published, failed)
        aggregation = "search_count · All Time"
    else:
        groups = service._call(model, "read_group", [domain, ["id:count"], ["status", "detail"]],
                               {"lazy": False, "limit": MAX_GROUPS + 1,
                                "context": {"tz": "Asia/Ho_Chi_Minh"}})
        if not isinstance(groups, list):
            raise GbError("SGT không trả về các nhóm GB Logs hợp lệ.")
        if len(groups) > MAX_GROUPS:
            counts = _targeted_counts(service, domain, published, failed)
            aggregation = "search_count · high cardinality"
        else:
            counts = _classified_counts(groups, published, failed)
            # An extra independent count detects silently missing/truncated groups.
            from .sgt import _integer
            independent = _integer(service._call(model, "search_count", [domain]), "total_count")
            if counts[0] != independent:
                counts = _targeted_counts(service, domain, published, failed)
                aggregation = "search_count · verified fallback"
            else:
                aggregation = "read_group · status/detail"

    total, approved, rejected, unchecked = counts
    return {
        "total_published": total, "approved_links": approved,
        "not_approved_links": rejected, "uncheck": unchecked,
        "data_source": "SGT GB Publishing History (read-only)",
        "aggregation": aggregation,
    }


# ---- Update_021: raw daily counts, so a saved version can answer ANY period without social360 --------------------------
RAW_PAGE = 5000
RAW_MAX_ROWS = 300000
HCM = ZoneInfo("Asia/Ho_Chi_Minh")


def load_daily(service) -> dict[str, Any]:
    """Read every GB Publishing History row of Project XINYANG (3 fields only) and tally it per Asia/Ho_Chi_Minh day.

    Same classification rules and the same fail-closed checks as ``fetch_history`` (Approved = Published + Detail "OK",
    Failed = Failed, Unchecked = Published + empty Detail; anything else stops with an error). The result is tiny
    (days x 4 numbers): {"daily": {"2026-11-17": [total, approved, rejected, unchecked]}, "undated": [...], "rows": n}.
    """
    from .sgt import GbError, _integer
    project_id = service._project()
    model = service._discover_history_model()
    metadata = service._call(model, "fields_get", [], {"attributes": ["type", "relation", "selection", "store"]})
    if not isinstance(metadata, dict):
        raise GbError("Không đọc được metadata GB Publishing History từ SGT.")
    for field, typ in {"posted_at": "datetime", "project_id": "many2one", "status": "selection", "detail": "char"}.items():
        desc = metadata.get(field)
        if not isinstance(desc, dict) or desc.get("type") != typ or desc.get("store") is False:
            raise GbError(f"GB Publishing History thiếu field lưu trữ {field} ({typ}).")
    published = _selection_code(metadata["status"], "Published")
    failed = _selection_code(metadata["status"], "Failed")
    if not published or not failed or published == failed:
        raise GbError("Chưa xác định duy nhất giá trị kỹ thuật Published và Failed của GB Logs; cần xác minh Selection Options.")
    has_url = isinstance(metadata.get("external_post_url"), dict) and metadata["external_post_url"].get("store") is not False
    fields = ["id", "posted_at", "status", "detail"] + (["external_post_url"] if has_url else [])
    domain: list = [["project_id", "=", project_id]]
    expected = _integer(service._call(model, "search_count", [domain]), "search_count")
    if expected > RAW_MAX_ROWS:
        raise GbError(f"GB Logs có {expected} dòng, vượt giới hạn {RAW_MAX_ROWS} của bản lưu; cần xử lý riêng.")
    daily: dict[str, list[int]] = {}
    undated = [0, 0, 0, 0]
    keep: list[tuple[str, int, int, str]] = []      # (posted, id, slot, url) of the rows that have a post URL
    rows_read = 0
    last_id = 0
    while True:
        rows = service._call(model, "search_read", [domain + [["id", ">", last_id]]],
                             {"fields": fields, "order": "id asc", "limit": RAW_PAGE})
        if not isinstance(rows, list):
            raise GbError("SGT không trả về danh sách GB Logs hợp lệ.")
        if not rows:
            break
        for row in rows:
            rid = row.get("id")
            if type(rid) is not int or rid <= last_id:
                raise GbError("GB Logs trả về ID trùng hoặc không tăng dần; dừng để tránh đếm sai.")
            last_id = rid
            status, detail = row.get("status"), row.get("detail")
            if status == failed:
                slot = 2
            elif status == published and isinstance(detail, str) and detail.strip().casefold() == "ok":
                slot = 1
            elif status == published and detail in (False, None, ""):
                slot = 3
            else:
                raise GbError("GB Logs có trạng thái/Detail chưa có quy tắc KPI xác minh. Cần đối chiếu Summary trước khi lưu phiên bản.")
            posted = row.get("posted_at")
            local = ""
            if posted:
                try:
                    moment = datetime.fromisoformat(str(posted).replace("Z", "+00:00").replace(" ", "T"))
                except ValueError as exc:
                    raise GbError("GB Logs có Posted At không hợp lệ.") from exc
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=timezone.utc)
                local_dt = moment.astimezone(HCM)
                local = local_dt.strftime("%Y-%m-%dT%H:%M:%S")
                bucket = daily.setdefault(str(local_dt.date()), [0, 0, 0, 0])
            else:
                bucket = undated
            url = row.get("external_post_url")
            if isinstance(url, str) and url.strip():
                keep.append((local, rid, slot, url.strip()))
            bucket[0] += 1
            bucket[slot] += 1
            rows_read += 1
        if len(rows) < RAW_PAGE:
            break
    if rows_read != expected:
        raise GbError(f"GB Logs đọc được {rows_read} dòng nhưng SGT báo {expected}; không lưu phiên bản thiếu dữ liệu.")
    keep.sort(key=lambda k: (k[0], k[1]), reverse=True)          # posted_at desc, id desc (undated last)
    out: dict[str, Any] = {"daily": daily, "undated": undated, "rows": rows_read}
    if not has_url:
        out["links_error"] = "GB Publishing History không có field external_post_url; không lấy được link bài."
    elif len(keep) > LINKS_MAX:
        out["links_error"] = f"Có {len(keep)} link, vượt giới hạn {LINKS_MAX} của bản lưu; không lưu danh sách link."
    else:
        out["links"] = [[k[0], k[2], k[3]] for k in keep]
    return out


def values_from_daily(raw: dict[str, Any], start: date | None, end: date | None) -> dict[str, Any]:
    """Same shape as ``fetch_history`` from the saved daily tally. All Time (start is None) also counts undated rows."""
    total = approved = rejected = unchecked = 0
    parts = [] if start is not None else [raw.get("undated") or [0, 0, 0, 0]]
    for day, numbers in (raw.get("daily") or {}).items():
        if start is None or start <= date.fromisoformat(day) <= end:
            parts.append(numbers)
    for p in parts:
        total += p[0]; approved += p[1]; rejected += p[2]; unchecked += p[3]
    return {"total_published": total, "approved_links": approved, "not_approved_links": rejected, "uncheck": unchecked,
            "data_source": "SGT GB Publishing History (saved version)", "aggregation": "saved daily tally"}


# ---- Update_026: post URLs (the "POST URLS" box of the SGT Summary: Approved / Uncheck / Not Approved / All) -------------------
LINKS_MAX = 50000
LINK_SLOTS = {"approved": 1, "not_approved": 2, "uncheck": 3}


def links_from_saved(raw: dict[str, Any], start: date | None, end: date | None) -> list[list[Any]]:
    """[[slot, url], ...] of the saved version for the period (newest first). All Time (start is None) also gives undated rows."""
    out = []
    for posted, slot, url in raw.get("links") or []:
        if start is None or (posted and start <= date.fromisoformat(posted[:10]) <= end):
            out.append([slot, url])
    return out


def fetch_links(service, start: date | None, end: date | None) -> list[list[Any]]:
    """Live read of the same list (rows of Project XINYANG that have a post URL), classified like the Summary."""
    from .sgt import GbError, _integer
    project_id = service._project()
    model = service._discover_history_model()
    metadata = service._call(model, "fields_get", [], {"attributes": ["type", "relation", "selection", "store"]})
    if not isinstance(metadata, dict) or not isinstance(metadata.get("external_post_url"), dict):
        raise GbError("GB Publishing History không có field external_post_url; không lấy được link bài.")
    published = _selection_code(metadata["status"], "Published")
    failed = _selection_code(metadata["status"], "Failed")
    if not published or not failed or published == failed:
        raise GbError("Chưa xác định duy nhất giá trị kỹ thuật Published và Failed của GB Logs; cần xác minh Selection Options.")
    domain: list = [["project_id", "=", project_id], ["external_post_url", "!=", False]]
    if start is not None:
        left, right = _utc_bounds(start, end)
        domain += [["posted_at", ">=", left], ["posted_at", "<", right]]
    expected = _integer(service._call(model, "search_count", [domain]), "search_count")
    if expected > LINKS_MAX:
        raise GbError(f"Có {expected} link trong kỳ này, vượt giới hạn {LINKS_MAX}; hãy chọn kỳ ngắn hơn.")
    out: list[list[Any]] = []
    offset = seen = 0
    while offset < expected:
        rows = service._call(model, "search_read", [domain], {"fields": ["id", "status", "detail", "external_post_url"],
                             "order": "posted_at desc, id desc", "offset": offset, "limit": RAW_PAGE})
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            status, detail = row.get("status"), row.get("detail")
            if status == failed:
                slot = 2
            elif status == published and isinstance(detail, str) and detail.strip().casefold() == "ok":
                slot = 1
            elif status == published and detail in (False, None, ""):
                slot = 3
            else:
                slot = 0                    # Published with another Detail text: listed under All only
            url = row.get("external_post_url")
            if isinstance(url, str) and url.strip():
                out.append([slot, url.strip()])
        offset += len(rows)
        seen += len(rows)
    if seen != expected:
        raise GbError(f"Đọc được {seen} dòng link nhưng SGT báo {expected}; không hiển thị danh sách thiếu.")
    return out
