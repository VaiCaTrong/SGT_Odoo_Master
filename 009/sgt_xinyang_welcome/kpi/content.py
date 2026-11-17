"""Content created-in-period KPI for XINYANG on SGT; strictly read-only.

Source-of-truth statuses are Odoo's destination relation sets. Post create_date
is the cohort date for every column EXCEPT "approved": Update 024 counts approved
Content by sgt.social.post.reviewed_at ("Last Reviewed"), i.e. publications that are
currently approved AND were last reviewed inside the period.
Counters represent CURRENT status, not transition history.
Fail closed on contradictory or incomplete records. No content bodies/PII emitted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from typing import Any

from .sgt import GbError, normalized_period, PROJECT_MODEL, _integer

STATES = {
    'unapproved': ('unapproved_content_count', 'unapproved_publication_ids'),
    'approved': ('approved_content_count', 'approved_publication_ids'),
    'rejected': ('rejected_content_count', 'rejected_publication_ids'),
    'archived': ('used_content_count', 'used_publication_ids'),
}
# Statuses that follow an EVENT date instead of the post creation date:
#   approved -> sgt.social.post.reviewed_at (Last Reviewed)
#   archived -> sgt.social.post.reviewed_at as well: SGT has no separate archive-date field; an Archived post shows
#               Reviewed By + Last Reviewed (screenshot of an Archived post, 2026-10-28), i.e. the last status change.
#               Set ARCHIVED_DATE_FIELD = None to fall back to the creation date.
EVENT_STATES = ('approved', 'archived')
ARCHIVED_DATE_FIELD: str | None = 'reviewed_at'
MAX_PUBLICATIONS = 50000
MAX_POSTS = 50000
BATCH = 300


def _ids(value: Any, field: str) -> set[int]:
    if not isinstance(value, list) or any(type(x) is not int or x <= 0 for x in value) or len(set(value)) != len(value):
        raise GbError(f'Content: quan hệ {field} thiếu, trùng hoặc không hợp lệ.')
    return set(value)


def _relation_id(value: Any) -> int | None:
    if isinstance(value, (list, tuple)) and value and type(value[0]) is int:
        return value[0]
    if type(value) is int:
        return value
    return None


def _iso_local(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise GbError(f'Content có {label} trống, không thể xác định ngày tạo.')
    try:
        d = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError as exc:
        raise GbError(f'Content có {label} không hợp lệ.') from exc
    # Odoo ORM datetime strings are UTC, without offset.
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))


def _schema(service) -> None:
    definitions = {
        PROJECT_MODEL: {'name': 'char', 'content_count': 'integer', 'publication_ids': 'one2many',
                        **{k: 'integer' for k, _ in STATES.values()},
                        **{k: 'one2many' for _, k in STATES.values()}},
        'sgt.social.post.publication': {'id': 'integer', 'post_id': 'many2one', 'destination_id': 'many2one'},
        'sgt.social.post': {'id': 'integer', 'create_date': 'datetime', 'reviewed_at': 'datetime',
                            **({ARCHIVED_DATE_FIELD: 'datetime'} if ARCHIVED_DATE_FIELD else {})},
    }
    for model, expected in definitions.items():
        meta = service._call(model, 'fields_get', [], {'attributes': ['type', 'relation']})
        if not isinstance(meta, dict):
            raise GbError(f'Không xác minh được schema Content của {model}.')
        if any(not isinstance(meta.get(field), dict) or meta[field].get('type') != typ
               for field, typ in expected.items()):
            raise GbError(f'Model {model} thiếu trường hoặc sai kiểu dữ liệu cần thiết để đếm Content theo ngày tạo / ngày duyệt (reviewed_at).')
    # Relation fields must point to their verified technical models.
    meta = service._call(PROJECT_MODEL, 'fields_get', [], {'attributes': ['type', 'relation']})
    for relation in ['publication_ids', *[x[1] for x in STATES.values()]]:
        if meta[relation].get('relation') != 'sgt.social.post.publication':
            raise GbError(f'Quan hệ {relation} không trỏ tới sgt.social.post.publication.')
    pub_meta = service._call('sgt.social.post.publication', 'fields_get', [], {'attributes': ['type', 'relation']})
    for field, target in [('destination_id', PROJECT_MODEL), ('post_id', 'sgt.social.post')]:
        if pub_meta[field].get('relation') != target:
            raise GbError(f'Quan hệ {field} không liên kết đúng model {target}.')


def _read_chunks(service, model: str, identifiers: set[int], fields: list[str], limit: int) -> dict[int, dict]:
    if len(identifiers) > limit:
        raise GbError(f'Content vượt giới hạn kiểm tra {limit} bản ghi; cần giải pháp phân trang an toàn trước khi tính KPI.')
    output = {}
    sorted_ids = sorted(identifiers)
    for offset in range(0, len(identifiers), BATCH):
        requested = sorted_ids[offset:offset + BATCH]
        rows = service._call(model, 'read', [requested], {'fields': fields})
        if not isinstance(rows, list) or len(rows) != len(requested):
            raise GbError(f'Không đọc được đầy đủ dữ liệu Content từ {model}.')
        for row in rows:
            if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] not in requested or row['id'] in output:
                raise GbError(f'Bản ghi Content không hợp lệ hoặc trùng trong {model}.')
            output[row['id']] = row
    if set(output) != identifiers:
        raise GbError(f'Không thể xác minh toàn bộ ID thuộc {model}.')
    return output


def fetch_content(service, period_type: str, reference_date: str, *, include_approved_samples: bool = False) -> dict:
    start, end = normalized_period(period_type, reference_date)
    _schema(service)
    # Verified Odoo sgt.social.post technical field screenshots (Update 009).
    # Optional data never changes the correctness of Update 008's 5 KPIs.
    post_meta = service._call('sgt.social.post', 'fields_get', [],
                              {'attributes': ['type', 'relation']})
    author_fields_ok = (isinstance(post_meta, dict) and
        isinstance(post_meta.get('author_id'), dict) and
        post_meta['author_id'].get('type') == 'many2one' and
        post_meta['author_id'].get('relation') == 'res.users')
    author_name_ok = (isinstance(post_meta, dict) and
        isinstance(post_meta.get('author_display_name'), dict) and
        post_meta['author_display_name'].get('type') == 'char')
    submitted_ok = (isinstance(post_meta, dict) and
        isinstance(post_meta.get('submitted_at'), dict) and
        post_meta['submitted_at'].get('type') == 'datetime')
    pid = service._project()  # fixed exact XINYANG name, single project
    fields = ['id', 'name', 'content_count', 'publication_ids'] + [x for pair in STATES.values() for x in pair]
    rows = service._call(PROJECT_MODEL, 'read', [[pid]], {'fields': fields})
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get('name') != 'XINYANG':
        raise GbError('Không xác nhận được Project XINYANG trong dữ liệu Content SGT.')
    proj = rows[0]
    all_ids = _ids(proj.get('publication_ids'), 'publication_ids')
    groups: dict[str, set[int]] = {}
    for state, (counter, relation) in STATES.items():
        group = _ids(proj.get(relation), relation)
        if len(group) != _integer(proj.get(counter), counter):
            raise GbError(f'Số lượng {state} không khớp field {counter} của SGT; dừng để tránh đếm sai.')
        groups[state] = group
    combined = [pid for group in groups.values() for pid in group]
    if len(combined) != len(set(combined)) or set(combined) != all_ids:
        raise GbError('Các nhóm trạng thái Content chồng lấn hoặc thiếu bản ghi so với danh sách Project.')
    total = _integer(proj.get('content_count'), 'content_count')
    if total != len(all_ids) or total != sum(len(group) for group in groups.values()):
        raise GbError('Bộ đếm Content toàn thời gian không khớp với các nhóm trạng thái SGT; cần xác minh quy tắc nghiệp vụ.')
    # Explicitly scoped to this project, never another destination; limit all-time batch reads.
    publications = _read_chunks(service, 'sgt.social.post.publication', all_ids,
                                ['id', 'post_id', 'destination_id'], MAX_PUBLICATIONS)
    linked_posts: set[int] = set()
    pub_post: dict[int, int] = {}
    for pub_id, publication in publications.items():
        if _relation_id(publication.get('destination_id')) != pid:
            raise GbError('Publication không thuộc Project XINYANG; từ chối dữ liệu sai Project.')
        post_id = _relation_id(publication.get('post_id'))
        if post_id is None or post_id < 1:
            raise GbError('Publication thiếu liên kết Content gốc để lấy ngày tạo.')
        pub_post[pub_id] = post_id
        linked_posts.add(post_id)
    post_fields = list(dict.fromkeys(['id', 'create_date', 'reviewed_at'] + ([ARCHIVED_DATE_FIELD] if ARCHIVED_DATE_FIELD else [])))
    if author_fields_ok:
        post_fields.append('author_id')
    if author_name_ok:
        post_fields.append('author_display_name')
    if submitted_ok:
        post_fields.append('submitted_at')
    posts = _read_chunks(service, 'sgt.social.post', linked_posts, post_fields, MAX_POSTS)
    datetimes = {k: _iso_local(v.get('create_date'), 'create_date') for k, v in posts.items()}
    # Last Reviewed: empty means "never reviewed" (no date); a non-empty value must parse.
    reviewed = {k: (_iso_local(v['reviewed_at'], 'reviewed_at') if v.get('reviewed_at') else None) for k, v in posts.items()}

    archived_at = {k: (_iso_local(v[ARCHIVED_DATE_FIELD], ARCHIVED_DATE_FIELD) if v.get(ARCHIVED_DATE_FIELD) else None)
                   for k, v in posts.items()} if ARCHIVED_DATE_FIELD else dict(datetimes)

    def in_range(d: date | None, left: date | None, right: date | None) -> bool:
        return left is None or (d is not None and left <= d <= right)

    def event_when(state: str, pub_id: int) -> datetime | None:
        post_id = pub_post[pub_id]
        return reviewed[post_id] if state == 'approved' else archived_at[post_id]

    def event_pubs(state: str, left: date | None, right: date | None) -> list[int]:
        """Currently-<state> publications whose event date is in [left, right]; all of them for All Time."""
        return [pub_id for pub_id in groups[state]
                if in_range((lambda w: w and w.date())(event_when(state, pub_id)), left, right)]

    counts: Counter = Counter()          # create_date cohort, all four statuses
    by_day: dict[str, Counter] = {}
    for state, group in groups.items():
        for pub_id in group:
            d = datetimes[pub_post[pub_id]].date()
            if start is None or start <= d <= end:
                counts[state] += 1
                by_day.setdefault(str(d), Counter())[state] += 1
    event_selected = {state: event_pubs(state, start, end) for state in EVENT_STATES}
    event_total = {state: len(items) for state, items in event_selected.items()}
    for state, items in event_selected.items():
        for pub_id in items:
            when = event_when(state, pub_id)
            if when is not None:
                by_day.setdefault(str(when.date()), Counter())[state + '_event'] += 1
    daily = []
    for day, cnt in sorted(by_day.items(), reverse=True):
        created = cnt['unapproved'] + cnt['approved'] + cnt['rejected'] + cnt['archived']
        daily.append({'date': day, 'content': created, 'unapproved': cnt['unapproved'],
                      'approved_created': cnt['approved'], 'approved': cnt['approved_event'],
                      'rejected': cnt['rejected'],
                      'archived_created': cnt['archived'], 'archived': cnt['archived_event']})
    final_total = sum(counts.values())
    approved_without_review = sum(1 for pub_id in groups['approved'] if reviewed[pub_post[pub_id]] is None)
    if period_type == 'all' and final_total != total:
        raise GbError('Content All Time không khớp số liệu SGT.')
    for state in EVENT_STATES:
        if period_type == 'all' and event_total[state] != len(groups[state]):
            raise GbError(f'Content {state} All Time không khớp số liệu SGT.')
    # All supplementary calculations reuse the *same* verified Project, pub IDs,
    # post IDs and current statuses as 008. No alternate source.
    def bucket_period(left: date | None, right: date | None) -> dict:
        tally = Counter()
        if left is not None:
            for state, group in groups.items():
                for pub_id in group:
                    d = datetimes[pub_post[pub_id]].date()
                    if left <= d <= right:
                        tally[state] += 1
        out = {'content': sum(tally.values()), **{name: tally[name] for name in STATES},
               'approved_created': tally['approved'], 'archived_created': tally['archived']}
        for state in EVENT_STATES:
            out[state] = len(event_pubs(state, left, right)) if left is not None else 0
        return out

    def period_before():
        if start is None:
            return None, None
        if period_type == 'day':
            return start - timedelta(days=1), start - timedelta(days=1)
        if period_type == 'week':
            return start - timedelta(days=7), end - timedelta(days=7)
        return normalized_period('month', str(start - timedelta(days=1)))

    prev_start, prev_end = period_before()
    today = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
    this_month_start = today.replace(day=1)
    last_month_start, last_month_end = normalized_period('month', str(this_month_start - timedelta(days=1)))
    # Update 024: Tổng Content + Chưa duyệt are a MONTH view (month of the reference date; All Time -> this month),
    # independent of the week/day selection, compared with the previous calendar month.
    ref_day = today if period_type == 'all' else date.fromisoformat(reference_date)
    month_start, month_end = normalized_period('month', str(ref_day))
    prev_month_start, prev_month_end = normalized_period('month', str(month_start - timedelta(days=1)))
    month_view = {
        'label': f'{month_start.month:02d}/{month_start.year}',
        'previous_label': f'{prev_month_start.month:02d}/{prev_month_start.year}',
        'range': [str(month_start), str(month_end)],
        'previous_range': [str(prev_month_start), str(prev_month_end)],
        'current': {k: v for k, v in bucket_period(month_start, month_end).items() if k in ('content', 'unapproved')},
        'previous': {k: v for k, v in bucket_period(prev_month_start, prev_month_end).items() if k in ('content', 'unapproved')},
        'basis': 'sgt.social.post.create_date',
    }
    comparison = {
        'selected': {'current': {'content': final_total, **{k: counts[k] for k in STATES}, **event_total,
                                 'approved_created': counts['approved'], 'archived_created': counts['archived']},
                     'previous': bucket_period(prev_start, prev_end) if prev_start else None,
                     'current_range': [str(start), str(end)] if start else None,
                     'previous_range': [str(prev_start), str(prev_end)] if prev_start else None},
        'month': {'current': bucket_period(this_month_start, today),
                  'previous': bucket_period(last_month_start, last_month_end),
                  'current_range': [str(this_month_start), str(today)],
                  'previous_range': [str(last_month_start), str(last_month_end)],
                  'unequal_periods': True},
    }
    creators = {'available': False,
                'notice': 'Không xác minh được trường author_id liên kết res.users.'}
    if author_fields_ok:
        people = {}
        daily_people = defaultdict(lambda: Counter())
        submitted_dates = defaultdict(lambda: Counter())

        def actor_of(post: dict) -> tuple[str, str]:
            author = post.get('author_id')
            if isinstance(author, (list, tuple)) and len(author) == 2 and type(author[0]) is int and author[0] > 0 and isinstance(author[1], str):
                return str(author[0]), author[1] or f'User #{author[0]}'
            return 'unknown', 'Chưa xác định tác giả'

        def person(actor_id: str, actor_name: str) -> dict:
            if actor_id not in people:
                people[actor_id] = {'id': actor_id, 'name': actor_name, 'content': 0, **{k: 0 for k in STATES}}
            return people[actor_id]

        for state, group in groups.items():
            for pub_id in group:
                post = posts[pub_post[pub_id]]
                d = datetimes[pub_post[pub_id]].date()
                if start is not None and not start <= d <= end:
                    continue
                actor_id, actor_name = actor_of(post)
                row = person(actor_id, actor_name)
                row['content'] += 1
                if state not in EVENT_STATES:
                    row[state] += 1
                daily_people[(str(d), actor_id)]['created_' + state] += 1
                if submitted_ok and post.get('submitted_at'):
                    try:
                        submit_day = str(_iso_local(post['submitted_at'], 'submitted_at').date())
                        submitted_dates[(submit_day, actor_id)]['count'] += 1
                    except GbError:
                        # Optional submission timestamp cannot invalidate KPI.
                        pass
        for state, items in event_selected.items():            # event-date statuses
            for pub_id in items:
                actor_id, actor_name = actor_of(posts[pub_post[pub_id]])
                person(actor_id, actor_name)[state] += 1
                when = event_when(state, pub_id)
                if when is not None:
                    daily_people[(str(when.date()), actor_id)][state] += 1
        p_list = sorted(people.values(), key=lambda p: (-p['content'], -p['approved'], p['name'].casefold()))
        if (sum(p['content'] for p in p_list) == final_total
                and all(sum(p[state] for p in p_list) == event_total[state] for state in EVENT_STATES)
                and all(sum(p[state] for p in p_list) == counts[state] for state in STATES if state not in EVENT_STATES)):
            creator_days = []
            for (d, actor_id), values in daily_people.items():
                created_total = sum(v for k, v in values.items() if k.startswith('created_'))
                creator_days.append({'date': d, 'author_id': actor_id,
                                      'author': people[actor_id]['name'],
                                      'content': created_total, 'approved': values['approved'],
                                      'unapproved': values['created_unapproved'], 'rejected': values['created_rejected'],
                                      'archived': values['archived']})
            creator_days.sort(key=lambda x: (x['date'], x['content'], x['approved']), reverse=True)
            submitted_days = [{'date': d, 'author_id': actor_id,
                               'author': people[actor_id]['name'], 'count': values['count']}
                              for (d, actor_id), values in submitted_dates.items()]
            submitted_days.sort(key=lambda x: (x['date'], x['count']), reverse=True)
            creators = {'available': True, 'basis': 'sgt.social.post.author_id',
                        'unit': 'Project publication (Tổng/Chưa duyệt/Từ chối theo ngày tạo; Đã duyệt theo Last Reviewed; Lưu trữ theo ngày lưu trữ)',
                        'people': p_list, 'daily': creator_days[:400],
                        'daily_rows_total': len(creator_days),
                        'submitted_dates_by_author': submitted_days[:200],
                        'submitted_dates_notice':
                            'submitted_at là ngày gửi của Content gốc, không xác nhận người gửi hoặc ngày gửi riêng vào Project XINYANG.'}
        else:
            creators = {'available': False,
                        'notice': 'Số Content theo tác giả không khớp bộ KPI gốc; không hiển thị.'}
    submitters = {'available': False, 'basis': None,
                  'notice': 'Chưa có field định danh người gửi Content vào Project XINYANG được xác minh. Không tự gán author_id/create_uid thành người gửi.'}
    result = {
        'source': 'sgt', 'project': 'XINYANG', 'data_source': 'SGT Content / Project publications',
        'date_basis': 'sgt.social.post.create_date', 'status_basis': 'current project publication groups',
        'period_type': period_type, 'reference_date': reference_date,
        'date_from': str(start) if start else None, 'date_to': str(end) if end else None,
        'content': final_total, 'unapproved': counts['unapproved'], 'approved': event_total['approved'], 'archived_created': counts['archived'],
        'approved_created': counts['approved'], 'approved_date_basis': 'sgt.social.post.reviewed_at',
        'archived_date_basis': ARCHIVED_DATE_FIELD and f'sgt.social.post.{ARCHIVED_DATE_FIELD}' or 'sgt.social.post.create_date',
        'month_view': month_view,
        'approved_without_review_date': approved_without_review,
        'rejected': counts['rejected'], 'archived': event_total['archived'],
        'checked_publications': len(all_ids), 'checked_posts': len(linked_posts),
        'daily_breakdown': daily, 'days_with_content': len(daily),
        'comparison_009': comparison, 'creators_009': creators, 'submitters_009': submitters,
        'updated_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds'),
        'cohort_explanation': 'Tổng/Chưa duyệt (xem theo tháng, month_view) và Từ chối lọc theo ngày tạo Content; Đã duyệt lọc theo Last Reviewed (reviewed_at); Lưu trữ lọc theo archived_date_basis; đều theo trạng thái hiện tại.',
    }
    if include_approved_samples:
        # EXACT approved publication cohort used by the current Content KPI.
        # Sort ascending in Asia/Ho_Chi_Minh. Only 3 distinct posts go to the weekly report.
        ranked = sorted(event_selected['approved'], key=lambda ident:
                        (reviewed[pub_post[ident]], ident))
        samples = []
        seen_posts = set()
        for pub_id in ranked:
            post_id = pub_post[pub_id]
            if post_id in seen_posts:
                continue
            samples.append({'publication_id': pub_id, 'post_id': post_id,
                            'reviewed_at': reviewed[post_id].isoformat(timespec='seconds')})
            seen_posts.add(post_id)
            if len(samples) == 3:
                break
        result['approved_sample_refs'] = samples
    return result
