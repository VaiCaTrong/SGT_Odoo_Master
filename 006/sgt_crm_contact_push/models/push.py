"""Pure helpers of CRM-006 (no Odoo import, so they can be unit tested).

CRM-006 copies Deal (crm.lead) data into the Contact (res.partner) that the
existing "Create Contact" button created.

* Update_001: the NATIVE Contact fields (address, website, job, Tax ID, salesperson, reference, tags) are only
  FILLED WHEN EMPTY; what a user (or the old addon) already wrote is never overwritten.
* Update_002 (CRM-007 profile): the company-profile fields, the Vietnamese introduction (comment) and the logo
  fields are MIRRORED: every press of "Cập nhật Contact" updates them from the Deal. Empty Deal fields
  never erase Contact values. Update_003: the logo is mirrored ONLY to Company, never to the Person avatar.
"""

import re
import math

# Observable result fields written by the legacy Create Contact workflow.
# CRM-006 also watches partner_id attachment and guards with the existing
# x_sgt_crm_synced marker. The exact write order must be tested on Odoo.
TRIGGER_FIELDS = frozenset({'x_groupname', 'x_getfly_id'})

# Contact field -> label shown in the Chatter note.  ONE place to extend:
# CRM-007 only has to add the new Contact field here and in build_wanted().
LABELS = {
    'parent_id': 'Company',
    'street': 'Street',
    'street2': 'Street 2',
    'city': 'City',
    'zip': 'ZIP',
    'state_id': 'State',
    'country_id': 'Country',
    'website': 'Website',
    'function': 'Job Position',
    'vat': 'Tax ID',
    'user_id': 'Salesperson',
    'ref': 'Internal Reference (VN Odoo ID)',
    'category_id': 'Tags',
    'name': 'Name',
    # Update_002 (profile shown by CRM-007)
    'x_type_contact': 'Business Type',
    'x_country': 'Main Market',
    'x_yp_employee_range': 'Employee Size',
    'x_fb_industry': 'Business Industries',
    'x_url_zalo_group': 'Link Zalo Group',
    'x_url_fb_profile': 'Link Profile',
    'x_group_link': 'Group URL',
    'x_group_post_link': 'Post URL',
    'x_yp_founded_year': 'Founded Year',
    'x_yp_listing_url': 'Yellow Pages Link',
    'x_yp_intro_en': 'Company Introduction (English)',
    'x_yp_gallery_html': 'Image Gallery',
    'x_yp_partners_html': 'Partners',
    'comment': 'Company Introduction (Vietnamese)',
    'image_1920': 'Company Logo',
    'Geolocation': 'Geolocation (tọa độ)',
    'partner_latitude': 'Latitude',
    'partner_longitude': 'Longitude',
    'GeoProtectedContact': 'Contact coordinates preserved; use Cập nhật Contact to replace with Deal coordinates',
    'GeoProtectedCompany': 'Company coordinates preserved; use Cập nhật Contact to replace with Deal coordinates',
    'email': 'Email',
    'phone': 'Phone',
}

# Deal field -> Contact field, MIRRORED (Update_002).  Tax Code is NOT here: it is the native Tax ID (vat) and
# keeps the fill-empty rule of Update_001.
PROFILE_MAP = (
    ('x_type_contact', 'x_type_contact'),
    ('x_country', 'x_country'),
    ('x_yp_employee_range', 'x_yp_employee_range'),
    ('x_fb_industry', 'x_fb_industry'),
    ('x_url_zalo_group', 'x_url_zalo_group'),
    ('x_url_fb_profile', 'x_url_fb_profile'),
    ('x_group_link', 'x_group_link'),
    ('x_group_post_link', 'x_group_post_link'),
    ('x_yp_founded_year', 'x_yp_founded_year'),
    ('referred', 'x_yp_listing_url'),
    ('x_yp_intro_en', 'x_yp_intro_en'),
    ('x_yp_gallery_html', 'x_yp_gallery_html'),
    ('x_yp_partners_html', 'x_yp_partners_html'),
    ('description', 'comment'),
)
HTML_TARGETS = frozenset({'x_yp_intro_en', 'x_yp_gallery_html', 'x_yp_partners_html', 'comment'})
INT_TARGETS = frozenset({'x_yp_founded_year'})
LOGO_FIELD = 'image_1920'
SYNC_FLAG = 'x_sgt_crm_synced'   # sync marker; Person avatar is separately managed in CRM-007 Update_002

# Address fields shared by the Contact and the Company created for it.
ADDRESS_FIELDS = ('street', 'street2', 'city', 'zip', 'state_id', 'country_id')


def norm(text):
    """Comparison key: trimmed, single spaces, case-insensitive."""
    return re.sub(r'\s+', ' ', (text or '').strip()).casefold()


def like_pattern(text):
    """'Công  Ty TNHH' -> 'Công%Ty%TNHH': an ilike pattern that survives double
    spaces; the exact comparison is done afterwards with norm()."""
    return '%'.join((text or '').split())


def clean(value):
    """Trimmed text or '' (False / None / 0 / spaces -> '')."""
    if isinstance(value, str):
        return value.strip()
    return ''


def collapse_repeated_name(name):
    """'Mr. Chinh Mr. Chinh' -> 'Mr. Chinh'.

    Only a phrase of at least 2 words repeated twice is collapsed, so a real
    one-word double name ("Bình Bình") is left alone.
    """
    words = (name or '').split()
    if len(words) >= 4 and len(words) % 2 == 0:
        half = len(words) // 2
        if [w.casefold() for w in words[:half]] == [w.casefold() for w in words[half:]]:
            return ' '.join(words[:half])
    return name


def first_text(*values):
    """First non-empty text among the values."""
    for value in values:
        text = clean(value)
        if text:
            return text
    return ''


def unique_names(names):
    """Tag names without duplicates (case-insensitive) in first-seen order."""
    seen, out = set(), []
    for name in names or ():
        text = clean(name)
        key = norm(text)
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def build_wanted(lead):
    """Deal data (plain dict) -> wanted Contact values (only non-empty ones).

    lead keys: street, street2, city, zip, state_id(int|False), country_id,
    website, x_website, function, x_jobtitle, x_yp_tax_code, user_id(int),
    x_getfly_id, tag_names(list).
    """
    wanted = {}
    for key in ('street', 'street2', 'city', 'zip'):
        text = clean(lead.get(key))
        if text:
            wanted[key] = text
    for key in ('state_id', 'country_id', 'user_id'):
        if lead.get(key):
            wanted[key] = int(lead[key])
    website = first_text(lead.get('website'), lead.get('x_website'))
    if website:
        wanted['website'] = website
    function = first_text(lead.get('function'), lead.get('x_jobtitle'))
    if function:
        wanted['function'] = function
    vat = clean(lead.get('x_yp_tax_code'))
    if vat:
        wanted['vat'] = vat
    ref = clean(lead.get('x_getfly_id'))
    if ref:
        wanted['ref'] = ref
    return wanted



def build_contact_channels(lead):
    """Contact's email and phone for the first complete push and explicit button.

    Do not map these values into an existing parent Company: the Deal's phone
    and email identify an individual interlocutor, not an organization-wide
    mailbox or telephone.  On a Deal linked DIRECTLY to a Company, that Company
    is the selected Contact and can receive them.

    Source priority follows native CRM fields, then matching legacy contact
    fields.  An entirely empty source never clears a previous Contact value.
    """
    out = {}
    email = first_text(lead.get('email_from'), lead.get('x_email01'))
    phone = first_text(lead.get('phone'), lead.get('x_phone'), lead.get('x_mobilephone'))
    if email:
        out['email'] = email
    if phone:
        out['phone'] = phone
    return out

def fill_empty(current, wanted):
    """Values to write: only where the Contact field is currently empty."""
    return {key: value for key, value in wanted.items()
            if value and not current.get(key)}


def overwrite_nonempty(current, wanted):
    """Explicit button: update only non-empty values different from current; never clear old fields."""
    return {key: value for key, value in wanted.items()
            if value and current.get(key) != value}


def company_vals(name, wanted):
    """Values of a NEW Company: name + the company-type data of the Deal."""
    vals = {'name': name, 'is_company': True, 'company_type': 'company'}
    for key in ADDRESS_FIELDS + ('website', 'vat', 'user_id'):
        if wanted.get(key):
            vals[key] = wanted[key]
    return vals


_TAG = re.compile(r'<[^>]+>')


def html_has_content(value):
    """True when the Html value shows something: a picture or some text ('<p><br></p>' is empty)."""
    if not isinstance(value, str):
        return False
    if '<img' in value.lower():
        return True
    text = _TAG.sub('', value).replace('&nbsp;', ' ').replace('\u200b', '')
    return bool(text.strip())


def build_profile(lead):
    """Deal data (plain dict) -> profile values for the Contact (only non-empty ones).

    Keys of lead = the Deal field names of PROFILE_MAP; result keys = Contact field names.
    """
    out = {}
    for src, dst in PROFILE_MAP:
        value = lead.get(src)
        if dst in HTML_TARGETS:
            if html_has_content(value):
                out[dst] = value
        elif dst in INT_TARGETS:
            try:
                number = int(value or 0)
            except (TypeError, ValueError):
                number = 0
            if number > 0:
                out[dst] = number
        else:
            text = clean(value)
            if text:
                out[dst] = text
    return out


_DATA_URI = re.compile(r'^data:image/[\w.+-]+;base64,(.+)$', re.S)


def logo_value(upload, image_text=None):
    """Base64 picture for the avatar, or False.

    upload     = x_yp_logo_upload (CRM-005, Binary: picture uploaded by hand) -> used first.
    image_text = x_image (Char written by the Chrome extension): used ONLY when it holds an inline picture
                 (data:image/...;base64,...).  A plain link is NOT downloaded (no network call in this addon).
    """
    if upload:
        return upload if isinstance(upload, bytes) else str(upload).encode()
    match = _DATA_URI.match(clean(image_text))
    if match:
        return re.sub(r'\s+', '', match.group(1)).encode()
    return False


def mirror_keys(profile, logo):
    """Contact fields that have to be read before mirroring (the avatar only when there is a logo)."""
    return list(profile) + ([LOGO_FIELD] if logo else []) + [SYNC_FLAG]


def mirror_vals(current, profile, logo):
    """Values to write on a Contact / Company so that it mirrors the Deal: only what differs.

    current = {field: value now on the Contact} for mirror_keys(profile, logo).  Idempotent: when everything
    is already equal (and the flag is set) the result is {}.
    """
    vals = {}
    for key, value in profile.items():
        have = current.get(key)
        if isinstance(value, str):
            same = isinstance(have, str) and have.strip() == value.strip()
        else:
            same = have == value
        if not same:
            vals[key] = value
    if logo and current.get(LOGO_FIELD) != logo:
        vals[LOGO_FIELD] = logo
    if not current.get(SYNC_FLAG):
        vals[SYNC_FLAG] = True
    return vals


def summary(changed_keys, failed_keys=(), company_name=None, company_keys=()):
    """Plain text for the Chatter note (labels only, no data)."""
    done = [LABELS.get(key, key) for key in changed_keys if key != SYNC_FLAG]
    comp = [LABELS.get(key, key) for key in company_keys if key != SYNC_FLAG]
    parts = []
    if done:
        parts.append('Đã đồng bộ %d trường vào Contact: %s.' % (len(done), ', '.join(done)))
    if comp:
        parts.append('Company "%s": %d trường: %s.' % (company_name or '', len(comp), ', '.join(comp)))
    text = ' '.join(parts) or 'Contact đã đủ thông tin, không có trường nào cần điền thêm.'
    if failed_keys:
        text += ' Không ghi được: %s.' % ', '.join(LABELS.get(key, key) for key in failed_keys)
    return text


# CRM-006 Update_008: direct CRM-005 geolocation with NO new res.partner field.
# The explicit Update Contact action is authoritative; initial automatic push
# conservatively preserves a pre-existing different Contact pin.
GEO_STATES = frozenset({'estimated', 'manual'})
GEO_PRECISIONS = frozenset({'address', 'neighborhood', 'city', 'region', 'manual'})


def valid_geo_pair(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError, OverflowError):
        return False
    return (math.isfinite(lat) and math.isfinite(lon)
            and -90 <= lat <= 90 and -180 <= lon <= 180
            and (lat != 0 or lon != 0))


def geo_pairs_equal(first, second, tolerance=0.000001):
    return (valid_geo_pair(*first) and valid_geo_pair(*second)
            and abs(float(first[0]) - float(second[0])) <= tolerance
            and abs(float(first[1]) - float(second[1])) <= tolerance)


def source_geo_pair(data):
    '''Only copy a valid CRM-005 pair for the unchanged, geocoded Deal address.'''
    if data.get('x_yp_geo_status') not in GEO_STATES:
        return None
    if data.get('x_yp_geo_precision') not in GEO_PRECISIONS:
        return None
    stored_key = data.get('x_yp_geo_address_key')
    live_key = data.get('crm005_geo_current_key')
    if not stored_key or not live_key or stored_key != live_key:
        return None
    lat, lon = data.get('x_yp_latitude'), data.get('x_yp_longitude')
    return (float(lat), float(lon)) if valid_geo_pair(lat, lon) else None
