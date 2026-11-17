"""One time filter for every KPI (same rules as the Management Dashboard: Day / Week / Month / All Time + reference date).

Dates are Asia/Ho_Chi_Minh calendar days. ``previous`` is the period right before the selected one (same length; a calendar
month is compared with the previous calendar month). ``all`` has no previous period.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time as day_time, timedelta, timezone
from zoneinfo import ZoneInfo

HCM = ZoneInfo("Asia/Ho_Chi_Minh")
PERIOD_TYPES = ("day", "week", "month", "all")
DEFAULT_PERIOD = "week"


class PeriodError(ValueError):
    """Bad period / date given by the browser."""


@dataclass(frozen=True)
class Period:
    kind: str
    reference: date
    start: date | None
    end: date | None
    prev_start: date | None
    prev_end: date | None

    @property
    def is_all(self) -> bool:
        return self.start is None

    def previous(self) -> "Period | None":
        if self.prev_start is None:
            return None
        return Period(self.kind, self.prev_start, self.prev_start, self.prev_end, *_before(self.kind, self.prev_start, self.prev_end))

    def utc_bounds(self) -> tuple[str, str] | None:
        """[start, end) as Odoo UTC datetime text; None for All Time."""
        if self.start is None or self.end is None:
            return None
        left = datetime.combine(self.start, day_time.min, tzinfo=HCM).astimezone(timezone.utc)
        right = datetime.combine(self.end + timedelta(days=1), day_time.min, tzinfo=HCM).astimezone(timezone.utc)
        return left.strftime("%Y-%m-%d %H:%M:%S"), right.strftime("%Y-%m-%d %H:%M:%S")

    def label(self) -> str:
        if self.start is None:
            return ""
        return str(self.start) if self.start == self.end else f"{self.start} – {self.end}"

    def as_dict(self) -> dict:
        return {
            "period_type": self.kind, "reference_date": str(self.reference),
            "date_from": str(self.start) if self.start else None, "date_to": str(self.end) if self.end else None,
            "previous_from": str(self.prev_start) if self.prev_start else None,
            "previous_to": str(self.prev_end) if self.prev_end else None,
            "label": self.label(),
        }


def today() -> date:
    return datetime.now(HCM).date()


def bounds(kind: str, ref: date) -> tuple[date | None, date | None]:
    if kind == "all":
        return None, None
    if kind == "day":
        return ref, ref
    if kind == "week":
        monday = ref - timedelta(days=ref.weekday())
        return monday, monday + timedelta(days=6)
    first = ref.replace(day=1)
    nxt = first.replace(year=first.year + 1, month=1) if first.month == 12 else first.replace(month=first.month + 1)
    return first, nxt - timedelta(days=1)


def _before(kind: str, start: date | None, end: date | None) -> tuple[date | None, date | None]:
    if start is None or end is None:
        return None, None
    if kind == "month":
        prev_end = start - timedelta(days=1)
        return prev_end.replace(day=1), prev_end
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=span - 1), prev_end


def resolve(kind: str | None, reference: str | None) -> Period:
    kind = (kind or DEFAULT_PERIOD).strip().lower()
    if kind not in PERIOD_TYPES:
        raise PeriodError("Kỳ không hợp lệ. Chọn Ngày / Tuần / Tháng / Toàn thời gian.")
    try:
        ref = date.fromisoformat(reference) if reference else today()
    except (ValueError, TypeError) as exc:
        raise PeriodError("Ngày tham chiếu không hợp lệ (YYYY-MM-DD).") from exc
    if not date(2000, 1, 1) <= ref <= date(2100, 12, 31):
        raise PeriodError("Ngày tham chiếu nằm ngoài phạm vi cho phép.")
    start, end = bounds(kind, ref)
    prev_start, prev_end = _before(kind, start, end)
    return Period(kind, ref, start, end, prev_start, prev_end)


def delta(current: int, previous: int | None) -> dict:
    """'So với kỳ trước' as the Dashboard shows it: percentage, direction up (>= 0 %) / down / flat (N/A)."""
    if previous is None:
        return {"value": None, "direction": "flat"}
    if previous == 0:
        return {"value": 0.0, "direction": "up"} if current == 0 else {"value": None, "direction": "flat"}
    value = round((current - previous) / previous * 100, 1)
    return {"value": value, "direction": "up" if value >= 0 else "down"}
