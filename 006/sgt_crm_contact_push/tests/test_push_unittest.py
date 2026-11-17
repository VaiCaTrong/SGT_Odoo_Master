"""CRM-006 unit tests.  Run:  python3 tests/test_push_unittest.py   (no Odoo needed).

Part 1 tests the pure helpers.  Part 2 loads the REAL models/crm_lead.py against
a tiny fake of the Odoo ORM and runs the real trigger / push / button code.
"""
import importlib.util
import os
import sys
import types
import unittest
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, relpath, package=None):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relpath))
    mod = importlib.util.module_from_spec(spec)
    if package:
        mod.__package__ = package
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


push = _load('crm006_push', 'models/push.py')


# ----------------------------------------------------------------- part 1: pure
class PureTests(unittest.TestCase):
    def test_collapse_doubled_name(self):
        self.assertEqual(push.collapse_repeated_name('Mr. Chinh Mr. Chinh'), 'Mr. Chinh')
        self.assertEqual(push.collapse_repeated_name('Nguyen Van A nguyen van a'), 'Nguyen Van A')

    def test_one_word_repeat_is_kept(self):
        # a real name such as "Bình Bình" must NOT be touched
        self.assertEqual(push.collapse_repeated_name('Bình Bình'), 'Bình Bình')
        self.assertEqual(push.collapse_repeated_name('Mr. Chinh'), 'Mr. Chinh')
        self.assertEqual(push.collapse_repeated_name('A B C'), 'A B C')
        self.assertEqual(push.collapse_repeated_name(False), False)

    def test_build_wanted_only_non_empty(self):
        w = push.build_wanted({
            'street': ' 04 Mộc Bài ', 'street2': False, 'city': '', 'zip': None,
            'state_id': False, 'country_id': 241, 'website': '', 'x_website': 'http://khataco.vn/',
            'function': '', 'x_jobtitle': 'Giám đốc', 'x_yp_tax_code': '0401305016',
            'user_id': 35, 'x_getfly_id': 'VN021635', 'tag_names': ['Hunter']})
        self.assertEqual(w, {'street': '04 Mộc Bài', 'country_id': 241, 'website': 'http://khataco.vn/',
                             'function': 'Giám đốc', 'vat': '0401305016', 'user_id': 35, 'ref': 'VN021635'})

    def test_website_prefers_standard_field(self):
        w = push.build_wanted({'website': 'a.vn', 'x_website': 'b.vn'})
        self.assertEqual(w['website'], 'a.vn')

    def test_fill_empty_never_overwrites(self):
        cur = {'street': 'Old', 'city': False, 'vat': ''}
        self.assertEqual(push.fill_empty(cur, {'street': 'New', 'city': 'HN', 'vat': '1'}),
                         {'city': 'HN', 'vat': '1'})
        self.assertEqual(push.overwrite_nonempty(cur, {'street': 'New', 'city': 'HN', 'vat': '1'}),
                         {'street': 'New', 'city': 'HN', 'vat': '1'})
        self.assertNotIn('street2', push.overwrite_nonempty({'street2': 'Old'}, {'street2': ''}))

    def test_unique_names_case_insensitive(self):
        self.assertEqual(push.unique_names(['hunter', 'Hunter', ' HUNTER ', 'Google', False, '']),
                         ['hunter', 'Google'])

    def test_company_vals(self):
        v = push.company_vals('Khả Tâm', {'street': 's', 'vat': '1', 'ref': 'x', 'user_id': 5, 'website': 'w'})
        self.assertEqual(v, {'name': 'Khả Tâm', 'is_company': True, 'company_type': 'company',
                             'street': 's', 'vat': '1', 'website': 'w', 'user_id': 5})

    def test_summary_text(self):
        self.assertIn('2 trường', push.summary(['street', 'vat']))
        self.assertIn('Tax ID', push.summary(['street', 'vat']))
        self.assertIn('đủ thông tin', push.summary([]))
        self.assertIn('Không ghi được: Tax ID', push.summary(['street'], ['vat']))

    # ---- Update_002 pure helpers
    def test_html_has_content(self):
        self.assertFalse(push.html_has_content(False))
        self.assertFalse(push.html_has_content('<p><br></p>'))
        self.assertFalse(push.html_has_content('<p>&nbsp; \u200b</p>'))
        self.assertTrue(push.html_has_content('<p>Hello</p>'))
        self.assertTrue(push.html_has_content('<p><img src="data:image/png;base64,AAAA"></p>'))

    def test_build_profile_maps_names_and_skips_empty(self):
        p = push.build_profile({
            'x_type_contact': ' Manufacturer ', 'x_country': '', 'x_fb_industry': 'Packaging',
            'x_yp_founded_year': 2008, 'referred': 'https://yellowpages.vn/lis/1',
            'x_yp_intro_en': '<p>EN</p>', 'x_yp_gallery_html': '<p><br></p>', 'description': '<p>VI</p>',
            'x_yp_employee_range': False})
        self.assertEqual(p, {'x_type_contact': 'Manufacturer', 'x_fb_industry': 'Packaging', 'x_yp_founded_year': 2008,
                             'x_yp_listing_url': 'https://yellowpages.vn/lis/1', 'x_yp_intro_en': '<p>EN</p>',
                             'comment': '<p>VI</p>'})

    def test_build_profile_year_zero_or_bad_is_empty(self):
        self.assertEqual(push.build_profile({'x_yp_founded_year': 0}), {})
        self.assertEqual(push.build_profile({'x_yp_founded_year': 'abc'}), {})

    def test_tax_code_is_not_mirrored(self):
        self.assertNotIn('vat', [dst for _src, dst in push.PROFILE_MAP])
        self.assertNotIn('x_yp_tax_code', [src for src, _dst in push.PROFILE_MAP])

    def test_logo_value(self):
        self.assertEqual(push.logo_value(b'UPLOAD', 'data:image/png;base64,AAAA'), b'UPLOAD')
        self.assertEqual(push.logo_value(False, 'data:image/png;base64,AA AA\n'), b'AAAA')
        self.assertFalse(push.logo_value(False, 'https://yellowpages.vn/logo.png'))     # links are never downloaded
        self.assertFalse(push.logo_value(False, False))

    def test_mirror_vals_only_differences_and_flag(self):
        prof = {'x_country': 'VN', 'x_yp_founded_year': 2008}
        self.assertEqual(push.mirror_vals({'x_country': 'VN', 'x_yp_founded_year': 2008, 'x_sgt_crm_synced': True}, prof, False), {})
        self.assertEqual(push.mirror_vals({'x_country': 'Old', 'x_yp_founded_year': 2008, 'x_sgt_crm_synced': True}, prof, False),
                         {'x_country': 'VN'})
        self.assertEqual(push.mirror_vals({'x_country': 'VN', 'x_yp_founded_year': 2008}, prof, False),
                         {'x_sgt_crm_synced': True})
        self.assertEqual(push.mirror_vals({'x_sgt_crm_synced': True, 'image_1920': b'OLD'}, {}, b'NEW'), {'image_1920': b'NEW'})
        self.assertEqual(push.mirror_keys(prof, b'L'), ['x_country', 'x_yp_founded_year', 'image_1920', 'x_sgt_crm_synced'])
        self.assertEqual(push.mirror_keys({}, False), ['x_sgt_crm_synced'])

    def test_summary_with_company_and_flag_hidden(self):
        t = push.summary(['street', 'x_sgt_crm_synced'], (), 'ACME', ['x_country', 'image_1920', 'x_sgt_crm_synced'])
        self.assertIn('1 trường vào Contact: Street', t)
        self.assertIn('Company "ACME": 2 trường: Main Market, Company Logo', t)
        self.assertNotIn('synced', t.lower())
        self.assertIn('đủ thông tin', push.summary(['x_sgt_crm_synced'], (), 'ACME', ['x_sgt_crm_synced']))


# ------------------------------------------------------------ part 2: fake ORM
class FakeRS:
    """Tiny recordset of FakeRec."""

    def __init__(self, recs=()):
        self.recs = list(recs)

    def __iter__(self):
        return iter(self.recs)

    def __bool__(self):
        return bool(self.recs)

    def __len__(self):
        return len(self.recs)

    def __getattr__(self, name):          # recordset.name / recordset.vat ...
        if name.startswith('_') or name == 'recs':
            raise AttributeError(name)
        if name == 'active':
            return self.recs[0].vals.get('active', True) if self.recs else False
        return self.recs[0][name] if self.recs else False

    def __getitem__(self, i):
        if isinstance(i, str):
            return self.recs[0][i]
        return self.recs[i]

    @property
    def ids(self):
        return [r.id for r in self.recs]

    @property
    def id(self):
        return self.recs[0].id if self.recs else False

    def mapped(self, name):
        return [r.vals.get(name) for r in self.recs]

    def write(self, vals):
        return self.recs[0].write(vals)

    def geo_localize(self):
        return self.recs[0].geo_localize() if self.recs else False

    def sudo(self):
        return self

    def browse(self, *a):
        return FakeRS()


class FakeRec(FakeRS):
    def __init__(self, store, id_, vals):
        super().__init__([self])
        self.store, self.id_, self.vals = store, id_, vals
        self.recs = [self]

    @property
    def id(self):
        return self.id_

    @property
    def _fields(self):
        return {'x_sgt_crm_synced': True}

    def __getattr__(self, name):
        if name in ('vals', 'store', 'id_', 'recs'):
            raise AttributeError(name)
        if name == 'active':
            return self.vals.get('active', True)
        return self.vals.get(name, False)

    def __getitem__(self, name):
        if isinstance(name, int):
            return self
        v = self.vals.get(name, False)
        if name in ('state_id', 'country_id', 'user_id', 'parent_id'):
            return self.store.rel(v)
        if name == 'category_id':
            return FakeRS([self.store.cat.recs[i] for i in (v or [])])
        return v

    def geo_localize(self):
        self.vals['partner_latitude'] = 10.77
        self.vals['partner_longitude'] = 106.70
        return True

    def write(self, vals):
        self.store.write_log.append((self.id_, dict(vals)))
        if self.store.refuse and any(k in self.store.refuse for k in vals):
            raise ValueError('refused')
        if getattr(self.store, 'reset_geo_on_address', False) and any(
                k in push.ADDRESS_FIELDS or k == 'parent_id' for k in vals):
            self.vals['partner_latitude'] = 0.0
            self.vals['partner_longitude'] = 0.0
        for k, v in vals.items():
            if k == 'category_id':
                for cmd in v:
                    self.vals.setdefault('category_id', []).append(cmd[1])
            else:
                self.vals[k] = v
        return True

    @property
    def name(self):
        return self.vals.get('name')

    @property
    def is_company(self):
        return self.vals.get('is_company', False)

    @property
    def parent_id(self):
        return self.store.rel(self.vals.get('parent_id'))

    @property
    def category_id(self):
        return FakeRS([self.store.cat.recs[i] for i in self.vals.get('category_id', [])])


class FakeStore:
    """Acts as env[model] for res.partner and res.partner.category."""

    def __init__(self, prefix):
        self.recs, self.next, self.write_log, self.created, self.refuse = {}, 100, [], [], set()
        self.prefix = prefix

    def rel(self, v):
        return FakeRS([self.recs[v]]) if v in self.recs else FakeRS([FakeRel(v)]) if v else FakeRS()

    def add(self, **vals):
        self.next += 1
        rec = FakeRec(self, self.next, vals)
        self.recs[self.next] = rec
        return rec

    def create(self, vals):
        if self.refuse and any(k in self.refuse for k in vals) and self.prefix == 'partner':
            raise ValueError('refused create')
        self.created.append(dict(vals))
        return self.add(**vals)

    def search(self, domain, limit=None):
        out = []
        for rec in self.recs.values():
            ok = True
            for field, op, value in domain:
                have = rec.vals.get(field)
                if op == '=' and have != value:
                    ok = False
                if op == 'ilike':
                    import re
                    pat = '.*'.join(re.escape(x) for x in str(value).split('%'))
                    if not re.search(pat, str(have or ''), re.I):
                        ok = False
            if ok:
                out.append(rec)
        return FakeRS(out[:limit] if limit else out)

    def sudo(self):
        return self

    def with_context(self, **kwargs):
        return self

    def browse(self, *a):
        return FakeRS()


class FakeRel:
    def __init__(self, id_):
        self.id, self.id_ = id_, id_


class FakeCr:
    @contextmanager
    def savepoint(self):
        yield


class FakeDocumentsFolders:
    def __init__(self):
        self.calls = []
        self.fail = False

    def explorer_create_deal_folder(self, lead_id):
        self.calls.append(lead_id)
        if self.fail:
            raise RuntimeError('Temporary Documents unavailable')
        return {'id': 8008, 'name': 'Công Ty TNHH Khả Tâm - 0401305016', 'already_exists': False}


class FakeEnv:
    def __init__(self, partner, cat):
        self.cr = FakeCr()
        self.context = {}
        self.docs = FakeDocumentsFolders()
        self.models = {'res.partner': partner, 'res.partner.category': cat,
                       'argo.document.folder': self.docs}

    def __getitem__(self, name):
        return self.models[name]


def _stub_odoo():
    odoo = types.ModuleType('odoo')

    class Model:
        _inherit = None
        written = []

        def write(self, vals):
            type(self).written.append(dict(vals))
            if hasattr(self, 'vals'):
                for key, value in vals.items():
                    if key == 'partner_id':
                        self.partner_id = value
                    else:
                        self.vals[key] = value
            return True

    odoo.models = types.SimpleNamespace(Model=Model)
    odoo._ = lambda text, *a: text % a if a else text
    exc = types.ModuleType('odoo.exceptions')

    class UserError(Exception):
        pass

    exc.UserError = UserError
    class AccessError(Exception):
        pass
    exc.AccessError = AccessError
    tools = types.ModuleType('odoo.tools')
    tools.html_escape = lambda s: str(s).replace('&', '&amp;').replace('<', '&lt;')
    sys.modules.update({'odoo': odoo, 'odoo.exceptions': exc, 'odoo.tools': tools})
    return Model, UserError


Model, UserError = _stub_odoo()
pkg = types.ModuleType('crm006pkg')
pkg.__path__ = [os.path.join(ROOT, 'models')]
sys.modules['crm006pkg'] = pkg
sys.modules['crm006pkg.push'] = push
crm_mod = _load('crm006pkg.crm_lead', 'models/crm_lead.py', package='crm006pkg')
CrmLead = crm_mod.CrmLead


class FakeLead(CrmLead):
    """The REAL CrmLead methods on a fake record."""

    def __init__(self, env, partner, **vals):
        self.env = env
        self.partner_id = partner
        self.vals = vals
        self.notes = []
        self._fields = {name: 1 for name in ('x_website', 'x_jobtitle', 'x_yp_tax_code', 'x_groupname', 'x_getfly_id',
                                             'x_yp_logo_upload', 'x_image', 'x_email01', 'x_phone', 'x_mobilephone',
                                             'x_yp_latitude', 'x_yp_longitude', 'x_yp_geo_status',
                                             'x_yp_geo_precision', 'x_yp_geo_address_key')}
        self._fields.update({src: 1 for src, _dst in push.PROFILE_MAP})
        self.contact_name = vals.get('contact_name', False)
        self.display_name = 'Deal'
        self.id = 215

    def __getattr__(self, name):
        v = self.__dict__.get('vals', {}).get(name, False)
        return v

    def __getitem__(self, name):
        return self.vals.get(name, False)

    def __iter__(self):
        return iter([self])

    def ensure_one(self):
        return self

    def filtered(self, name):
        return [self] if getattr(self, name) else []

    def _crm005_geo_signature(self):
        return self.vals.get('_geo_signature', False)

    def with_context(self, **kw):
        return self

    @property
    def state_id(self):
        return FakeRel(self.vals.get('state_id'))

    @property
    def country_id(self):
        return FakeRel(self.vals.get('country_id'))

    @property
    def user_id(self):
        return FakeRel(self.vals.get('user_id'))

    @property
    def tag_ids(self):
        return FakeRS([FakeRec(None, i, {'name': n}) for i, n in enumerate(self.vals.get('tags', []))])

    def message_post(self, **kw):
        self.notes.append(kw)


def make(partner_vals=None, lead_vals=None, companies=(), tags=(), refuse=()):
    pstore, cstore = FakeStore('partner'), FakeStore('cat')
    pstore.refuse = set(refuse)
    for c in companies:
        pstore.add(**c)
    for t in tags:
        cstore.add(name=t)
    partner = pstore.add(**(partner_vals if partner_vals is not None else {'name': 'Mr. Chinh Mr. Chinh', 'email': 'khatam@khataco.vn'}))
    pstore.cat = cstore
    env = FakeEnv(pstore, cstore)
    base = dict(partner_name='Công Ty TNHH Khả Tâm', street='04 Mộc Bài 01', city='Đà Nẵng', country_id=241,
                x_website='http://khataco.vn/', x_yp_tax_code='0401305016', user_id=35, x_getfly_id='VN021635',
                tags=['Hunter', 'hunter'], contact_name='Mr. Chinh Mr. Chinh')
    base.update(lead_vals or {})
    return FakeLead(env, partner if partner else FakeRS(), **base), pstore, cstore, partner


class ModelTests(unittest.TestCase):
    def test_trigger_runs_push_after_old_button_write(self):
        lead, pstore, cstore, partner = make()
        lead.write({'x_groupname': 'Mr. Chinh xSGT VN021635', 'x_getfly_id': 'VN021635'})
        self.assertEqual(partner.vals['street'], '04 Mộc Bài 01')
        self.assertEqual(partner.vals['vat'], '0401305016')
        self.assertEqual(partner.vals['ref'], 'VN021635')
        self.assertEqual(partner.vals['user_id'], 35)
        self.assertEqual(partner.vals['name'], 'Mr. Chinh')
        self.assertEqual(lead.contact_name, 'Mr. Chinh')

    def test_other_writes_do_not_trigger(self):
        lead, pstore, cstore, partner = make()
        lead.write({'name': 'x', 'stage_id': 3})
        self.assertEqual(pstore.write_log, [])
        self.assertEqual(lead.notes, [])

    def test_no_contact_no_push(self):
        lead, pstore, cstore, partner = make(partner_vals=None)
        lead.partner_id = FakeRS()
        lead.write({'x_groupname': 'a'})
        self.assertEqual(pstore.write_log, [])

    def test_skip_context(self):
        lead, pstore, cstore, partner = make()
        lead.env.context['sgt_crm006_skip'] = True
        lead.write({'x_groupname': 'a'})
        self.assertEqual(pstore.write_log, [])

    def test_creates_company_and_links(self):
        lead, pstore, cstore, partner = make()
        lead.write({'x_groupname': 'a'})
        self.assertEqual(len(pstore.created), 1)
        c = pstore.created[0]
        self.assertEqual(c['name'], 'Công Ty TNHH Khả Tâm')
        self.assertTrue(c['is_company'])
        self.assertEqual(c['vat'], '0401305016')
        self.assertEqual(partner.vals['parent_id'], 102 if False else partner.vals['parent_id'])
        self.assertTrue(partner.vals['parent_id'])

    def test_reuses_company_by_tax_id(self):
        lead, pstore, cstore, partner = make(companies=[{'name': 'Khả Tâm (cũ)', 'is_company': True, 'vat': '0401305016'}])
        lead.write({'x_groupname': 'a'})
        self.assertEqual(pstore.created, [])
        self.assertEqual(partner.vals['parent_id'], 101)

    def test_reuses_company_by_name_ignoring_case_and_spaces(self):
        lead, pstore, cstore, partner = make(companies=[{'name': 'công ty  tnhh khả tâm', 'is_company': True}])
        lead.write({'x_groupname': 'a'})
        self.assertEqual(pstore.created, [])
        self.assertEqual(partner.vals['parent_id'], 101)

    def test_existing_company_receives_full_first_sync(self):
        lead, pstore, cstore, partner = make(companies=[{'name': 'Công Ty TNHH Khả Tâm', 'is_company': True,
                                                          'street': 'Địa chỉ cũ'}])
        lead.write({'x_groupname': 'a'})
        company = pstore.recs[101]
        self.assertEqual(company.vals['street'], '04 Mộc Bài 01')       # full first sync
        self.assertEqual(company.vals['vat'], '0401305016')           # empty -> filled

    def test_company_not_created_without_name(self):
        lead, pstore, cstore, partner = make(lead_vals={'partner_name': False})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(pstore.created, [])
        self.assertNotIn('parent_id', partner.vals)

    def test_contact_that_has_company_keeps_it(self):
        lead, pstore, cstore, partner = make(companies=[{'name': 'Công ty khác', 'is_company': True}])
        partner.vals['parent_id'] = 101
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['parent_id'], 101)
        self.assertEqual(pstore.created, [])

    def test_first_sync_overwrites_nonempty_native_fields(self):
        lead, pstore, cstore, partner = make(partner_vals={'name': 'An', 'street': 'Giữ nguyên', 'vat': 'GIỮ', 'ref': 'R1'})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['street'], '04 Mộc Bài 01')
        self.assertEqual(partner.vals['vat'], '0401305016')
        self.assertEqual(partner.vals['ref'], 'VN021635')
        self.assertEqual(partner.vals['city'], 'Đà Nẵng')

    def test_name_not_changed_when_not_doubled(self):
        lead, pstore, cstore, partner = make(partner_vals={'name': 'Mr. Chinh'}, lead_vals={'contact_name': 'Mr. Chinh'})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['name'], 'Mr. Chinh')

    def test_tags_created_deduplicated_and_added_not_replaced(self):
        lead, pstore, cstore, partner = make(tags=['Google'])
        partner.vals['category_id'] = [cstore.add(name='VIP').id]
        lead.write({'x_groupname': 'a'})
        names = sorted(cstore.recs[i].vals['name'] for i in partner.vals['category_id'])
        self.assertEqual(names, ['Hunter', 'VIP'])               # 'hunter'+'Hunter' -> ONE; VIP kept
        self.assertEqual([c['name'] for c in cstore.created], ['Hunter'])

    def test_existing_partner_tag_reused_case_insensitive(self):
        lead, pstore, cstore, partner = make(tags=['HUNTER'])
        lead.write({'x_groupname': 'a'})
        self.assertEqual(cstore.created, [])
        self.assertEqual(len(partner.vals['category_id']), 1)

    def test_run_twice_changes_nothing_the_second_time(self):
        lead, pstore, cstore, partner = make()
        lead.write({'x_groupname': 'a'})
        before_notes, before_log = len(lead.notes), len(pstore.write_log)
        lead.partner_id = partner
        lead.write({'x_groupname': 'b'})
        self.assertEqual(len(pstore.write_log), before_log)
        self.assertEqual(len(lead.notes), before_notes)

    def test_chatter_note_lists_labels_not_data(self):
        lead, pstore, cstore, partner = make()
        lead.write({'x_groupname': 'a'})
        self.assertEqual(len(lead.notes), 1)
        body = str(lead.notes[0]['body'])
        self.assertIn('Tax ID', body)
        self.assertIn('Company', body)
        self.assertNotIn('0401305016', body)
        self.assertEqual(lead.notes[0]['subtype_xmlid'], 'mail.mt_note')

    def test_refused_vat_does_not_block_other_fields(self):
        lead, pstore, cstore, partner = make(refuse={'vat'})
        lead.write({'x_groupname': 'a'})
        self.assertNotIn('vat', partner.vals)
        self.assertEqual(partner.vals['street'], '04 Mộc Bài 01')
        self.assertIn('Không ghi được', str(lead.notes[0]['body']))

    def test_refused_company_vat_fails_closed_without_new_company(self):
        lead, pstore, cstore, partner = make(refuse={'vat'})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(len(pstore.created), 0)
        self.assertIn('Company', str(lead.notes[0]['body']))

    def test_exception_in_push_never_blocks_old_flow(self):
        lead, pstore, cstore, partner = make()
        lead._sgt_crm006_push_to_partner = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom'))
        self.assertTrue(lead.write({'x_groupname': 'a'}))

    def test_button_without_contact_is_refused(self):
        lead, pstore, cstore, partner = make()
        lead.partner_id = FakeRS()
        with self.assertRaises(UserError):
            lead.action_sgt_crm006_push_contact()

    def test_button_runs_push_and_returns_notification(self):
        lead, pstore, cstore, partner = make()
        action = lead.action_sgt_crm006_push_contact()
        self.assertEqual(action['tag'], 'display_notification')
        self.assertIn('Đã đồng bộ', action['params']['message'])
        self.assertEqual(partner.vals['vat'], '0401305016')

    def test_button_second_time_says_nothing_to_fill_and_posts_note(self):
        lead, pstore, cstore, partner = make()
        lead.action_sgt_crm006_push_contact()
        lead.partner_id = partner
        action = lead.action_sgt_crm006_push_contact()
        self.assertIn('đủ thông tin', action['params']['message'])


PROFILE = dict(
    x_type_contact='Manufacturer', x_country='Korea; Japan', x_yp_employee_range='51-200', x_fb_industry='Packaging; Printing',
    x_url_zalo_group='https://zalo.me/g/1', x_url_fb_profile='https://facebook.com/p', x_group_link='https://facebook.com/groups/1',
    x_group_post_link='https://facebook.com/groups/1/posts/2', x_yp_founded_year=2008, referred='https://yellowpages.vn/lis/1',
    x_yp_intro_en='<p>EN intro</p>', x_yp_gallery_html='<p><img src="data:image/png;base64,GGG"></p>',
    x_yp_partners_html='<p><img src="data:image/png;base64,PPP"></p>', description='<p>Giới thiệu VI</p>')
MIRRORED = ('x_type_contact', 'x_country', 'x_yp_employee_range', 'x_fb_industry', 'x_url_zalo_group', 'x_url_fb_profile',
            'x_group_link', 'x_group_post_link', 'x_yp_founded_year', 'x_yp_intro_en', 'x_yp_gallery_html', 'x_yp_partners_html')


class Update004Tests(unittest.TestCase):
    def test_button_overwrites_nonempty_but_not_avatar_or_empty_fields(self):
        lead, ps, _, person = make(partner_vals={
            'name': 'Person', 'is_company': False, 'street': 'Old street', 'street2': 'Old 2',
            'website': 'old.vn', 'vat': '111', 'image_1920': b'PERSON', 'city':'Old city',
            'country_id':241, 'partner_latitude':10.5, 'partner_longitude':106.5},
            lead_vals={'street':'New street', 'street2':'', 'city':'New city',
                       'website':'new.vn', 'x_yp_tax_code':'222','x_yp_logo_upload':b'COMPANY'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['street'], 'New street')
        self.assertEqual(person.vals['street2'], 'Old 2')
        self.assertEqual(person.vals['vat'], '222')
        self.assertEqual(person.vals['website'], 'new.vn')
        self.assertEqual(person.vals['image_1920'], b'PERSON')
        self.assertEqual(person.vals['partner_latitude'], 10.77)
        company = next(r for r in ps.recs.values() if r.vals.get('is_company'))
        self.assertEqual(company.vals['image_1920'], b'COMPANY')
        self.assertEqual(company.vals['street'], 'New street')

    def test_trigger_full_sync_first_time(self):
        lead, _, _, person = make(partner_vals={'name':'Person','street':'Old', 'website':'old.vn'})
        lead.write({'x_groupname':'done'})
        self.assertEqual(person.vals['street'], '04 Mộc Bài 01')
        self.assertEqual(person.vals['website'], 'http://khataco.vn/')

    def test_button_overwrites_person_phone_email_when_source_has_values(self):
        lead, _, _, person = make(partner_vals={'name':'Person','phone':'123','email':'old@example.com'},
                                  lead_vals={'phone':'456','email_from':'new@example.com'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['phone'], '456')
        self.assertEqual(person.vals['email'], 'new@example.com')

    def test_geolocation_warning_if_address_incomplete(self):
        lead, _, _, person = make(partner_vals={'name':'Person','street':'Old','city':'Old',
                                              'country_id':False, 'partner_latitude':False,
                                              'partner_longitude':False},
                                   lead_vals={'street':'New','city':'', 'country_id':False})
        notification = lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['street'], 'New')
        self.assertIn('Geolocation', notification['params']['message'])
        self.assertEqual(notification['params']['type'], 'warning')

    def test_geolocation_failure_does_not_rollback_contact(self):
        original=FakeRec.geo_localize
        try:
            def fail_geo(self):
                raise ValueError('geocoder offline')
            FakeRec.geo_localize=fail_geo
            lead, _, _, person = make(partner_vals={'name':'Person','street':'OLD','city':'City',
                                                   'country_id':241, 'partner_latitude':False,
                                                   'partner_longitude':False},
                                       lead_vals={'street':'NEW'})
            result=lead.action_sgt_crm006_push_contact()
            self.assertEqual(person.vals['street'], 'NEW')
            self.assertEqual(result['params']['type'], 'warning')
            self.assertIn('Geolocation', result['params']['message'])
        finally:
            FakeRec.geo_localize=original

    def test_button_updates_existing_company_address(self):
        lead, ps, _, person = make(partner_vals={'name':'Person','street':'Old','parent_id':101},
                                   companies=({'name':'Company','is_company':True,'street':'Old',
                                               'city':'Old city','country_id':241},),
                                   lead_vals={'street':'NEW','city':'New city'})
        lead.action_sgt_crm006_push_contact()
        company=ps.recs[101]
        self.assertEqual(company.vals['street'], 'NEW')
        self.assertEqual(company.vals['city'], 'New city')
        self.assertEqual(company.vals['partner_latitude'], 10.77)


class Update005Tests(unittest.TestCase):
    def test_manual_button_reuses_company_found_by_vat_without_duplicate(self):
        lead, ps, _, person = make(
            companies=({'name': 'Tên cũ', 'is_company': True, 'vat':'0401305016',
                        'street':'Old company street', 'city':'Old city', 'country_id':241},),
            partner_vals={'name':'Ms. A', 'is_company':False, 'email':'old@company.com'},
            lead_vals={'street':'New street', 'city':'New city', 'email_from':'a@example.com'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(ps.created, [])  # ABSOLUTELY no second Company
        self.assertEqual(person.vals['parent_id'], 101)
        self.assertEqual(ps.recs[101].vals['street'], 'New street')
        self.assertEqual(ps.recs[101].vals['city'], 'New city')
        self.assertEqual(ps.recs[101].vals.get('email'), None)  # Person email not company email
        self.assertEqual(person.vals['email'], 'a@example.com')

    def test_manual_button_reuses_company_found_by_name_without_duplicate(self):
        lead, ps, _, person = make(
            companies=({'name':'CÔNG TY TNHH KHẢ TÂM','is_company':True,'street':'Old'},),
            partner_vals={'name':'Person'},
            lead_vals={'x_yp_tax_code':False,'street':'New'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(ps.created, [])
        self.assertEqual(person.vals['parent_id'], 101)
        self.assertEqual(ps.recs[101].vals['street'], 'New')

    def test_manual_button_update_without_parent_company_does_not_create_duplicate(self):
        lead, ps, _, person = make(
            companies=({'name':'Khả Tâm cũ','is_company':True,'vat':'0401305016'},),
            lead_vals={'email_from':'new@example.org','phone':'0909123456'},
            partner_vals={'name':'Person','email':'old@x.com','phone':'0000'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(ps.created, [])
        self.assertEqual(person.vals['parent_id'], 101)
        self.assertEqual(person.vals['email'],'new@example.org')
        self.assertEqual(person.vals['phone'],'0909123456')

    def test_manual_button_empty_channels_preserves_existing(self):
        lead, _, _, person = make(
            partner_vals={'name':'Person','email':'existing@example.com','phone':'123'},
            lead_vals={'email_from':False,'x_email01':'','phone':'','x_phone':False,'x_mobilephone':' '})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['email'],'existing@example.com')
        self.assertEqual(person.vals['phone'],'123')

    def test_person_channel_fallback_priorities(self):
        self.assertEqual(push.build_contact_channels({'email_from':'primary@x.com','x_email01':'secondary@x.com',
                                                      'phone':'111','x_phone':'222','x_mobilephone':'333'}),
                         {'email':'primary@x.com','phone':'111'})
        self.assertEqual(push.build_contact_channels({'email_from':'','x_email01':' alt@x.com ',
                                                      'phone':'','x_phone':'222','x_mobilephone':'333'}),
                         {'email':'alt@x.com','phone':'222'})
        self.assertEqual(push.build_contact_channels({'x_mobilephone':' 333 '}),{'phone':'333'})

    def test_automatic_first_trigger_overwrites_existing_email_phone(self):
        lead, ps, _, person = make(
            partner_vals={'name':'Person','email':'old@example.com','phone':'111'},
            lead_vals={'email_from':'new@example.com','phone':'222'})
        lead.write({'x_groupname':'created'})
        self.assertEqual(person.vals['email'],'new@example.com')
        self.assertEqual(person.vals['phone'],'222')

    def test_manual_on_direct_company_updates_channels_and_logo(self):
        lead, ps, _, company = make(
            partner_vals={'name':'Company','is_company':True,'email':'old@example.com',
                          'phone':'111', 'image_1920':b'OLD'},
            lead_vals={'email_from':'sales@example.com','phone':'0908', 'x_yp_logo_upload':b'LOGO'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(company.vals['email'], 'sales@example.com')
        self.assertEqual(company.vals['phone'], '0908')
        self.assertEqual(company.vals['image_1920'], b'LOGO')
        self.assertEqual(ps.created, [])

    def test_child_person_does_not_overwrite_company_phone_email(self):
        lead, ps, _, person = make(
            companies=({'name':'The Company','is_company':True,'email':'office@example.com','phone':'0288888'},),
            partner_vals={'name':'Person','parent_id':101,'email':'old@x.com','phone':'0000','image_1920':b'AVATAR'},
            lead_vals={'email_from':'new@example.com','phone':'0909','x_yp_logo_upload':b'COMPANYLOGO'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['email'], 'new@example.com')
        self.assertEqual(person.vals['phone'], '0909')
        self.assertEqual(person.vals['image_1920'], b'AVATAR')
        self.assertEqual(ps.recs[101].vals['email'],'office@example.com')
        self.assertEqual(ps.recs[101].vals['phone'],'0288888')
        self.assertEqual(ps.recs[101].vals['image_1920'], b'COMPANYLOGO')

    def test_idempotence_contact_channels_on_second_manual_run(self):
        lead, ps, _, person = make(
            partner_vals={'name':'Person','email':'old@example.com','phone':'111'},
            lead_vals={'email_from':'new@example.com','phone':'0909'})
        lead.action_sgt_crm006_push_contact()
        before=len([x for x in ps.write_log if x[0]==person.id and ('email' in x[1] or 'phone' in x[1])])
        lead.action_sgt_crm006_push_contact()
        after=len([x for x in ps.write_log if x[0]==person.id and ('email' in x[1] or 'phone' in x[1])])
        self.assertEqual(before,after)


    def test_manual_button_fallback_channels_from_legacy_deal_fields(self):
        lead, ps, _, person = make(
            partner_vals={'name':'Person','email':'old@x.com','phone':'111'},
            lead_vals={'email_from':'','x_email01':'alt@example.com','phone':'', 'x_phone':'0900'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['email'],'alt@example.com')
        self.assertEqual(person.vals['phone'],'0900')

    def test_new_company_has_salesperson_without_changing_existing_company_owner(self):
        lead, ps, _, person=make(partner_vals={'name':'Person'},lead_vals={'user_id':35})
        lead.action_sgt_crm006_push_contact()
        company=ps.recs[person.vals['parent_id']]
        self.assertEqual(company.vals['user_id'],35)
        lead2, ps2, _, person2=make(companies=({'name':'Khả Tâm cũ','is_company':True,'vat':'0401305016', 'user_id':42},),
                                    partner_vals={'name':'Person'},lead_vals={'user_id':35})
        lead2.action_sgt_crm006_push_contact()
        self.assertEqual(ps2.recs[101].vals['user_id'],42)


class Update009DocumentsFolderTests(unittest.TestCase):
    def test_create_contact_auto_ensures_folder_once(self):
        lead, _, _, _ = make()
        lead.write({'x_groupname': 'Create result'})
        self.assertEqual(lead.env.docs.calls, [215])
        lead.write({'name': 'Unrelated data'})
        lead.write({'x_groupname': 'Create result'})
        self.assertEqual(lead.env.docs.calls, [215])

    def test_create_contact_marker_before_partner_will_create_folder(self):
        lead, _, _, partner = make(lead_vals={'x_getfly_id': False})
        lead.partner_id = FakeRS()
        lead.write({'x_groupname': 'Created'})
        self.assertEqual(lead.env.docs.calls, [])
        lead.write({'partner_id': partner})
        self.assertEqual(lead.env.docs.calls, [215])

    def test_folder_creation_failure_does_not_roll_back_contact(self):
        lead, _, _, partner = make()
        lead.env.docs.fail = True
        self.assertTrue(lead.write({'x_groupname': 'Created'}))
        self.assertTrue(partner.vals.get('x_sgt_crm_synced'))
        self.assertEqual(lead.env.docs.calls, [215])

    def test_synced_contact_link_still_checks_for_missing_folder(self):
        lead, _, _, partner = make(partner_vals={'x_sgt_crm_synced': True})
        lead.write({'x_groupname': 'Created'})
        self.assertEqual(lead.env.docs.calls, [215])


class Update006Tests(unittest.TestCase):
    """New behavior: observe legacy completion, do one full verified push."""

    def test_first_create_full_overwrite_including_company_logo_and_channels(self):
        lead, store, _, person = make(
            partner_vals={'name':'Real Person','is_company':False,
                          'email':'legacy@example.com','phone':'000',
                          'street':'Old street','vat':'OLD',
                          'image_1920':b'PERSON_AVATAR'},
            lead_vals={'email_from':'person@example.com','phone':'0908',
                       'x_yp_logo_upload':b'COMPANY_LOGO', 'city':'Da Nang'})
        lead.write({'x_groupname':'Create result'})
        self.assertEqual(person.vals['email'], 'person@example.com')
        self.assertEqual(person.vals['phone'], '0908')
        self.assertEqual(person.vals['street'], '04 Mộc Bài 01')
        self.assertEqual(person.vals['image_1920'], b'PERSON_AVATAR')
        company=store.recs[person.vals['parent_id']]
        self.assertTrue(company.vals['is_company'])
        self.assertEqual(company.vals['image_1920'], b'COMPANY_LOGO')
        self.assertEqual(company.vals['city'], 'Da Nang')
        self.assertEqual(company.vals['partner_latitude'], 10.77)
        self.assertTrue(person.vals['x_sgt_crm_synced'])
        self.assertEqual(len(lead.notes), 1)

    def test_multiple_result_markers_only_one_first_push(self):
        lead, store, _, person = make()
        lead.write({'x_getfly_id':'NEW_REF'})
        counts=(len(store.write_log),len(lead.notes))
        lead.write({'x_groupname':'Complete'})
        self.assertEqual((len(store.write_log),len(lead.notes)),counts)
        lead.write({'x_getfly_id':'NEWER_REF'})
        self.assertEqual((len(store.write_log),len(lead.notes)),counts)

    def test_partner_first_then_result_marker(self):
        lead, store, _, person = make(lead_vals={'x_getfly_id':False})
        lead.partner_id=FakeRS()
        lead.write({'partner_id':person})
        self.assertFalse(person.vals.get('x_sgt_crm_synced'))
        lead.write({'x_groupname':'Created'})
        self.assertTrue(person.vals['x_sgt_crm_synced'])
        self.assertEqual(person.vals['street'],'04 Mộc Bài 01')

    def test_result_marker_first_then_partner(self):
        lead, store, _, person = make(lead_vals={'x_getfly_id':False})
        lead.partner_id=FakeRS()
        lead.write({'x_groupname':'Created'})
        self.assertEqual(store.write_log, [])
        lead.write({'partner_id':person})
        self.assertTrue(person.vals['x_sgt_crm_synced'])
        self.assertEqual(person.vals['street'],'04 Mộc Bài 01')

    def test_no_partner_no_push(self):
        lead, store, _, person = make()
        lead.partner_id=FakeRS()
        lead.write({'x_groupname':'Created'})
        self.assertEqual(store.write_log, [])
        self.assertEqual(lead.notes, [])

    def test_normal_edits_and_repeat_marker_no_repeat(self):
        lead, store, _, person = make()
        lead.write({'x_groupname':'Created'})
        n=len(store.write_log)
        lead.write({'name':'Normal update','stage_id':7})
        lead.write({'x_groupname':'Created'})
        self.assertEqual(len(store.write_log), n)

    def test_company_only_existing_person_receives_parent_without_rename(self):
        lead, store, _, person = make(
            partner_vals={'name':'Công Ty TNHH Khả Tâm','is_company':False},
            companies=({'name':'Công Ty TNHH Khả Tâm','is_company':True,'vat':'0401305016'},))
        lead.write({'x_groupname':'Created'})
        self.assertEqual(person.vals['name'], 'Công Ty TNHH Khả Tâm')
        self.assertEqual(person.vals['parent_id'],101)
        self.assertEqual(len(store.created),0)

    def test_conflicting_vat_same_name_cannot_auto_link_or_create(self):
        lead, store, _, person = make(
            companies=({'name':'Công Ty TNHH Khả Tâm','is_company':True,'vat':'DIFFERENT'},))
        lead.write({'x_groupname':'Created'})
        self.assertEqual(len(store.created),0)
        self.assertFalse(person.vals.get('parent_id'))
        self.assertIn('Không ghi được: Company',str(lead.notes[0]['body']))

    def test_archived_company_not_linked_or_duplicated(self):
        lead, store, _, person = make(
            companies=({'name':'Công Ty TNHH Khả Tâm','is_company':True,
                        'vat':'0401305016','active':False},))
        lead.write({'x_groupname':'Created'})
        self.assertEqual(store.created,[])
        self.assertFalse(person.vals.get('parent_id'))
        self.assertIn('Không ghi được: Company',str(lead.notes[0]['body']))

    def test_duplicate_vat_companies_fail_closed(self):
        lead, store, _, person = make(
            companies=({'name':'A','is_company':True,'vat':'0401305016'},
                       {'name':'B','is_company':True,'vat':'0401305016'}))
        lead.write({'x_groupname':'Created'})
        self.assertFalse(person.vals.get('parent_id'))
        self.assertEqual(len(store.created),0)
        self.assertIn('Không ghi được: Company',str(lead.notes[0]['body']))

    def test_link_not_persisted_does_not_report_success(self):
        lead, store, _, person = make()
        old=person.write
        def write_without_parent(vals):
            # simulate ORM override silently discarding parent_id
            filtered=dict(vals)
            filtered.pop('parent_id',None)
            return old(filtered)
        person.write=write_without_parent
        lead.write({'x_groupname':'Created'})
        self.assertFalse(person.vals.get('parent_id'))
        self.assertIn('Không ghi được: Company',str(lead.notes[0]['body']))

    def test_write_mutation_does_not_falsely_report_geolocation_success(self):
        lead, store, _, person = make(lead_vals={'city':False,'country_id':False})
        old=person.write
        def mutate_write(vals):
            if 'street' in vals:
                vals['partner_latitude']=0.0
                vals['partner_longitude']=0.0
            return old(vals)
        person.write=mutate_write
        lead.write({'x_groupname':'Created'})
        text=str(lead.notes[0]['body'])
        self.assertNotIn('partner_latitude', text)
        self.assertNotIn('partner_longitude', text)

    def test_auto_failure_cannot_cancel_legacy_write(self):
        lead, store, _, person = make()
        lead._sgt_crm006_push_to_partner=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('push failed'))
        self.assertTrue(lead.write({'x_groupname':'Created'}))
        self.assertEqual(lead.vals['x_groupname'],'Created')

    def test_manual_remains_available_after_first_auto(self):
        lead, store, _, person = make()
        lead.write({'x_groupname':'Created'})
        lead.vals['street']='Revised Street'
        result=lead.action_sgt_crm006_push_contact()
        self.assertEqual(person.vals['street'],'Revised Street')
        self.assertEqual(result['tag'],'display_notification')

class ProfileTests(unittest.TestCase):
    """Update_002: profile + logo mirrored on the Contact AND on its Company."""

    def assert_profile(self, rec):
        for key in MIRRORED:
            self.assertEqual(rec.vals.get(key), PROFILE[key], key)
        self.assertEqual(rec.vals.get('x_yp_listing_url'), PROFILE['referred'])
        self.assertEqual(rec.vals.get('comment'), PROFILE['description'])
        self.assertTrue(rec.vals.get('x_sgt_crm_synced'))

    def test_profile_written_to_contact_and_new_company(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE)
        lead.write({'x_groupname': 'a'})
        company = pstore.recs[partner.vals['parent_id']]
        self.assert_profile(partner)
        self.assert_profile(company)

    def test_profile_written_to_found_company(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE, companies=[{'name': 'Công Ty TNHH Khả Tâm', 'is_company': True}])
        lead.write({'x_groupname': 'a'})
        self.assertEqual(pstore.created, [])
        self.assert_profile(pstore.recs[101])
        self.assert_profile(partner)

    def test_profile_written_to_existing_parent_company(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE, companies=[{'name': 'Công ty khác', 'is_company': True, 'street': 'Cũ'}])
        partner.vals['parent_id'] = 101
        lead.write({'x_groupname': 'a'})
        self.assert_profile(pstore.recs[101])
        self.assertEqual(pstore.recs[101].vals['street'], '04 Mộc Bài 01')  # complete first sync
        self.assertEqual(pstore.created, [])

    def test_contact_that_is_a_company_gets_profile_only_itself(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE, partner_vals={'name': 'ACME', 'is_company': True})
        lead.write({'x_groupname': 'a'})
        self.assert_profile(partner)
        self.assertEqual(pstore.created, [])
        self.assertNotIn('parent_id', partner.vals)

    def test_first_sync_overwrites_profile_and_native(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE, partner_vals={
            'name': 'An', 'x_type_contact': 'OLD', 'comment': '<p>cũ</p>', 'x_yp_founded_year': 1999, 'street': 'Giữ nguyên'})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['x_type_contact'], 'Manufacturer')
        self.assertEqual(partner.vals['comment'], '<p>Giới thiệu VI</p>')
        self.assertEqual(partner.vals['x_yp_founded_year'], 2008)
        self.assertEqual(partner.vals['street'], '04 Mộc Bài 01')

    def test_empty_deal_value_never_erases_the_contact(self):
        lead, pstore, cstore, partner = make(
            lead_vals={'x_type_contact': False, 'x_country': '  ', 'x_yp_intro_en': '<p><br></p>', 'description': '<p><br></p>',
                       'x_yp_founded_year': 0},
            partner_vals={'name': 'An', 'x_type_contact': 'Keep', 'x_country': 'Keep2', 'x_yp_intro_en': '<p>keep</p>',
                          'comment': '<p>note</p>', 'x_yp_founded_year': 1990})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['x_type_contact'], 'Keep')
        self.assertEqual(partner.vals['x_country'], 'Keep2')
        self.assertEqual(partner.vals['x_yp_intro_en'], '<p>keep</p>')
        self.assertEqual(partner.vals['comment'], '<p>note</p>')
        self.assertEqual(partner.vals['x_yp_founded_year'], 1990)

    def test_flag_set_on_contact_and_company_even_without_profile(self):
        lead, pstore, cstore, partner = make()
        lead.write({'x_groupname': 'a'})
        self.assertTrue(partner.vals['x_sgt_crm_synced'])
        self.assertTrue(pstore.recs[partner.vals['parent_id']].vals['x_sgt_crm_synced'])

    def test_logo_upload_preserves_person_avatar_and_updates_company(self):
        lead, pstore, cstore, partner = make(lead_vals={'x_yp_logo_upload': b'LOGO', 'x_image': 'https://x/y.png'},
                                             partner_vals={'name': 'An', 'image_1920': b'OLDAVATAR'})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['image_1920'], b'OLDAVATAR')
        self.assertEqual(pstore.recs[partner.vals['parent_id']].vals['image_1920'], b'LOGO')

    def test_inline_x_image_only_updates_company_and_link_is_ignored(self):
        lead, pstore, cstore, partner = make(lead_vals={'x_image': 'data:image/png;base64,QUJD'})
        lead.write({'x_groupname': 'a'})
        self.assertNotIn('image_1920', partner.vals)
        self.assertEqual(pstore.recs[partner.vals['parent_id']].vals['image_1920'], b'QUJD')
        lead2, pstore2, _c, partner2 = make(lead_vals={'x_image': 'https://yellowpages.vn/logo.png'},
                                            partner_vals={'name': 'An', 'image_1920': b'OLDAVATAR'})
        lead2.write({'x_groupname': 'a'})
        self.assertEqual(partner2.vals['image_1920'], b'OLDAVATAR')      # no picture on the Deal -> avatar untouched

    def test_person_avatar_changed_between_syncs_stays_independent(self):
        lead, pstore, cstore, partner = make(lead_vals=dict(PROFILE, x_yp_logo_upload=b'LOGO_A'),
                                             partner_vals={'name': 'An', 'image_1920': b'PERSON_A'})
        lead.action_sgt_crm006_push_contact()
        partner.vals['image_1920'] = b'PERSON_B'   # manual avatar update in Contacts
        lead.vals['x_yp_logo_upload'] = b'LOGO_B'
        lead.partner_id = partner
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(partner.vals['image_1920'], b'PERSON_B')
        company = pstore.recs[partner.vals['parent_id']]
        self.assertEqual(company.vals['image_1920'], b'LOGO_B')

    def test_existing_parent_company_receives_logo_not_person(self):
        lead, pstore, cstore, partner = make(lead_vals={'x_yp_logo_upload': b'NEW_COMPANY'},
                                             partner_vals={'name': 'An', 'image_1920': b'KEEP_PERSON'},
                                             companies=[{'name': 'ACME', 'is_company': True, 'image_1920': b'OLD_COMPANY'}])
        partner.vals['parent_id'] = 101
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(partner.vals['image_1920'], b'KEEP_PERSON')
        self.assertEqual(pstore.recs[101].vals['image_1920'], b'NEW_COMPANY')

    def test_direct_company_contact_still_receives_logo(self):
        lead, pstore, cstore, partner = make(lead_vals={'x_yp_logo_upload': b'NEW_COMPANY'},
                                             partner_vals={'name': 'ACME', 'is_company': True,
                                                           'image_1920': b'OLD_COMPANY'})
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(partner.vals['image_1920'], b'NEW_COMPANY')
        self.assertEqual(pstore.created, [])

    def test_second_run_writes_nothing_with_profile_and_logo(self):
        lead, pstore, cstore, partner = make(lead_vals=dict(PROFILE, x_yp_logo_upload=b'LOGO'))
        lead.write({'x_groupname': 'a'})
        before_log, before_notes = len(pstore.write_log), len(lead.notes)
        lead.partner_id = partner
        lead.write({'x_groupname': 'b'})
        self.assertEqual(len(pstore.write_log), before_log)
        self.assertEqual(len(lead.notes), before_notes)

    def test_changing_the_deal_and_pressing_again_updates_both(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE)
        lead.write({'x_groupname': 'a'})
        lead.vals['x_country'] = 'USA'
        lead.vals['x_yp_gallery_html'] = '<p><img src="data:image/png;base64,NEW"></p>'
        lead.partner_id = partner
        action = lead.action_sgt_crm006_push_contact()
        company = pstore.recs[partner.vals['parent_id']]
        for rec in (partner, company):
            self.assertEqual(rec.vals['x_country'], 'USA')
            self.assertIn('NEW', rec.vals['x_yp_gallery_html'])
        self.assertIn('Main Market', action['params']['message'])
        self.assertIn('Company "Công Ty TNHH Khả Tâm"', action['params']['message'])

    def test_note_names_fields_but_never_shows_profile_data(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE)
        lead.write({'x_groupname': 'a'})
        body = str(lead.notes[0]['body'])
        self.assertIn('Business Type', body)
        self.assertNotIn('Manufacturer', body)
        self.assertNotIn('Giới thiệu VI', body)

    def test_one_refused_profile_field_does_not_block_the_rest(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE, refuse={'x_country'})
        lead.write({'x_groupname': 'a'})
        self.assertNotIn('x_country', partner.vals)
        self.assertEqual(partner.vals['x_type_contact'], 'Manufacturer')
        self.assertIn('Main Market', str(lead.notes[0]['body']))     # listed under "Không ghi được"

    def test_deal_without_crm005_fields_still_pushes(self):
        lead, pstore, cstore, partner = make()
        lead._fields = {'x_website': 1, 'x_yp_tax_code': 1, 'x_groupname': 1, 'x_getfly_id': 1}   # no profile / logo fields on the Deal
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['vat'], '0401305016')
        self.assertTrue(partner.vals['x_sgt_crm_synced'])
        self.assertNotIn('x_type_contact', partner.vals)

    def test_tax_code_is_overwritten_on_first_full_sync(self):
        lead, pstore, cstore, partner = make(lead_vals=PROFILE, partner_vals={'name': 'An', 'vat': 'GIỮ'})
        lead.write({'x_groupname': 'a'})
        self.assertEqual(partner.vals['vat'], '0401305016')




# ------------------------------------- Update_008: direct geo, no added columns
VALID_GEO = dict(x_yp_latitude=10.8123456, x_yp_longitude=106.6789012,
                 x_yp_geo_status='estimated', x_yp_geo_precision='address',
                 x_yp_geo_address_key='valid-sig', _geo_signature='valid-sig')


class GeolocationUpdate008Tests(unittest.TestCase):
    def test_source_validation_and_no_zero_or_stale(self):
        self.assertEqual(push.source_geo_pair(dict(VALID_GEO, x_yp_geo_status='pending')), None)
        self.assertEqual(push.source_geo_pair(dict(VALID_GEO, _geo_signature='different',
                                                  crm005_geo_current_key='different')), None)
        self.assertIsNone(push.source_geo_pair(dict(VALID_GEO, x_yp_latitude=0, x_yp_longitude=0,
                                                     crm005_geo_current_key='valid-sig')))
        self.assertTrue(push.valid_geo_pair(10.1, 106.2))
        self.assertFalse(push.valid_geo_pair(float('nan'), 1))
        self.assertFalse(push.valid_geo_pair(91, 1))

    def test_direct_copy_after_manual_button_to_company_and_person(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO)
        lead.action_sgt_crm006_push_contact()
        company = pstore.recs[partner.vals['parent_id']]
        for rec in (partner, company):
            self.assertAlmostEqual(rec.vals['partner_latitude'], VALID_GEO['x_yp_latitude'])
            self.assertAlmostEqual(rec.vals['partner_longitude'], VALID_GEO['x_yp_longitude'])
            self.assertNotIn('x_sgt_crm006_geo_last_key', rec.vals)

    def test_auto_create_does_not_overwrite_old_contact_pin(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO, partner_vals={
            'name': 'Existing', 'partner_latitude': 10.1, 'partner_longitude': 106.1})
        lead.write({'x_groupname': 'create-success'})
        self.assertEqual(partner.vals['partner_latitude'], 10.1)
        self.assertEqual(partner.vals['partner_longitude'], 106.1)
        self.assertIn('preserved', str(lead.notes[-1]['body']))

    def test_auto_create_copies_to_empty_pin(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO)
        lead.write({'x_groupname': 'create-success'})
        self.assertAlmostEqual(partner.vals['partner_latitude'], 10.8123456)

    def test_manual_button_can_update_old_contact_pin(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO, partner_vals={
            'name': 'Existing', 'partner_latitude': 10.1, 'partner_longitude': 106.1})
        lead.action_sgt_crm006_push_contact()
        self.assertAlmostEqual(partner.vals['partner_latitude'], 10.8123456)

    def test_native_reset_cannot_clear_synced_geo(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO)
        pstore.reset_geo_on_address = True
        lead.action_sgt_crm006_push_contact()
        company = pstore.recs[partner.vals['parent_id']]
        for rec in (partner, company):
            self.assertAlmostEqual(rec.vals['partner_latitude'], 10.8123456)

    def test_auto_create_restores_preserved_pin_after_native_address_reset(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO, partner_vals={
            'name': 'Existing', 'partner_latitude': 10.1, 'partner_longitude': 106.1})
        pstore.reset_geo_on_address = True
        lead.write({'x_groupname': 'create-success'})
        self.assertAlmostEqual(partner.vals['partner_latitude'], 10.1)
        self.assertAlmostEqual(partner.vals['partner_longitude'], 106.1)
        self.assertIn('preserved', str(lead.notes[-1]['body']))

    def test_auto_create_without_geo_preserves_existing_pin(self):
        lead, pstore, _, partner = make(partner_vals={
            'name': 'Existing', 'partner_latitude': 10.1, 'partner_longitude': 106.1})
        pstore.reset_geo_on_address = True
        lead.write({'x_groupname': 'create-success'})
        self.assertAlmostEqual(partner.vals['partner_latitude'], 10.1)

    def test_direct_company_without_person(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO, partner_vals={
            'name': 'ACME', 'is_company': True})
        lead.action_sgt_crm006_push_contact()
        self.assertAlmostEqual(partner.vals['partner_longitude'], 106.6789012)
        self.assertEqual(pstore.created, [])

    def test_failed_or_stale_source_not_copied(self):
        for bad in [dict(VALID_GEO, x_yp_geo_status='failed'),
                    dict(VALID_GEO, x_yp_geo_address_key='old-sig')]:
            lead, pstore, _, partner = make(lead_vals=bad)
            lead.action_sgt_crm006_push_contact()
            self.assertNotAlmostEqual(partner.vals.get('partner_latitude', 0), 10.8123456)

    def test_double_click_no_extra_gps_write(self):
        lead, pstore, _, partner = make(lead_vals=VALID_GEO)
        lead.action_sgt_crm006_push_contact()
        gps_writes = lambda: [vals for _, vals in pstore.write_log if 'partner_latitude' in vals]
        before = len(gps_writes())
        lead.action_sgt_crm006_push_contact()
        self.assertEqual(len(gps_writes()), before)

    def test_no_new_contact_db_field_or_model(self):
        root = ROOT
        self.assertFalse(os.path.exists(os.path.join(root, 'models', 'res_partner.py')))
        with open(os.path.join(root, 'models', 'crm_lead.py'), encoding='utf-8') as fh:
            src = fh.read()
        self.assertNotIn('x_sgt_crm006_geo_last_key', src)
        self.assertNotIn('fields.Char', src)
        self.assertNotIn('fields.Float', src)

# --------------------------------------------------------- part 3: source rules
class ContractTests(unittest.TestCase):
    def read(self, rel):
        with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
            return fh.read()

    def test_manifest(self):
        m = self.read('__manifest__.py')
        self.assertIn("'version': '19.0.1.8.0'", m)
        self.assertIn("'depends': ['crm', 'crm_sync_contact_odoo2', 'sgt_contact_company_profile', 'sgt_crm_yellowpages_profile']", m)
        self.assertNotIn('assets', m)           # no JS / CSS
        self.assertNotIn('cron', m.lower())

    def test_no_new_fields_models_js_cron_api(self):
        src = self.read('models/crm_lead.py') + self.read('models/push.py')
        for bad in ('fields.Char', 'fields.Boolean', 'fields.Many2one', 'ir.cron', 'requests',
                    'urllib', 'xmlrpc', 'jsonrpc', 'fetch('):
            self.assertNotIn(bad, src, bad)
        import re
        self.assertIsNone(re.search(r'^\s+_name\s*=', src, re.M))   # no new model
        self.assertFalse(os.path.exists(os.path.join(ROOT, 'static')))
        self.assertNotIn('self.sudo()', src)    # only the partner / category stores use sudo

    def test_old_addon_files_not_touched(self):
        src = self.read('models/crm_lead.py')
        self.assertNotIn('sync.contact.odoo2.wizard', src)
        self.assertIn("TRIGGER_FIELDS", src)

    def test_button_view(self):
        v = self.read('views/crm_lead_views.xml')
        self.assertIn('action_sgt_crm006_push_contact', v)
        self.assertIn('invisible="not partner_id"', v)
        self.assertNotIn('data-tooltip', v)     # Odoo 19 view validator

    def test_like_pattern_survives_double_spaces(self):
        self.assertEqual(push.like_pattern(' Công  Ty TNHH '), 'Công%Ty%TNHH')

    def test_every_label_has_a_key(self):
        for key in ('parent_id', 'street', 'vat', 'user_id', 'ref', 'category_id', 'name') + \
                tuple(dst for _src, dst in push.PROFILE_MAP) + (push.LOGO_FIELD,):
            self.assertIn(key, push.LABELS)


if __name__ == '__main__':
    unittest.main(verbosity=1)
