"""Pure time-window utilities. Integer full-days, cumulative across visits.
Open windows come from lead's existing Chatter stage/active history;
Won/Lost pauses the clock; total age never pauses.
"""
from datetime import datetime


def active_windows(created_at, now, current_stage, current_active, won_stages,
                   events, date_closed=None, currently_closed=False):
    """Derive conservative open windows from CRM event snapshots.
    Missing transitions do not receive fictitious time allocations.
    """
    if not created_at or now <= created_at:
        return []
    stage = int(current_stage or 0)
    active = True
    chronological = sorted(
        (e for e in events if e.get('at') and created_at <= e['at'] <= now),
        key=lambda e: (e['at'], e.get('id', 0)))
    for e in chronological:
        if e['field'] == 'stage_id':
            stage = int(e.get('old') or 0)
            break
    for e in chronological:
        if e['field'] == 'active':
            active = bool(e.get('old'))
            break
    # Some Lost operations are not Chatter-tracked. When date_closed is known,
    # preserve open time *up to closure* rather than losing the whole interval.
    has_close = any(e['field'] == 'active' and not bool(e.get('new')) for e in chronological)
    if (currently_closed and not has_close and date_closed
            and created_at < date_closed <= now):
        chronological.append({'field': 'active', 'at': date_closed, 'old': 1, 'new': 0})
        chronological.sort(key=lambda e: (e['at'], e.get('id', 0)))
    position = created_at
    windows = []
    for e in chronological:
        moment = max(position, min(now, e['at']))
        if active and stage not in won_stages and not (stage == 0 and chronological):
            if moment > position:
                windows.append((position, moment))
        position = moment
        if e['field'] == 'stage_id':
            stage = int(e.get('new') or 0)
        elif e['field'] == 'active':
            active = bool(e.get('new'))
    # Current values override potentially incomplete Chatter history. If those
    # values mismatch, don't ascribe an unverified interval to the current stage.
    if stage != int(current_stage or 0) or active != bool(current_active):
        position = now
    if currently_closed:
        position = now
    if position < now and active and stage not in won_stages:
        windows.append((position, now))
    return windows


def visit_seconds(visits, windows, now):
    """visits: (start, end_or_none) pairs for ONE funnel stage."""
    total = 0.0
    for start, end in visits:
        if not start:
            continue
        finish = min(end or now, now)
        for a, b in windows:
            left, right = max(a, start), min(b, finish)
            if right > left:
                total += (right - left).total_seconds()
    return max(0, int(total))


def full_days(seconds):
    return max(0, int(seconds // 86400))


def stage_color(days, closed=False):
    if closed:
        return 'stopped'
    return 'green' if days <= 3 else 'yellow' if days <= 7 else 'red'


# ---- Update_016: age of a Deal in its current stage (Kanban bar, card label, list colour) ----
AGE_BUCKETS = (('fresh', 'Fresh (0-3 d)'), ('warn', 'Warning (4-7 d)'), ('late', 'Late (> 7 d)'))
AGE_FRESH_MAX = 3      # days, inclusive: 0-3 green
AGE_WARN_MAX = 7       # days, inclusive: 4-7 yellow, more = red


def age_days(since, now):
    """Whole days between the last stage change and now (never negative)."""
    if not since or not now or now <= since:
        return 0
    return int((now - since).total_seconds() // 86400)


def age_bucket(days, closed=False):
    """fresh / warn / late; False for Won Deals (no colour)."""
    if closed:
        return False
    return 'fresh' if days <= AGE_FRESH_MAX else 'warn' if days <= AGE_WARN_MAX else 'late'


# Update_016: data a Deal needs in the Match Making columns (bell).  Update_025: no longer blocks the move,
# only the bell + red frames.  (technical field, label shown to the user).  Change this list to change the rule.
MM_REQUIRED_FIELDS = (('partner_id', 'Contact'), ('email_from', 'Email'), ('phone', 'Phone'),
                      ('source_id', 'Source'), ('x_getfly_id', 'VN Odoo ID'), ('street', 'Address'))
# Columns where the missing data is framed in red automatically when the Deal is opened (Update_025;
# Update_016-024 blocked the move into them).  Exact names, no fuzzy matching.
MM_GUARD_STAGE_NAMES = ('5.Match Making', '6.Approved Match Making')

# Update_025: evidence picture pasted in the Evidence box of CRM-005 (field of CRM-005, checked softly:
# without CRM-005 the field does not exist and Evidence is not required).
EVIDENCE_FIELD = 'x_yp_evidence_html'
EVIDENCE_LABEL = 'Evidence'


def evidence_missing(html):
    """True when the Evidence box holds no picture (empty, only text, or only <p><br></p>)."""
    return '<img' not in str(html or '').lower()


def in_gate_stage(stage_name):
    return (stage_name or '') in MM_GUARD_STAGE_NAMES


def missing_labels(getter, required=MM_REQUIRED_FIELDS, available=None):
    """Labels of the required fields that are empty.  `getter(field)` returns the value;
    fields not present in this database (`available` set) are skipped, not reported."""
    out = []
    for name, label in required:
        if available is not None and name not in available:
            continue
        value = getter(name)
        if value is None or value is False or (isinstance(value, str) and not value.strip()) \
                or (not isinstance(value, (int, float, str)) and not value):   # empty record set (Many2one)
            out.append(label)
    return out
