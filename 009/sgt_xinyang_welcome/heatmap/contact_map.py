"""Update 033 — Read-only Xinyang Contacts geographic snapshot.

Update 036 enriches Contact points with their CURRENT CRM Stage 5/6 Deals.
Update 039 makes one map point = one Company: a Person (or sub-contact) that
shares the Company's location is merged into the Company's point through the
standard Odoo field ``commercial_partner_id``. Only Contacts located within
GROUP_RADIUS_KM of the Company's point are merged; a Person at a clearly
different place keeps its own point. Deals of every merged Contact are summed
on the point, so no Deal is dropped or counted twice. Each Odoo model uses the
current Xinyang user, never sudo/write/geocoding.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Any

from .adapter import OdooError, OdooGateway, OdooSession

PAGE_SIZE = 800
MAX_CONTACTS = 40000
MAX_STAGE_DEALS = 30000
GROUP_RADIUS_KM = 1.0
MAX_MEMBERS_SHOWN = 60
STAGE_NAMES = {"mm": "5.Match Making", "approved": "6.Approved Match Making"}
CACHE_SECONDS = 360
_lock = threading.RLock()
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class ContactMapError(ValueError):
    pass


def valid_pair(latitude: object, longitude: object) -> bool:
    """Accept finite earth coordinates, excluding Odoo's 0,0 missing markers."""
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        return False
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180 and lat != 0 and lon != 0


def _short(value: object, length: int = 180) -> str:
    return str(value or '')[:length]


def _relation_name(value: object) -> str:
    return _short(value[1] if isinstance(value, (list, tuple)) and len(value) >= 2 else '', 100)


def _positive_id(value: object) -> int | None:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _distance_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def _group_contacts(contacts: list[dict[str, Any]], enabled: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge co-located Contacts of one commercial entity into one map point.

    ``contacts`` are individual Contacts that already have valid coordinates.
    The point id is the commercial entity id (the Company, or the Contact itself
    when it has no parent). Coordinates come from the Company when it has them,
    otherwise from its lowest-id Contact. A Contact farther than GROUP_RADIUS_KM
    from that anchor is never hidden: it starts another point.
    """
    buckets: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for contact in contacts:
        key = contact['cid'] if enabled else contact['id']
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(contact)
    points: list[dict[str, Any]] = []
    index: dict[str, Any] = {'member': {}, 'entity': {}, 'resolve': enabled}
    for key in order:
        remaining = sorted(buckets[key], key=lambda c: (c['id'] != key, c['id']))
        first = True
        while remaining:
            anchor = remaining[0]
            members = [c for c in remaining if c is anchor or _distance_km(
                anchor['lat'], anchor['lon'], c['lat'], c['lon']) <= GROUP_RADIUS_KM]
            remaining = [c for c in remaining if not any(c is m for m in members)]
            point_id = key if first else anchor['id']
            self_row = next((m for m in members if m['id'] == point_id), None)
            base = self_row or anchor
            parent_root = bool(enabled and first and any(m['id'] != key for m in members))
            name = (self_row['name'] if self_row else
                    (anchor['cname'] if enabled and first and anchor.get('cname') else anchor['name']))
            ordered = sorted(members, key=lambda m: (m['id'] != point_id, str(m['name']).casefold(), m['id']))
            shown = [{'id': m['id'], 'name': m['name'], 'company': m['company'], 'archived': m['archived'],
                      'mm_deals': 0, 'approved_deals': 0} for m in ordered[:MAX_MEMBERS_SHOWN]]
            point = {'id': point_id, 'name': _short(name), 'lat': base['lat'], 'lon': base['lon'],
                     'company': bool(any(m['company'] for m in members) or parent_root),
                     'city': base['city'], 'country': base['country'],
                     'archived': bool(self_row['archived'] if self_row else all(m['archived'] for m in members)),
                     'contacts': len(members), 'members': shown,
                     'members_more': max(0, len(members) - len(shown)),
                     'unlisted_deals': 0, 'mm_deals': 0, 'approved_deals': 0}
            points.append(point)
            for position, m in enumerate(ordered):
                index['member'][m['id']] = (point, shown[position] if position < len(shown) else None)
            if first:
                index['entity'][key] = point
            first = False
    return points, index


def _commercial_ids(gateway: OdooGateway, session: OdooSession, partner_ids: list[int]) -> dict[int, int]:
    """Resolve the commercial entity of Deal partners that are not map members."""
    resolved: dict[int, int] = {}
    ids = sorted(set(partner_ids))
    for start in range(0, len(ids), PAGE_SIZE):
        chunk = ids[start:start + PAGE_SIZE]
        rows = gateway.call(session, 'res.partner', 'read', [chunk, ['commercial_partner_id']],
                            {'context': {'active_test': False}})
        if not isinstance(rows, list):
            raise ContactMapError('Odoo trả danh sách Company của Contact không hợp lệ.')
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), int):
                raise ContactMapError('Odoo trả Company của Contact không hợp lệ.')
            cid = _positive_id(row.get('commercial_partner_id'))
            if cid is not None:
                resolved[row['id']] = cid
    return resolved


def _crm_stages(gateway: OdooGateway, session: OdooSession, points: list[dict[str, Any]],
                index: dict[str, Any] | None = None) -> dict[str, Any]:
    """Decorate map points with CURRENT stage matches, including multiple Deals.

    A Deal is credited to the point that contains its Contact (Update 039: the
    Company point). Deals of Contacts without coordinates are credited to their
    Company's point when that point exists; otherwise they are ignored as before.

    No fuzzy stage matching or historical Chatter counts. Search/read all calls use
    the current user's ACL and record rules; nothing is created or modified.
    """
    stage_rows = gateway.call(session, 'crm.stage', 'search_read',
                              [[('name', 'in', list(STAGE_NAMES.values()))]],
                              {'fields': ['id', 'name'], 'limit': 100})
    if not isinstance(stage_rows, list):
        raise ContactMapError('Không đọc được danh sách Stage CRM Xinyang.')
    by_kind: dict[str, set[int]] = {'mm': set(), 'approved': set()}
    for stage in stage_rows:
        if not isinstance(stage, dict) or not isinstance(stage.get('id'), int):
            raise ContactMapError('Odoo trả thông tin Stage CRM không hợp lệ.')
        for kind, name in STAGE_NAMES.items():
            if str(stage.get('name') or '').strip() == name:
                by_kind[kind].add(stage['id'])
    missing = [name for kind, name in STAGE_NAMES.items() if not by_kind[kind]]
    if missing:
        raise ContactMapError('Không tìm thấy Stage CRM đúng tên: ' + ', '.join(missing))

    lookup = {sid: kind for kind, ids in by_kind.items() for sid in ids}
    # The target stages contain relatively few Deals; query only these stages,
    # then match partner_id against mapped Contact IDs in local memory. Avoid
    # constructing a huge list of Contact IDs inside the Odoo RPC domain.
    domain = [[('stage_id', 'in', sorted(lookup))]]
    count = gateway.call(session, 'crm.lead', 'search_count', domain)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > MAX_STAGE_DEALS:
        raise ContactMapError('Số Deal trong Stage 5/6 vượt giới hạn kiểm tra an toàn.')
    if index is None:
        index = {'member': {p['id']: (p, None) for p in points}, 'entity': {p['id']: p for p in points}, 'resolve': False}
    for point in points:
        point['mm_deals'] = 0
        point['approved_deals'] = 0
        point['unlisted_deals'] = 0
        for member in point.get('members', []):
            member['mm_deals'] = 0
            member['approved_deals'] = 0
    pending: dict[int, dict[str, int]] = {}
    seen: set[int] = set()
    offset = 0
    while offset < count:
        rows = gateway.call(session, 'crm.lead', 'search_read', domain, {
            'fields': ['id', 'partner_id', 'stage_id'], 'offset': offset,
            'limit': min(PAGE_SIZE, count - offset), 'order': 'id asc',
        })
        if not isinstance(rows, list) or not rows:
            raise ContactMapError('Không đọc đủ Deal ở Stage 5/6; chưa xác minh phân loại.')
        for deal in rows:
            if not isinstance(deal, dict) or not isinstance(deal.get('id'), int) or deal['id'] in seen:
                raise ContactMapError('Danh sách Deal của Stage 5/6 bị trùng hoặc không hợp lệ.')
            seen.add(deal['id'])
            stage = deal.get('stage_id')
            partner = deal.get('partner_id')
            sid = stage[0] if isinstance(stage, (list, tuple)) and stage else stage
            pid = partner[0] if isinstance(partner, (list, tuple)) and partner else partner
            kind = lookup.get(sid)
            if not kind or isinstance(pid, bool) or not isinstance(pid, int):
                continue
            hit = index['member'].get(pid)
            if hit:
                point, member = hit
                point[kind + '_deals'] += 1
                if member is not None:
                    member[kind + '_deals'] += 1
            elif index.get('resolve'):
                pending.setdefault(pid, {'mm': 0, 'approved': 0})[kind] += 1
        offset += len(rows)
        if offset > count:
            raise ContactMapError('Số Deal thay đổi trong lúc tải, hãy Reset.')
    if offset != count:
        raise ContactMapError('Chưa đọc đủ Deal Stage 5/6.')
    if pending:
        resolved = _commercial_ids(gateway, session, list(pending))
        for pid, counts in pending.items():
            point = index['entity'].get(resolved.get(pid))
            if point is not None:
                point['mm_deals'] += counts['mm']
                point['approved_deals'] += counts['approved']
                point['unlisted_deals'] += counts['mm'] + counts['approved']
    mm_contacts = sum(p['mm_deals'] > 0 for p in points)
    approved_contacts = sum(p['approved_deals'] > 0 for p in points)
    both_contacts = sum(p['mm_deals'] > 0 and p['approved_deals'] > 0 for p in points)
    return {'available': True, 'reason': '', 'matched_deals': sum(p['mm_deals'] + p['approved_deals'] for p in points),
            'mm_contacts': mm_contacts, 'approved_contacts': approved_contacts,
            'both_contacts': both_contacts,
            'mm_deals': sum(p['mm_deals'] for p in points),
            'approved_deals': sum(p['approved_deals'] for p in points)}


def _snapshot(gateway: OdooGateway, session: OdooSession) -> dict[str, Any]:
    # Standard search_read enforces Odoo ACL and record rules for this exact user.
    available = gateway.fields(session, 'res.partner')
    required = {'name', 'partner_latitude', 'partner_longitude'}
    missing = required.difference(available)
    if missing:
        raise ContactMapError('Contacts chưa có field cần thiết: ' + ', '.join(sorted(missing)))

    extras = [f for f in ('is_company','city','country_id','active','commercial_partner_id') if f in available]
    # Update 039: one Company = one map point. Without the standard field the map falls back to one Contact per point.
    grouping = 'commercial_partner_id' in available
    fields = ['id'] + sorted(required) + extras
    # Include active and archived as the user explicitly requested ALL Contacts;
    # still subject to current user's Odoo ACL and record rules.
    ctx = {'active_test': False}
    query = [[('partner_latitude','!=',0.0),('partner_longitude','!=',0.0)]]
    total = gateway.call(session, 'res.partner', 'search_count', [[]], {'context': ctx})
    candidate_count = gateway.call(session, 'res.partner', 'search_count', query, {'context': ctx})
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ContactMapError('Odoo trả tổng Contacts không hợp lệ.')
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int) or candidate_count < 0 or candidate_count > total:
        raise ContactMapError('Odoo trả số Contacts có tọa độ không hợp lệ.')
    if candidate_count > MAX_CONTACTS:
        raise ContactMapError(f'Có {candidate_count} Contacts có tọa độ; vượt giới hạn an toàn {MAX_CONTACTS}. Chưa tải bản đồ để tránh lấy thiếu dữ liệu.')

    contacts: list[dict[str, Any]] = []
    bad_coordinates = 0
    seen_ids: set[int] = set()
    offset = 0
    while offset < candidate_count:
        rows = gateway.call(session, 'res.partner', 'search_read', query, {
            'fields': fields, 'offset': offset, 'limit': min(PAGE_SIZE, candidate_count-offset),
            'order': 'id asc', 'context': ctx,
        })
        if not isinstance(rows, list) or not rows:
            raise ContactMapError('Odoo trả thiếu trang dữ liệu Contacts; không hiển thị thống kê chưa đầy đủ.')
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), int) or row['id'] in seen_ids:
                raise ContactMapError('Contacts có ID bị trùng hoặc không hợp lệ trong lần đọc.')
            seen_ids.add(row['id'])
            lat, lon = row.get('partner_latitude'), row.get('partner_longitude')
            if not valid_pair(lat, lon):
                bad_coordinates += 1
                continue
            own_name = _short(row.get('name') or f'Contact #{row["id"]}')
            cid = _positive_id(row.get('commercial_partner_id')) if grouping else None
            ref = row.get('commercial_partner_id')
            cname = _short(ref[1]) if grouping and cid and isinstance(ref, (list, tuple)) and len(ref) >= 2 else ''
            contacts.append({'id': row['id'], 'name': own_name,
                             'lat': float(lat), 'lon': float(lon),
                             'company': bool(row.get('is_company')),
                             'city': _short(row.get('city'), 100),
                             'country': _relation_name(row.get('country_id')),
                             'archived': row.get('active') is False,
                             'cid': cid or row['id'], 'cname': cname})
        offset += len(rows)
        if offset > candidate_count:
            raise ContactMapError('Số Contacts thay đổi khi đang tải dữ liệu, vui lòng Reset.')
    if offset != candidate_count:
        raise ContactMapError('Chưa đọc đủ số Contact có tọa độ, vui lòng Reset.')

    points, group_index = _group_contacts(contacts, grouping)

    # Stage information is optional. If CRM rights, names or paging are not
    # confirmed, DO NOT turn unknown into zero. Contacts remain visible and the
    # stage filters become unavailable until permissions/data are fixed.
    try:
        stage_info = _crm_stages(gateway, session, points, group_index)
    except Exception as exc:
        for point in points:
            point['mm_deals'] = None
            point['approved_deals'] = None
            point['unlisted_deals'] = None
            for member in point.get('members', []):
                member['mm_deals'] = None
                member['approved_deals'] = None
        detail = str(exc).strip()
        stage_info = {'available': False,
                      'reason': ('Chưa xác minh được Stage CRM qua tài khoản hiện tại. '
                                 + (detail[:220] if detail else 'Kiểm tra quyền đọc CRM và tên Stage.')),
                      'mm_contacts': None, 'approved_contacts': None,
                      'both_contacts': None, 'matched_deals': None,
                      'mm_deals': None, 'approved_deals': None}

    merged = len(contacts) - len(points)
    return {'source': 'xinyang.res.partner',
            'basis': 'one_company_one_point' if grouping else 'one_contact_one_point',
            'total': total, 'candidates': candidate_count, 'mapped': len(points),
            'contacts_mapped': len(contacts), 'merged': merged,
            'grouping': {'available': grouping, 'rule': 'commercial_partner_id' if grouping else 'none',
                         'radius_km': GROUP_RADIUS_KM, 'contacts': len(contacts),
                         'points': len(points), 'merged': merged},
            'missing': total - candidate_count, 'invalid': bad_coordinates,
            'points': points, 'stage': stage_info, 'complete': True,
            'note': 'Đọc cả Contact đã lưu trữ; chỉ hiển thị record được tài khoản Odoo hiện tại phép đọc. Không lọc theo kỳ báo cáo.'
                    + (' Mỗi Company là một điểm: Person cùng vị trí (trong ' + str(GROUP_RADIUS_KM).rstrip('0').rstrip('.') + ' km) được gộp vào Company.' if grouping else '')}


def contact_map(gateway: OdooGateway, session: OdooSession, *, force: bool = False) -> dict[str, Any]:
    token = session.token
    now = time.monotonic()
    if not force:
        with _lock:
            hit = _cache.get(token)
            if hit and hit[0] > now:
                return hit[1]
    result = _snapshot(gateway, session)
    with _lock:
        # Prevent one user session from exposing cached results to another.
        if len(_cache) > 200:
            for k, (exp, _) in list(_cache.items()):
                if exp < now: _cache.pop(k, None)
        _cache[token] = (time.monotonic() + CACHE_SECONDS, result)
    return result


def forget_contact_map(token: str | None) -> None:
    if token:
        with _lock:
            _cache.pop(token, None)


# Update 092: on-demand profile behind the existing authenticated Xinyang Odoo gateway.
# No new database connection, no write, and no images downloaded for map markers.
def contact_map_profile(gateway: OdooGateway, session: OdooSession, contact_id: int) -> dict[str, Any]:
    if isinstance(contact_id, bool) or not isinstance(contact_id, int) or contact_id <= 0:
        raise ContactMapError('Contact ID không hợp lệ.')
    descriptions = gateway.fields_get(session, 'res.partner')
    if not isinstance(descriptions, dict):
        raise ContactMapError('Không đọc được cấu trúc Contact.')
    import unicodedata
    def clean(s):
        return ''.join(ch for ch in unicodedata.normalize('NFD', str(s or '').lower()) if unicodedata.category(ch) != 'Mn').strip()
    # Optional custom fields are resolved from Odoo's real field definitions.
    # Deliberately do not assume a technical x_ field name.
    desired = {
        'business_type': ('business type', 'loai hinh kinh doanh'),
        'main_market': ('main market', 'thi truong chinh'),
        'employee_size': ('employee size', 'quy mo nhan su'),
        'business_industries': ('business industries', 'nganh nghe kinh doanh'),
        'founded_year': ('founded year', 'nam thanh lap'),
        'yellow_pages': ('yellow pages', 'trang vang'),
    }
    resolved = {}
    accepted_types = {'char', 'text', 'html', 'integer', 'float', 'selection', 'many2one'}
    # Update 097: tên kỹ thuật của CRM-007 (res.partner) được ưu tiên; chỉ khi không có mới dò theo nhãn.
    technical = {
        'business_type': ('x_type_contact',), 'main_market': ('x_country',),
        'employee_size': ('x_yp_employee_range',), 'business_industries': ('x_fb_industry',),
        'founded_year': ('x_yp_founded_year',), 'yellow_pages': ('x_yp_listing_url',),
    }
    for key, labels in desired.items():
        direct = [f for f in technical.get(key, ()) if isinstance(descriptions.get(f), dict)
                  and descriptions[f].get('type') in accepted_types]
        if direct:
            resolved[key] = direct[0]
            continue
        matches = [field for field, meta in descriptions.items() if isinstance(meta, dict)
                   and meta.get('type') in accepted_types and clean(meta.get('string')) in labels]
        if len(matches) == 1:
            resolved[key] = matches[0]
    standard = ('name','is_company','phone','mobile','email','website','vat',
                'street','street2','city','state_id','country_id','zip',
                'partner_latitude','partner_longitude','category_id','image_128','image_1920')
    available = [v for v in standard if v in descriptions]
    fields = list(dict.fromkeys(available + list(resolved.values())))
    rows = gateway.call(session, 'res.partner', 'read', [[contact_id], fields],
                        {'context': {'active_test': False}})
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get('id') != contact_id:
        raise ContactMapError('Không tìm thấy Contact hoặc không có quyền xem.')
    r = rows[0]
    def value(field):
        raw = r.get(field)
        if isinstance(raw, (list, tuple)):
            return str(raw[1]) if len(raw) > 1 and isinstance(raw[1], str) else ''
        if raw is False or raw is None:
            return ''
        meta = descriptions.get(field, {})
        if meta.get('type') == 'selection':
            return next((str(label) for code, label in meta.get('selection', []) if code == raw), str(raw))
        if meta.get('type') == 'html':
            # Strip markup from the text-only profile view; no HTML from Odoo is injected in the browser.
            import re
            return re.sub(r'<[^>]*>', ' ', str(raw)).strip()[:2500]
        return str(raw)[:2500]
    profile = {key: value(field) for key, field in resolved.items()}
    for field in available:
        if field not in ('image_128', 'image_1920', 'category_id'):
            profile[field] = value(field)
    profile['contact_id'] = contact_id
    profile['field_mapping'] = resolved
    # Image is returned only on explicitly requested detail, not on every map snapshot.
    pic = r.get('image_128') or r.get('image_1920')
    if isinstance(pic, str) and len(pic) <= 700_000:
        import base64
        try:
            binary = base64.b64decode(pic, validate=True)
            if binary.startswith(b'\x89PNG\r\n\x1a\n'):
                mime = 'image/png'
            elif binary.startswith(b'\xff\xd8\xff'):
                mime = 'image/jpeg'
            elif binary.startswith(b'GIF8'):
                mime = 'image/gif'
            elif binary.startswith(b'RIFF') and binary[8:12] == b'WEBP':
                mime = 'image/webp'
            else:
                mime = None
            if mime:
                profile['logo'] = 'data:' + mime + ';base64,' + pic
        except (ValueError, base64.binascii.Error):
            pass
    # The selected map point represents a Contact/company, not necessarily one Deal.
    # Explicitly enumerate linked deals so the user selects the exact stage, never
    # display an aggregate Company MM count as if it were a Deal's stage.
    lead_fields = gateway.fields(session, 'crm.lead')
    # Update 097: ngoài Stage, đọc thêm các cột liên hệ/địa chỉ của Deal để bù chỗ Contact còn trống.
    extra_lead = ('phone', 'x_phone', 'x_mobilephone', 'email_from', 'website', 'referred',
                  'street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    base_lead = ('id', 'name', 'stage_id', 'partner_id')
    search_fields = [f for f in base_lead if f in lead_fields]
    deals = []
    deal_rows = []
    if len(search_fields) == 4:
        search_fields += [f for f in extra_lead if f in lead_fields]
        deal_rows = gateway.call(session, 'crm.lead', 'search_read',
                                 [[('partner_id', 'child_of', contact_id)]],
                                 {'fields': search_fields, 'limit': 101, 'order': 'id desc',
                                  'context': {'active_test': False}})
        if isinstance(deal_rows, list):
            for d in deal_rows[:100]:
                if isinstance(d, dict) and isinstance(d.get('id'), int):
                    deals.append({'id': d['id'], 'name': _short(d.get('name'), 200),
                                  'stage': _relation_name(d.get('stage_id')) or 'Chưa có Stage',
                                  'partner_id': _positive_id(d.get('partner_id'))})
            profile['deals_truncated'] = len(deal_rows) > 100
        else:
            deal_rows = []
    profile['deals'] = deals
    _fill_profile_gaps(gateway, session, contact_id, descriptions, profile,
                       [d for d in deal_rows[:100] if isinstance(d, dict)])
    return profile


def _text_value(raw: Any) -> str:
    if isinstance(raw, (list, tuple)):
        return str(raw[1]).strip() if len(raw) > 1 and isinstance(raw[1], str) else ''
    if raw is False or raw is None:
        return ''
    return str(raw).strip()[:500]


def _fill_profile_gaps(gateway, session, contact_id, descriptions, profile, deal_rows) -> None:
    """Update 097. Contact công ty thường để trống điện thoại/email/…, dữ liệu nằm ở Contact con (người)
    hoặc ở Deal. Thứ tự bù: Contact → Contact con → Deal liên kết (mới nhất trước). Chỉ ĐỌC, không ghi,
    không bịa. Điện thoại và Di động gộp thành MỘT số (`phone_any`): ưu tiên điện thoại, rồi di động.
    """
    notes: dict[str, str] = {}
    own_phone = profile.get('phone') or profile.get('mobile') or ''
    children: list[dict[str, Any]] = []
    child_fields = [f for f in ('name', 'phone', 'mobile', 'email', 'function') if f in descriptions]
    if child_fields and ('parent_id' in descriptions):
        try:
            rows = gateway.call(session, 'res.partner', 'search_read',
                                [[('parent_id', '=', contact_id)]],
                                {'fields': child_fields, 'limit': 20, 'order': 'id asc',
                                 'context': {'active_test': False}})
            children = [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
        except Exception:      # đọc bù là phụ; lỗi quyền không được làm hỏng cả hồ sơ
            children = []

    def first(rows, keys):
        for r in rows:
            for k in keys:
                v = _text_value(r.get(k))
                if v:
                    return v
        return ''

    phone = own_phone
    if not phone:
        phone = first(children, ('phone', 'mobile'))
        if phone:
            notes['phone'] = 'Contact con'
    if not phone:
        phone = first(deal_rows, ('phone', 'x_phone', 'x_mobilephone'))
        if phone:
            notes['phone'] = 'Deal liên kết'
    profile['phone_any'] = phone

    if not profile.get('email'):
        v = first(children, ('email',))
        if v:
            profile['email'], notes['email'] = v, 'Contact con'
        else:
            v = first(deal_rows, ('email_from',))
            if v:
                profile['email'], notes['email'] = v, 'Deal liên kết'
    for key, lead_key in (('website', 'website'), ('yellow_pages', 'referred')):
        if not profile.get(key):
            v = first(deal_rows, (lead_key,))
            if v:
                profile[key], notes[key] = v, 'Deal liên kết'
    # Địa chỉ: chỉ bù ô còn trống bằng Deal CÙNG địa chỉ (cùng Street hoặc cùng City), không trộn địa chỉ khác nhau.
    def norm(x):
        return ' '.join(_text_value(x).lower().split())
    for d in deal_rows:
        same = (not profile.get('street') and not profile.get('city')) \
            or (norm(d.get('street')) and norm(d.get('street')) == norm(profile.get('street'))) \
            or (norm(d.get('city')) and norm(d.get('city')) == norm(profile.get('city')))
        if not same:
            continue
        got = False
        for key in ('street', 'street2', 'city', 'state_id', 'zip', 'country_id'):
            if not profile.get(key):
                v = _text_value(d.get(key))
                if v:
                    profile[key], notes[key] = v, 'Deal liên kết'
                    got = True
        if got:
            break
    # Người phụ trách (nếu có) để người xem biết số/email đó của ai
    person = next((r for r in children if _text_value(r.get('name'))
                   and any(_text_value(r.get(k)) for k in ('phone', 'mobile', 'email'))), None)
    if person and any(k in notes for k in ('phone', 'email')) and 'Contact con' in notes.values():
        profile['contact_person'] = _text_value(person.get('name'))
    profile['gap_sources'] = notes


# Update 093: independent CRM-lead coordinate snapshot, using the SAME authenticated
# Odoo gateway/session as Contact Heat Map. No new connection or geocoding.
MAX_CRM_LEADS = 60000

def crm_lead_map(gateway: OdooGateway, session: OdooSession) -> dict[str, Any]:
    available = gateway.fields(session, 'crm.lead')
    required = {'name', 'stage_id', 'x_yp_latitude', 'x_yp_longitude'}
    absent = required - set(available)
    if absent:
        raise ContactMapError('CRM chưa có field cần thiết: ' + ', '.join(sorted(absent)) + '. Cần cập nhật CRM-005 Update 047.')
    optional = ['partner_id', 'partner_name', 'contact_name', 'phone', 'email_from', 'city',
                'country_id', 'active', 'x_yp_geo_status', 'x_yp_geo_updated_at']
    fields = sorted(required) + [name for name in optional if name in available]
    ctx = {'active_test': False}
    domain = []
    candidate_domain = [('x_yp_latitude', '!=', 0), ('x_yp_longitude', '!=', 0)]
    total = gateway.call(session, 'crm.lead', 'search_count', [domain], {'context': ctx})
    candidates = gateway.call(session, 'crm.lead', 'search_count', [candidate_domain], {'context': ctx})
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (total, candidates)) or candidates > total:
        raise ContactMapError('Không xác minh được số Deal CRM.')
    if candidates > MAX_CRM_LEADS:
        raise ContactMapError(f'Có {candidates} Deal CRM có tọa độ; vượt giới hạn an toàn {MAX_CRM_LEADS}.')
    points, seen, invalid = [], set(), 0
    offset = 0
    while offset < candidates:
        rows = gateway.call(session, 'crm.lead', 'search_read', [candidate_domain], {
            'fields': fields, 'offset': offset, 'limit': min(PAGE_SIZE, candidates-offset),
            'order': 'id asc', 'context': ctx,
        })
        if not isinstance(rows, list) or not rows:
            raise ContactMapError('Odoo chưa trả đủ danh sách Deal CRM.')
        for r in rows:
            did = r.get('id') if isinstance(r, dict) else None
            if isinstance(did, bool) or not isinstance(did, int) or did <= 0 or did in seen:
                raise ContactMapError('ID Deal CRM không hợp lệ hoặc bị trùng.')
            seen.add(did)
            lat, lon = r.get('x_yp_latitude'), r.get('x_yp_longitude')
            if not valid_pair(lat, lon):
                invalid += 1
                continue
            stage = _relation_name(r.get('stage_id')) or 'Chưa xác định Stage'
            norm = stage.strip().casefold()
            mm = int(norm in ('5.match making', '8.match making'))
            approved = int(norm in ('6.approved match making', '9.approved match making'))
            partner = _positive_id(r.get('partner_id'))
            points.append({
                'id': -did, 'deal_id': did, 'partner_id': partner,
                'name': _short(r.get('name') or f'Deal #{did}'), 'lat': float(lat), 'lon': float(lon),
                'company': True, 'city': _short(r.get('city'), 100),
                'country': _relation_name(r.get('country_id')), 'archived': r.get('active') is False,
                'contacts': 1, 'members': [], 'members_more': 0, 'unlisted_deals': 0,
                'mm_deals': mm, 'approved_deals': approved, 'stage': stage,
                'phone': _short(r.get('phone'), 80), 'email': _short(r.get('email_from'), 180),
                'partner_name': _relation_name(r.get('partner_id')) or _short(r.get('partner_name'), 180),
                'geo_status': _short(r.get('x_yp_geo_status'), 50),
                'geo_updated_at': _short(r.get('x_yp_geo_updated_at'), 50),
            })
        offset += len(rows)
        if offset > candidates:
            raise ContactMapError('Số Deal CRM thay đổi trong khi tải, hãy Reset.')
    if offset != candidates:
        raise ContactMapError('Chưa tải đủ Deal CRM theo phân trang.')
    mm_count = sum(bool(p['mm_deals']) for p in points)
    approved_count = sum(bool(p['approved_deals']) for p in points)
    return {
        'source': 'xinyang.crm.lead', 'basis': 'one_deal_one_point', 'total': total,
        'candidates': candidates, 'mapped': len(points), 'contacts_mapped': len(points),
        'missing': total-candidates, 'invalid': invalid, 'merged': 0, 'points': points,
        'grouping': {'available': False, 'points': len(points), 'contacts': len(points), 'merged': 0},
        'stage': {'available': True, 'reason': '', 'matched_deals': mm_count+approved_count,
                  'mm_contacts': mm_count, 'approved_contacts': approved_count,
                  'both_contacts': 0, 'mm_deals': mm_count, 'approved_deals': approved_count},
        'complete': True,
        'note': 'Mỗi marker là một Deal CRM có cặp x_yp_latitude / x_yp_longitude hợp lệ. '
                'Không định vị giả và không sửa thông tin Odoo. Bao gồm Deal lưu trữ theo quyền của tài khoản.'
    }
