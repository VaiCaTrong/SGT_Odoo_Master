"""Saved versions of the social360 data (Update_021).

Why: if social360 is down the Dashboard still shows the last data that was saved on purpose ("Update Data" in Home > Settings).
GB and Content are NOT stored as finished numbers (those depend on the period picked with the filter); the raw material is
stored, so every Day / Week / Month / All Time still works:

* GB: the Publishing History of Project XINYANG tallied per day (days x 4 numbers, ``gb_history.load_daily``).
* Content: every answer social360 gave to the read-only calls the Content KPI makes (``RecordingClient``). Those calls do not
  depend on the period, so ``ReplayClient`` serves them back to the very same ``content.fetch_content`` code, which then
  computes any period exactly as it does live: no second copy of the Content rules.

Nothing here writes to social360, and a version holds no Xinyang CRM data (no Deals, contacts or images).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import logging

from . import gb_history, posts as posts_mod
from .sgt import GbError, SgtClient

_logger = logging.getLogger(__name__)

HCM = ZoneInfo("Asia/Ho_Chi_Minh")
FORMAT = 1
MAX_BYTES = 12 * 1024 * 1024


def _key(model: str, method: str, args: list, kwargs: dict | None) -> str:
    return json.dumps([model, method, args, kwargs or {}], sort_keys=True, default=str, separators=(",", ":"))


class RecordingClient(SgtClient):
    """A real connection that also remembers every answer of ``_call`` (reads only)."""

    def __init__(self, base: SgtClient):
        super().__init__(base.url, base.db, base.login, base._secret, base.verify_ssl, base._rpc_override)
        self.log: dict[str, Any] = {}

    def _call(self, model, method, args, kwargs=None):
        result = super()._call(model, method, args, kwargs)
        self.log[_key(model, method, args, kwargs)] = result
        return result


class ReplayClient(SgtClient):
    """Serves the recorded answers; it never opens a connection. A call that was not recorded is an error, never a guess."""

    def __init__(self, calls: dict[str, Any], label: str, version_id: int | str):
        super().__init__("snapshot://" + str(version_id), str(version_id), "saved", "saved")
        self._calls = calls
        self._label = label

    def configured(self) -> bool:
        return True

    def where(self) -> str:
        return f"phiên bản đã lưu ({self._label})"

    def _call(self, model, method, args, kwargs=None):
        key = _key(model, method, args, kwargs)
        if key not in self._calls:
            raise GbError("Phiên bản đã lưu thiếu một câu trả lời cần cho Content; hãy bấm Update Data để lưu phiên bản mới.")
        return self._calls[key]


def take(client: SgtClient) -> dict[str, Any]:
    """Read social360 now and return the payload of a new version. Raises GbError (message shown to the admin) on any problem."""
    from .content import fetch_content
    today = datetime.now(HCM).date().isoformat()
    rec = RecordingClient(client)
    gb = gb_history.load_daily(rec)
    content_all = fetch_content(rec, "all", today)      # records every call (same calls for every period)
    # The newest approved posts (text + first image) are read with the plain connection (their images must not enter the
    # recorded Content calls). A problem here never blocks the numbers: the reason is kept and shown on the Content page.
    try:
        posts = posts_mod.load_latest(client)
    except GbError as exc:
        posts = {"posts": [], "count": 0, "error": str(exc)}
    except Exception:  # noqa: BLE001
        _logger.exception("Update Data: reading the Content posts failed")
        posts = {"posts": [], "count": 0, "error": "Không đọc được bài Content (lỗi nội bộ); xem nhật ký máy chủ."}
    payload = {
        "format": FORMAT,
        "taken_at": datetime.now(HCM).isoformat(timespec="seconds"),
        "source": rec.where(),
        "gb": gb,
        "content_calls": rec.log,
        "posts": posts,
        "summary": {"gb_total": gb_total(gb), "content_total": content_all["content"],
                    "content_approved": content_all["approved"], "content_unapproved": content_all["unapproved"],
                    "posts": posts.get("count", 0), "posts_error": posts.get("error")},
    }
    # The saved version must reproduce the live answer: replay it and compare with what was just read.
    again = ReplayClient(rec.log, "kiểm tra", "check")
    check = fetch_content(again, "all", today)
    for name in ("content", "unapproved", "approved", "archived", "rejected"):
        if check[name] != content_all[name]:
            raise GbError(f"Bản lưu Content không tái hiện đúng số liệu ({name}); không lưu phiên bản.")
    size = len(json.dumps(payload, default=str))
    if size > MAX_BYTES:
        raise GbError(f"Phiên bản quá lớn ({size // 1024} KB) để lưu an toàn.")
    return payload


def gb_total(gb: dict) -> int:
    return sum(v[0] for v in (gb.get("daily") or {}).values()) + (gb.get("undated") or [0])[0]


def check_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("format") != FORMAT or not isinstance(payload.get("gb"), dict) \
            or not isinstance(payload.get("content_calls"), dict):
        raise GbError("Phiên bản đã lưu không đọc được (sai định dạng); hãy bấm Update Data.")
    return payload


def label(payload: dict[str, Any]) -> str:
    return str(payload.get("source") or "")


def fetch_gb(payload: dict[str, Any], period) -> dict:
    """The GB card from a saved version; same fields as ``sgt.fetch_gb``."""
    gb = payload["gb"]
    values = gb_history.values_from_daily(gb, period.start, period.end)
    prev = period.previous()
    previous = gb_history.values_from_daily(gb, prev.start, prev.end) if prev is not None else None
    return {"kpi": "gb", "source": "sgt", "available": True, "reason": None, **period.as_dict(),
            "total": values["total_published"], "approved": values["approved_links"],
            "not_approved": values["not_approved_links"], "unchecked": values["uncheck"],
            "previous": previous["approved_links"] if previous else None,
            "previous_total": previous["total_published"] if previous else None,
            "basis": values["data_source"], "aggregation": values["aggregation"],
            "cached": False, "updated_at": payload.get("taken_at")}
