"""Pure timeline accumulator for CRM-001 (V03).

V03: NOTHING stops the counter.  Won, Lost (archived) and any hand-off to
another funnel keep counting in the Stage the Deal currently sits in, exactly
like an ordinary Stage.  A Deal handed to the Sale funnels is the SAME record,
so it simply inherits its counters.  No persistent state is created; the
source is standard mail tracking of ``stage_id``.
"""

from collections import defaultdict


def cumulative_stage_seconds(created_at, now, current_stage, current_active=True,
                             won_stage_ids=(), events=(), last_stage_update=None,
                             date_closed=None):
    """Return nonnegative seconds by Stage ID.

    events: mappings with keys 'at', 'field', 'old', 'new'.  Only 'stage_id'
    events matter; 'active' events (Lost / reopen) are ignored on purpose.
    ``current_active``, ``won_stage_ids`` and ``date_closed`` are accepted for
    compatibility and are NOT used any more.
    """
    totals = defaultdict(float)
    if not created_at or now <= created_at:
        return {}

    stage_events = sorted((e for e in events if e['field'] == 'stage_id'),
                          key=lambda e: (e['at'], e.get('id', 0)))
    stage = int(current_stage or 0)
    if stage_events:
        # Initial stage = the oldest *old* value in the Chatter.
        stage = int(stage_events[0]['old'] or 0)
    elif last_stage_update and created_at < last_stage_update <= now:
        # No documented transition: do not ascribe the whole lifetime to a Stage
        # we cannot verify; start counting at the last stage update.
        stage_events = [{'at': last_stage_update, 'field': 'stage_id',
                         'old': 0, 'new': int(current_stage or 0), 'id': 0}]
        stage = 0

    previous = created_at
    for event in stage_events:
        moment = min(now, max(created_at, event['at']))
        if moment < previous:
            continue
        if stage:
            totals[stage] += (moment - previous).total_seconds()
        previous = moment
        stage = int(event['new'] or 0)

    # The database is authoritative when the Chatter misses a transition: do NOT
    # give the elapsed time to an unverified Stage.
    if stage != int(current_stage or 0):
        stage = int(current_stage or 0)
        previous = max(previous, last_stage_update or now)
    if stage and previous < now:
        totals[stage] += (now - previous).total_seconds()
    return {key: max(0, int(value)) for key, value in totals.items()}


def elapsed_full_days(seconds):
    return max(0, int(max(0, seconds) // 86400))


def stage_color_from_days(days):
    """UI-only Stage color: 0..3 green, 4..7 yellow, 8+ red."""
    days = max(0, int(days))
    if days <= 3:
        return 'green'
    if days <= 7:
        return 'yellow'
    return 'red'
