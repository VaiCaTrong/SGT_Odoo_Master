"""Update_026: pure helpers for the system-wide Deal duplicate check (no Odoo import).

The functions here have no database access so they can be unit-tested offline.
The rules mirror the Chrome extension "SGT CRM Assistant" (normalizePhoneKey):
a phone is compared by its LAST 9 DIGITS, a tax code by its upper-case letters+digits.
"""
import math
import re
import threading
import time
from collections import deque

# Department whose members may update any Deal (kept as one constant, no new setting).
SALES_DEPARTMENT_NAME = 'Kinh doanh (MMC)'
# Update_027: the Sales right every yp_* function needs ("User: Own Documents Only"; "All Documents" and
# Sales "Administrator" include it, the Role Administrator does not).
SALES_USER_GROUP = 'sales_team.group_sale_salesman'

MAX_PHONE_KEYS = 20          # accepted from the caller
MAX_KEYS_TOTAL = 40          # after adding the numbers found in the Deal values
MAX_TEXT = 40                # longest accepted key / tax string
MAX_MATCHES = 50
CHECK_LIMIT = 30             # yp_duplicate_check calls per minute per user
CREATE_LIMIT_USER = 5        # yp_create_lead calls per minute per user
CREATE_LIMIT_ADMIN = 10
WINDOW_SECONDS = 60
LOCK_TIMEOUT = '10s'

# yp_duplicate_scan (Admin only, read only)
SCAN_MAX_BATCH = 2000        # Deals ("seeds") per scan call, hard cap
SCAN_LIMIT = 6               # scans per SCAN_WINDOW_SECONDS per user
SCAN_WINDOW_SECONDS = 600
PROBE_LIMIT = 30             # probe calls per minute per user
SCAN_MAX_MEMBERS = 50        # members returned per group
LOST_STAGE_NAME = 'mark lost'   # an active Deal sitting in a stage with this name counts as lost
STEP_RANK = {'data': 1, 'verified': 2, 'potential': 3}
# Columns of crm_lead read once by the scan, beside the phone / tax columns (missing ones are skipped).
SCAN_META_FIELDS = ('active', 'lost_reason_id', 'probability', 'stage_id', 'sgt_crm002_step',
                    'sgt_crm002_sale_funnel_id', 'sgt_crm002_sale_stage_id')

# Fields scanned for phone numbers (those missing on a given database are skipped).
PHONE_FIELDS = ('phone', 'mobile', 'x_phone', 'x_mobilephone', 'description', 'name')
HTML_FIELDS = ('description',)
TAX_FIELD = 'x_yp_tax_code'
# Fields of a Deal values dict that may carry the Deal's own phone numbers.
VALUE_PHONE_FIELDS = ('phone', 'x_phone', 'x_mobilephone')

# Fields the Extension may write when it updates a Deal (white list, handoff 3.3).
WRITE_FIELDS = (
    'name', 'partner_name', 'x_company', 'contact_name', 'x_firstname', 'x_lastname', 'function',
    'phone', 'x_phone', 'x_mobilephone', 'email_from', 'website',
    'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
    'x_yp_tax_code', 'x_yp_founded_year', 'x_yp_employee_range', 'x_type_contact', 'x_fb_industry',
    'x_country', 'referred', 'description', 'x_yp_intro_en', 'source_id', 'x_image',
    'x_product_details', 'x_yp_gallery_html', 'x_yp_partners_html',
)
READ_FIELDS = WRITE_FIELDS + ('id', 'sgt_crm002_funnel_id', 'sgt_crm002_step')
CREATE_EXTRA_FIELDS = ('user_id', 'type', 'sgt_crm002_funnel_id', 'tag_ids')
M2O_VALUE_FIELDS = ('state_id', 'country_id', 'source_id', 'user_id', 'sgt_crm002_funnel_id')

_PHONE_RE = re.compile(r'(?:\+?84|0)?[\d .()\-]{8,20}')
_TAG_RE = re.compile(r'<[^>]*>')
_NBSP_RE = re.compile(r'&nbsp;|&#160;', re.I)


def phone_key(value):
    """Last 9 digits of a phone number, or '' when it is not a plausible phone number."""
    s = re.sub(r'\D', '', value if isinstance(value, str) else '')
    if s.startswith('84') and len(s) >= 11:
        s = '0' + s[2:]
    if len(s) == 9:
        s = '0' + s
    return s[-9:] if 9 <= len(s) <= 11 else ''


def tax_key(value):
    return re.sub(r'[^0-9A-Za-z]', '', value if isinstance(value, str) else '').upper()


def phone_keys_in_text(text, html=False):
    """All phone keys found in a free text (HTML tags are removed first when html=True)."""
    if not text or not isinstance(text, str):
        return []
    if html:
        text = _NBSP_RE.sub(' ', _TAG_RE.sub(' ', text))
    found = []
    for m in _PHONE_RE.finditer(text):
        k = phone_key(m.group(0))
        if k and k not in found:
            found.append(k)
    return found


_SEP = '[ .()-]'
_HTML_SEP = '(?:[ .()-]|&nbsp;|&#160;|<[^>]*>)'


def key_regex(keys, html=False):
    """PostgreSQL regex finding any of `keys` (digit strings) with optional separators between the digits."""
    sep = (_HTML_SEP if html else _SEP) + '*'
    parts = []
    for k in keys:
        if not k.isdigit():
            raise ValueError('phone key must be digits')
        parts.append(sep.join(k))
    return '|'.join(parts)


def _dedupe(items):
    out = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def clean_inputs(phone_keys, tax_code, require_one=True):
    """Validate what the caller sent. Returns (keys, tax, error_message).

    require_one=False lets yp_create_lead accept empty lists because it also reads the numbers from
    the Deal values; a malformed argument is an error either way."""
    if phone_keys is None or phone_keys is False:
        phone_keys = []
    if not isinstance(phone_keys, (list, tuple)) or len(phone_keys) > MAX_PHONE_KEYS:
        return [], '', 'phone_keys phải là danh sách tối đa %d phần tử.' % MAX_PHONE_KEYS
    keys = []
    for item in phone_keys:
        if not isinstance(item, str) or len(item) > MAX_TEXT:
            return [], '', 'Mỗi phone_keys phải là chuỗi tối đa %d ký tự.' % MAX_TEXT
        keys.append(phone_key(item))
    if tax_code is None or tax_code is False:
        tax_code = ''
    if not isinstance(tax_code, str) or len(tax_code) > MAX_TEXT:
        return [], '', 'tax_code phải là chuỗi tối đa %d ký tự.' % MAX_TEXT
    keys, tax = _dedupe(keys), tax_key(tax_code)
    if require_one and not keys and not tax:
        return [], '', 'Cần ít nhất một số điện thoại hoặc mã số thuế hợp lệ.'
    return keys, tax, ''


def keys_from_values(vals):
    """Phone keys and tax code that the new Deal itself carries (server does not trust the caller only)."""
    keys = []
    for name in VALUE_PHONE_FIELDS:
        keys.extend(phone_keys_in_text(vals.get(name)))
    return _dedupe(keys), tax_key(vals.get(TAX_FIELD))


def lock_keys(keys, taxes):
    """Sorted advisory-lock names: one per phone key and per tax code (sorted = no deadlock)."""
    names = ['yp-phone-' + k for k in keys] + ['yp-tax-' + t for t in taxes if t]
    return sorted(set(names))


def stage_is_lost(name):
    """True for a stage that stands for "Mark Lost" (none exists on Xinyang today; kept for safety)."""
    return isinstance(name, str) and LOST_STAGE_NAME in name.lower()


def lead_state(active, lost_reason, probability, lost_stage=False):
    if active:
        return 'lost' if lost_stage else 'active'
    if lost_reason or probability == 0:
        return 'lost'
    return 'archived'


def place_rank(sale_funnel, sale_funnel_seq, sale_stage_seq, stage, stage_seq, step):
    """How far a Deal has gone, as (tier, a, b); bigger = further (user 02/11 09:10).

    Sale (New/Renew) beats Match Making beats Data Funnel.  Inside a tier: Sale = funnel then stage
    sequence; Match Making = stage sequence; Data Funnel = potential > verified > data.
    """
    if sale_funnel:
        return (3, sale_funnel_seq or 0, sale_stage_seq or 0)
    if stage:
        return (2, stage_seq or 0, 0)
    return (1, STEP_RANK.get(step, 0), 0)


def order_key(state, place, lead_id):
    """Ascending sort = furthest first: active Deals before lost/archived ones, then the furthest
    place, then the older (smaller) id."""
    return (0 if state == 'active' else 1, -place[0], -place[1], -place[2], lead_id)


def sort_key(match):
    place = place_rank(match.get('sale_funnel'), match.get('sale_funnel_seq'), match.get('sale_stage_seq'),
                       match.get('stage'), match.get('stage_seq'), match.get('step'))
    return order_key(match['state'], place, match['id'])


def m2o_id(value):
    return value[0] if value else False


def m2o_name(value):
    return value[1] if value else ''


def can_update_lead(is_admin, is_sales, owner_id, uid):
    """Per-Deal rule (user 02/11): Admin, the Kinh doanh (MMC) department, or the Deal's owner."""
    return bool(is_admin or is_sales or (owner_id and owner_id == uid))


def seq_of(mapping, value):
    """Sequence number of a many2one value, or None (Deal not there / unknown)."""
    rec_id = m2o_id(value)
    if not rec_id or not mapping:
        return None
    return mapping.get(rec_id)


def build_match(row, phone_hit, tax_hit, is_admin, is_sales, uid, company_field, seqs=None, lost_stage_ids=()):
    """Minimal, safe view of a Deal for the caller (never phone, e-mail or notes).

    seqs = {'stage': {id: sequence}, 'funnel': {...}, 'sale_stage': {...}} gives the column order numbers.
    """
    seqs = seqs or {}
    owner_id = m2o_id(row.get('user_id'))
    stage_id = m2o_id(row.get('stage_id'))
    state = lead_state(row.get('active'), row.get('lost_reason_id'), row.get('probability'),
                       bool(stage_id) and stage_id in lost_stage_ids)
    return {
        'id': row['id'],
        'name': row.get('name') or '',
        'company': (row.get(company_field) if company_field else '') or row.get('partner_name') or '',
        'owner_id': owner_id,
        'owner_name': m2o_name(row.get('user_id')),
        'phone': bool(phone_hit),
        'tax': bool(tax_hit),
        'funnel_id': m2o_id(row.get('sgt_crm002_funnel_id')),
        'funnel': m2o_name(row.get('sgt_crm002_funnel_id')),
        'step': row.get('sgt_crm002_step') or '',
        'stage': m2o_name(row.get('stage_id')),
        'stage_seq': seq_of(seqs.get('stage'), row.get('stage_id')),
        'sale_funnel': m2o_name(row.get('sgt_crm002_sale_funnel_id')),
        'sale_funnel_seq': seq_of(seqs.get('funnel'), row.get('sgt_crm002_sale_funnel_id')),
        'sale_stage': m2o_name(row.get('sgt_crm002_sale_stage_id')),
        'sale_stage_seq': seq_of(seqs.get('sale_stage'), row.get('sgt_crm002_sale_stage_id')),
        'state': state,
        'is_owner': bool(owner_id and owner_id == uid),
        'can_update': can_update_lead(is_admin, is_sales, owner_id, uid),
    }


def validate_values(vals, allowed, existing_fields):
    """Check a values dict from the caller. Returns an error message or ''."""
    if not isinstance(vals, dict) or not vals:
        return 'vals phải là dict không rỗng.'
    bad = sorted(k for k in vals if k not in allowed)
    if bad:
        return 'Field không được phép: %s.' % ', '.join(str(k) for k in bad)
    missing = sorted(k for k in vals if k not in existing_fields)
    if missing:
        return 'Field không tồn tại trên Odoo này: %s.' % ', '.join(missing)
    for key, value in vals.items():
        if key == 'tag_ids':
            if not _valid_tag_commands(value):
                return 'tag_ids chỉ nhận lệnh (4, id) hoặc (6, 0, [ids]).'
        elif key in M2O_VALUE_FIELDS:
            if value is not False and not _is_id(value):
                return '%s phải là số nguyên dương hoặc False.' % key
        elif not (value is None or isinstance(value, (str, bool, int, float))):
            return '%s có kiểu dữ liệu không hợp lệ.' % key
    return ''


def _is_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _valid_tag_commands(value):
    if not isinstance(value, (list, tuple)) or len(value) > 50:
        return False
    for cmd in value:
        if not isinstance(cmd, (list, tuple)) or not cmd:
            return False
        if cmd[0] == 4 and len(cmd) >= 2 and _is_id(cmd[1]):
            continue
        if cmd[0] == 6 and len(cmd) == 3 and isinstance(cmd[2], (list, tuple)) and all(_is_id(i) for i in cmd[2]):
            continue
        return False
    return True


class KeyGraph:
    """Deals joined by a shared phone key or tax code; a group = one connected component.

    A shares a phone with B and B shares a tax code with C  =>  A, B, C are one group.
    Pure Python (union-find), so the same code is tested offline and runs in Odoo.
    """

    def __init__(self):
        self.parent, self.first, self.count, self.keys = {}, {}, {}, {}

    def _find(self, x):
        parent = self.parent
        root = parent.setdefault(x, x)
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:                      # path compression
            parent[x], x = root, parent[x]
        return root

    def _union(self, a, b):
        ra, rb = self._find(a), self._find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)

    def add(self, lead_id, phone_keys, tax):
        """Register one Deal with the keys it carries (a Deal without keys is never in a group)."""
        keys = tuple(dict.fromkeys(['p' + k for k in phone_keys if k] + (['t' + tax] if tax else [])))
        if not keys:
            return
        self.keys[lead_id] = keys
        for k in keys:
            self.count[k] = self.count.get(k, 0) + 1
            other = self.first.setdefault(k, lead_id)
            if other != lead_id:
                self._union(other, lead_id)

    def groups(self):
        """[[lead ids]] of every connected component with at least two Deals."""
        by_root = {}
        for lead_id in list(self.parent):
            by_root.setdefault(self._find(lead_id), []).append(lead_id)
        return [sorted(ids) for ids in by_root.values() if len(ids) >= 2]

    def shares(self, lead_id):
        """(shares a phone with another Deal, shares a tax code with another Deal)."""
        phone = tax = False
        for k in self.keys.get(lead_id, ()):
            if self.count[k] >= 2:
                if k[0] == 'p':
                    phone = True
                else:
                    tax = True
        return phone, tax


def parse_scan_options(options):
    """Returns ({'probe', 'after_id', 'limit'}, error_message). Unknown keys are ignored."""
    if options is None:
        options = {}
    if not isinstance(options, dict):
        return None, 'options phải là dict.'
    probe = options.get('probe', False)
    if probe is None:
        probe = False
    if not isinstance(probe, bool):
        return None, 'probe phải là true hoặc false.'
    values = {}
    for key, default in (('after_id', 0), ('limit', SCAN_MAX_BATCH)):
        value = options.get(key, default)
        if value is None:
            value = default
        if isinstance(value, bool) or not isinstance(value, int):
            return None, '%s phải là số nguyên.' % key
        values[key] = value
    if values['after_id'] < 0:
        return None, 'after_id phải >= 0.'
    return {'probe': probe, 'after_id': values['after_id'],
            'limit': max(1, min(values['limit'], SCAN_MAX_BATCH))}, ''


class SlidingLimiter:
    """Per-process counter: at most `limit` hits per `window` seconds for each key.

    Only meant to stop a broken client from hammering the server; Odoo may run several
    processes, so the limit is approximate by design.
    """

    def __init__(self, limit, window=WINDOW_SECONDS, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self._hits, self._lock = {}, threading.Lock()

    def hit(self, key):
        """Register a call. Returns 0 when allowed, otherwise the seconds to wait."""
        now = self.clock()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return max(1, int(math.ceil(self.window - (now - q[0]))))
            q.append(now)
            if len(self._hits) > 5000:       # forget idle users
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
                    del self._hits[k]
            return 0


CHECK_LIMITER = SlidingLimiter(CHECK_LIMIT)
PROBE_LIMITER = SlidingLimiter(PROBE_LIMIT)
SCAN_LIMITER = SlidingLimiter(SCAN_LIMIT, SCAN_WINDOW_SECONDS)
