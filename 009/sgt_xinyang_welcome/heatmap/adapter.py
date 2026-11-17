"""Bridge that lets the XINYANG MAP data builders (ported from the Management Dashboard) read Odoo directly.

The Dashboard reads Odoo through JSON-RPC with the logged-in user's own account. Inside Odoo the same thing is the user's
own environment (``request.env``): the same access rights and record rules apply, nothing is read with sudo and nothing
is written. ``OdooEnvGateway`` offers the three calls the builders use (``call``, ``fields``, ``fields_get``) with the
RPC conventions (positional ``args`` list, ``kwargs`` dict with an optional ``context``) and returns RPC-shaped values
(lists instead of tuples, dates as strings, binaries as text), so the builders run unchanged and give the same payload.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - the module is also imported by tests that run without Odoo
    from odoo.exceptions import AccessError, MissingError, UserError
    _ORM_ERRORS: tuple = (AccessError, MissingError, UserError)
except ImportError:  # pragma: no cover
    _ORM_ERRORS = ()

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
ALLOWED_METHODS = frozenset({"search_read", "search_count", "read", "fields_get", "read_group"})   # read only, nothing else is reachable


class OdooError(RuntimeError):
    """Message that is safe to show to the user."""


@dataclass
class OdooSession:
    uid: int
    token: str          # database + user: the key of the per-user snapshot cache


def _plain(value: Any) -> Any:
    """ORM value -> the value JSON-RPC would have returned."""
    if isinstance(value, _dt.datetime):
        return value.strftime(DATETIME_FORMAT)
    if isinstance(value, _dt.date):
        return value.strftime(DATE_FORMAT)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("ascii", "ignore")
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


class OdooEnvGateway:
    """Same interface as the Dashboard's OdooGateway, backed by an Odoo environment (the user's own)."""

    def __init__(self, env: Any, models: dict | None = None):
        self.env = env
        self.models = models        # None = every model; a dict {model: allowed methods} limits this gateway to exactly those

    def elevated(self, models: dict) -> "OdooEnvGateway":
        """Gateway with the rights of the system, limited to ``models`` = {model: methods} (read only like every gateway).

        Used for ONE thing: the Chatter stage history (``mail.message`` / ``mail.tracking.value``) and the field / funnel
        names, which Odoo 19 hides from everybody but Settings Administrators. The caller must always pass record ids it
        already read with the user's own gateway, so a user never gets history of a Deal they cannot see.
        """
        return OdooEnvGateway(self.env(su=True), {m: frozenset(v) for m, v in models.items()})

    def session(self) -> OdooSession:
        return OdooSession(uid=int(self.env.uid), token=f"{self.env.cr.dbname}:{int(self.env.uid)}")

    def _model(self, model: str, context: dict | None = None):
        if self.models is not None and model not in self.models:
            raise OdooError(f"Không được phép đọc {model} bằng quyền nâng cao.")
        try:
            records = self.env[model]
        except KeyError as exc:
            raise OdooError(f"Database này chưa có model {model}.") from exc
        return records.with_context(**context) if context else records

    def call(self, session: OdooSession, model: str, method: str, args=None, kwargs=None):
        if method not in ALLOWED_METHODS:
            raise OdooError(f"Không được phép gọi {method}.")
        if self.models is not None and method not in self.models.get(model, frozenset()):
            raise OdooError(f"Không được phép gọi {method} trên {model} bằng quyền nâng cao.")
        args = list(args or [])
        kwargs = dict(kwargs or {})
        context = kwargs.pop("context", None)
        try:
            records = self._model(model, context)
            if method == "read":    # JSON-RPC sends the ids first; in the ORM read() is called on the recordset: browse(ids).read(fields)
                records = records.browse(args.pop(0) if args else kwargs.pop("ids", []))
            result = getattr(records, method)(*args, **kwargs)
        except OdooError:
            raise
        except _ORM_ERRORS as exc:
            raise OdooError(f"Odoo từ chối quyền truy cập: {exc}") from exc
        return _plain(result)

    def fields(self, session: OdooSession, model: str) -> set[str]:
        return set(self._model(model)._fields)

    def fields_get(self, session: OdooSession, model: str, fields: list[str] | None = None) -> dict[str, Any]:
        try:
            result = self._model(model).fields_get(fields or None, attributes=["type", "string", "selection", "relation"])
        except _ORM_ERRORS as exc:
            raise OdooError(f"Odoo từ chối quyền truy cập: {exc}") from exc
        return _plain(result) or {}


# Same names as the Dashboard module, so the ported builders keep their original type hints.
OdooGateway = OdooEnvGateway
