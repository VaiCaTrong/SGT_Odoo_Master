"""Connector to the SGT (social360) Odoo: GB · Bài post đã duyệt and Content · Đã duyệt of Project XINYANG.

The Management Dashboard logs in to social360 with each person's own account. Inside Odoo there is no password to reuse, so
this connector uses ONE read-only service account (login + API key) that a Settings Administrator types in Home > Settings.
Nothing is written to social360; the key never leaves the server (it is not sent to the browser and never shown again).
Until the connection is set (or when social360 answers with an error) the KPI shows the reason, never a guessed number.
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from . import period as _period

PROJECT_MODEL = "sgt.social.destination"
HISTORY_MODEL = "sgt.social.publish.history"
CACHE_SECONDS = 60
HCM = ZoneInfo("Asia/Ho_Chi_Minh")


class GbError(RuntimeError):
    """The social360 side cannot be read / verified; the message is shown to the user."""


def normalized_period(period_type: str, reference_date: str) -> tuple[date | None, date | None]:
    try:
        p = _period.resolve(period_type, reference_date)
    except _period.PeriodError as exc:
        raise GbError(str(exc)) from exc
    return p.start, p.end


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GbError(f"SGT trả về trường {name} không hợp lệ.")
    return value


class SgtClient:
    """JSON-RPC client (service account). One instance = one connection setting; ``_call`` is what gb_history / content use."""

    def __init__(self, url: str, db: str, login: str, secret: str, verify_ssl: bool = True, rpc=None):
        url = (url or "").strip().rstrip("/")
        if url.lower().endswith("/odoo"):
            url = url[:-5].rstrip("/")
        self.url, self.db, self.login, self._secret = url, (db or "").strip(), (login or "").strip(), secret or ""
        self.verify_ssl = verify_ssl
        self._rpc_override = rpc
        self._uid: int | None = None
        self._project_id: int | None = None
        self._log_model: str | None = None
        self._meta: dict[tuple, tuple[float, Any]] = {}

    def configured(self) -> bool:
        return bool(self.url and self.db and self.login and self._secret) or self._rpc_override is not None

    def where(self) -> str:
        return f"{self.url} · database {self.db}"

    @staticmethod
    def _reason(error: Any) -> str:
        if not isinstance(error, dict):
            return ""
        data = error.get("data") if isinstance(error.get("data"), dict) else {}
        text = str(data.get("message") or error.get("message") or "").strip().replace("\n", " ")
        return text[:180]

    def _rpc(self, service: str, method: str, args: list):
        if self._rpc_override is not None:
            return self._rpc_override(service, method, args)
        try:
            import requests
        except ImportError as exc:   # pragma: no cover
            raise GbError("Thiếu thư viện requests trên máy chủ Odoo.") from exc
        if not self.url.lower().startswith(("https://", "http://")):
            raise GbError("URL social360 phải bắt đầu bằng https://")
        try:
            response = requests.post(f"{self.url}/jsonrpc", timeout=(8, 35), verify=self.verify_ssl, json={
                "jsonrpc": "2.0", "method": "call", "id": 1, "params": {"service": service, "method": method, "args": args}})
            response.raise_for_status()
            payload = response.json()
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            raise GbError(f"Odoo {self.where()} trả HTTP {code}; kiểm tra URL (không kèm /odoo), proxy/Cloudflare và dịch vụ Odoo.") from exc
        except requests.Timeout as exc:
            raise GbError(f"Odoo {self.where()} không phản hồi kịp; kiểm tra mạng từ máy chủ Xinyang.") from exc
        except ValueError as exc:
            raise GbError(f"Odoo {self.where()} không trả JSON-RPC hợp lệ (có thể bị Cloudflare chặn); kiểm tra URL.") from exc
        except requests.RequestException as exc:
            raise GbError(f"Không kết nối được Odoo {self.where()} ({type(exc).__name__}); kiểm tra URL, SSL, DNS và mạng từ máy chủ Xinyang.") from exc
        if payload.get("error"):
            reason = self._reason(payload["error"])
            raise GbError(f"Odoo {self.where()} từ chối yêu cầu ({service}.{method})" + (f": {reason}" if reason else "") + ".")
        return payload.get("result")

    def _authenticate(self) -> int:
        if self._uid:
            return self._uid
        uid = self._rpc("common", "authenticate", [self.db, self.login, self._secret, {}])
        if type(uid) is not int or uid < 1:
            raise GbError(f"Tài khoản dịch vụ không đăng nhập được social360 ({self.where()}). Kiểm tra login / API key / database.")
        self._uid = uid
        return uid

    def _call(self, model: str, method: str, args: list, kwargs: dict | None = None):
        key = None
        if method == "fields_get":
            key = (model, repr(args), repr(sorted((kwargs or {}).items())))
            hit = self._meta.get(key)
            if hit and hit[0] > time.monotonic():
                return hit[1]
        result = self._rpc("object", "execute_kw", [self.db, self._authenticate(), self._secret, model, method, args, kwargs or {}])
        if key is not None and isinstance(result, dict) and result:
            self._meta[key] = (time.monotonic() + 600, result)
        return result

    def _project(self) -> int:
        if self._project_id:
            return self._project_id
        rows = self._call(PROJECT_MODEL, "search_read", [[("name", "=", "XINYANG")]], {"fields": ["id", "name"], "limit": 3}) or []
        if len(rows) != 1 or rows[0].get("name") != "XINYANG":
            raise GbError("Project XINYANG trên SGT không tồn tại duy nhất (hoặc tài khoản dịch vụ không thấy nó). Kiểm tra sgt.social.destination.")
        self._project_id = _integer(rows[0]["id"], "project_id")
        return self._project_id

    def _discover_history_model(self) -> str:
        if self._log_model:
            return self._log_model
        probe = None
        try:
            probe = self._call(HISTORY_MODEL, "fields_get", [], {"attributes": ["type"]})
        except GbError:
            probe = None
        if not (isinstance(probe, dict) and "posted_at" in probe and "project_id" in probe):
            raise GbError(f"Tài khoản dịch vụ không đọc được model {HISTORY_MODEL} (GB Publishing History). Cấp quyền xem GB Logs cho tài khoản này.")
        self._log_model = HISTORY_MODEL
        return HISTORY_MODEL


# ---- one client + short cache per connection (the numbers are the same for everybody who may see the dashboard) ----------
_LOCK = threading.Lock()
_CACHE: dict[tuple, tuple[float, Any]] = {}


def forget_all():
    with _LOCK:
        _CACHE.clear()


def _cached(key: tuple, force: bool, build):
    now = time.monotonic()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and not force and now - hit[0] < CACHE_SECONDS:
            return hit[1], True
    value = build()
    with _LOCK:
        if len(_CACHE) > 200:
            _CACHE.clear()
        _CACHE[key] = (time.monotonic(), value)
    return value, False


def _stamp() -> str:
    return datetime.now(HCM).isoformat(timespec="seconds")


def fetch_gb(client: SgtClient, period: _period.Period, force: bool = False) -> dict:
    """GB · Bài post đã duyệt: Tổng / Đã duyệt / Không duyệt / Chưa kiểm tra from SGT Publishing History."""
    from .gb_history import fetch_history

    def build():
        try:
            values = fetch_history(client, period.kind, period.start, period.end)
        except GbError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GbError("Không thể truy vấn GB Publishing History ở SGT. Kiểm tra quyền xem Logs, model và kết nối mạng.") from exc
        return values

    values, was_cached = _cached((client.url, client.db, client.login, "gb", period.kind, str(period.start)), force, build)
    previous = None
    prev = period.previous()
    if prev is not None:
        try:
            previous, _ = _cached((client.url, client.db, client.login, "gb", prev.kind, str(prev.start)), force,
                                  lambda: fetch_history(client, prev.kind, prev.start, prev.end))
        except Exception:  # noqa: BLE001 - the comparison never blocks the main numbers
            previous = None
    return {"kpi": "gb", "source": "sgt", "available": True, "reason": None, **period.as_dict(),
            "total": values["total_published"], "approved": values["approved_links"],
            "not_approved": values["not_approved_links"], "unchecked": values["uncheck"],
            "previous": previous["approved_links"] if previous else None,
            "previous_total": previous["total_published"] if previous else None,
            "basis": values.get("data_source"), "aggregation": values.get("aggregation"),
            "cached": was_cached, "updated_at": _stamp()}


def fetch_content_kpi(client: SgtClient, period: _period.Period, force: bool = False) -> dict:
    """Content · Đã duyệt: Tổng / Chưa duyệt / Đã duyệt (theo Last Reviewed) / Đã lưu trữ."""
    from .content import fetch_content
    try:
        raw, was_cached = _cached((client.url, client.db, client.login, "content", period.kind, str(period.reference)), force,
                                  lambda: fetch_content(client, period.kind, str(period.reference)))
    except GbError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GbError("Không thể truy vấn Content ở SGT. Kiểm tra quyền của tài khoản dịch vụ và kết nối mạng.") from exc
    month = raw.get("month_view") or {}
    selected = (raw.get("comparison_009") or {}).get("selected") or {}
    prev = selected.get("previous") or None
    creators = raw.get("creators_009") or {}
    return {"kpi": "content", "source": "sgt", "available": True, "reason": None, **period.as_dict(),
            "total": raw["content"], "unapproved": raw["unapproved"], "approved": raw["approved"],
            "archived": raw["archived"], "rejected": raw["rejected"],
            "previous": prev.get("approved") if isinstance(prev, dict) else None,
            "month_view": month, "daily": (raw.get("daily_breakdown") or [])[:60],
            "creators": (creators.get("people") or [])[:50] if creators.get("available") else [],
            "creators_notice": None if creators.get("available") else creators.get("notice"),
            "basis": raw.get("cohort_explanation"), "checked_publications": raw.get("checked_publications"),
            "cached": was_cached, "updated_at": _stamp()}
