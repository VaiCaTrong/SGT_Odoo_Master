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
