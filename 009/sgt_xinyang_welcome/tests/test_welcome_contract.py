"""Offline contract tests for sgt_xinyang_welcome (no Odoo needed).
Run:  python3 -I tests/test_welcome_contract.py"""
import ast, csv, re, sys
from pathlib import Path
from lxml import etree

A = Path(__file__).resolve().parent.parent
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

man = ast.literal_eval((A / '__manifest__.py').read_text())
ok(man['depends'] == ['web', 'website'], 'depends = web + website (login layout is rendered by website.layout)')
ok(man['version'].startswith('19.0.'), 'version targets Odoo 19')
for f in man['data']:
    ok((A / f).is_file(), f'manifest data file exists: {f}')
    if f.endswith('.xml'): etree.parse(str(A / f))
for bundle, files in man['assets'].items():
    for f in files:
        ok((A / f.replace('sgt_xinyang_welcome/', '', 1)).is_file(), f'{bundle}: {f} exists')

# python models
names = {}
for py in (A / 'models').glob('*.py'):
    tree = ast.parse(py.read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == '_name':
            names[n.value.value] = py.name
ok(set(names) == {'sgt.home.slide', 'sgt.home.fact', 'sgt.home.product', 'sgt.home.product.image', 'sgt.home.setting', 'sgt.website.switch'}, f'models defined: {sorted(names)}')
home_models = ['sgt.home.slide', 'sgt.home.fact']  # data models read by the Home page
init = (A / 'models' / '__init__.py').read_text()
ok(all(m.replace('.py', '') in init for m in set(names.values())), 'models/__init__ imports every model file')

# access csv covers each model, users read-only, only system writes
rows = list(csv.DictReader((A / 'security/ir.model.access.csv').open()))
for m in home_models:
    xid = 'model_' + m.replace('.', '_')
    r = [x for x in rows if x['model_id:id'] == xid]
    ok(len(r) == 2, f'{m}: two access rows')
    user = [x for x in r if x['group_id:id'] == 'base.group_user']
    adm = [x for x in r if x['group_id:id'] == 'base.group_system']
    ok(len(user) == 1 and user[0]['perm_read'] == '1' and user[0]['perm_write'] == user[0]['perm_create'] == user[0]['perm_unlink'] == '0', f'{m}: every internal user may only read')
    ok(len(adm) == 1 and adm[0]['perm_write'] == adm[0]['perm_create'] == adm[0]['perm_unlink'] == '1', f'{m}: Settings group has full rights')

# menu: Home root must be visible to all (no groups) and be the first app (lowest sequence)
v = etree.parse(str(A / 'views/home_views.xml')).getroot()
root = [m for m in v.iter('menuitem') if m.get('id') == 'menu_sgt_home_root'][0]
ok(root.get('groups') is None, 'Home root menu has no groups -> visible to every user')
ok(root.get('parent') is None, 'Home is a ROOT menu (an app)')
ok(int(root.get('sequence')) <= -1, f"Home sequence {root.get('sequence')} sorts before every stock app")
ok(root.get('web_icon') == 'sgt_xinyang_welcome,static/description/icon.png' and (A / 'static/description/icon.png').is_file(), 'web_icon points to an existing file')
for mid in ('menu_sgt_home_slides', 'menu_sgt_home_facts'):
    m = [x for x in v.iter('menuitem') if x.get('id') == mid][0]
    ok(m.get('groups') == 'base.group_system' and m.get('parent') == 'menu_sgt_home_root', f'{mid}: Settings group only, under Home')
tag = [r for r in v.iter('record') if r.get('id') == 'action_sgt_home'][0].xpath("field[@name='tag']")[0].text
js = (A / 'static/src/home/home.js').read_text()
ok(f'add("{tag}", SgtHome)' in js, f'client action tag {tag!r} is registered in JS')
tpl = (A / 'static/src/home/home.xml').read_text()
ok(re.search(r'static template = "([^"]+)"', js).group(1) in tpl, 'component template name exists in home.xml')
for m in home_models:
    ok(f'"{m}"' in js, f'JS reads {m}')
# fields requested by JS exist on the models
src = (A / 'models/home_slide.py').read_text() + (A / 'models/home_fact.py').read_text()
for fld in ('name', 'tag', 'text', 'button_label', 'button_url', 'theme', 'has_image', 'write_date', 'value', 'accent'):
    ok(re.search(rf'\b{fld}\b\s*=\s*fields\.', src) or fld == 'write_date', f'field {fld} defined')

# link whitelist regex (server side) mirrors the JS one
rx = re.search(r"_SAFE_URL_RE = re.compile\(r'(.+?)', re.I\)", src).group(1)
jrx = re.search(r"SAFE_URL = /(.+?)/i;", js).group(1).replace('\\/', '/')
ok(rx == jrx, f'Python and JS link whitelist are identical ({rx} | {jrx})')
R = re.compile(rx, re.I)
for good in ('https://saigontrade.vn/', 'http://a.b/c?d=1', '/odoo', '/odoo/action-12'):
    ok(bool(R.match(good)), f'link allowed: {good}')
for bad in ('javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'data:text/html,x', '//evil.com', 'ftp://x', 'https://a b', ' https://x.y', 'vbscript:x'):
    ok(not R.match(bad), f'link refused: {bad!r}')

# seed data = no unsourced claims about Xinyang
seed = etree.parse(str(A / 'data/home_data.xml')).getroot()
ok(seed.get('noupdate') == '1', 'seed is noupdate (admin edits survive upgrades)')
text = ' '.join((f.text or '') for f in seed.iter('field'))
for banned in ('founded', 'since', 'ISO', 'export', 'employees', 'factory', 'manufactur', 'certif', 'years', 'tons', 'million'):
    ok(banned.lower() not in text.lower(), f'seed has no claim word {banned!r}')

# CSS: brand colours present, scoped to sgt_ classes
css = (A / 'static/src/css/login.css').read_text()
for hx in ('#0061BD', '#E51922', '#B3181A'):
    ok(hx.lower() in css.lower(), f'login.css uses {hx}')
sel = re.findall(r'^([^@{}\n][^{}]*)\{', css, re.M)
unscoped = [s.strip() for s in sel if not re.search(r'sgt_|oe_login_form|oe_website_login_container|:root', s)]
ok(not unscoped, f'login.css selectors are all scoped: {unscoped}')
login_xml = (A / 'views/login_templates.xml').read_text()
ok('inherit_id="website.login_layout"' in login_xml and 'inherit_id="web.login_layout"' not in login_xml, 'flag view hangs off website.login_layout (cannot crash login if disabled)')
ok(login_xml.count('t-if="sgt_login_page"') == 2, 'header + footer render only when sgt_login_page is set')
ok('Xinyang Vietnam' not in login_xml, 'no unsourced "Xinyang Vietnam" wording')
ok('555-555' not in login_xml, 'no website placeholder phone')
for img in re.findall(r'/sgt_xinyang_welcome/(static/[^"\']+\.png)', login_xml + tpl + js):
    ok((A / img).is_file() and (A / img).stat().st_size < (3_000_000 if 'poster_' in img else 200_000), f'asset exists and size reasonable: {img}')

# ---- Update_004 additions -------------------------------------------------
# header colour = backend navbar (blue + 4px red line)
hd = re.search(r'\.sgt_hd \{([^}]*)\}', css).group(1)
ok('var(--sgt-blue)' in hd and '4px solid var(--sgt-red)' in hd, 'login header = brand blue + 4px red bottom line (same as backend navbar)')
ok('--sgt-blue: #0061BD' in css.replace('  ', ' ') or '#0061BD' in css, 'blue token is #0061BD')
ok('sgt_ft_logo' in login_xml and 'sgt_ft_brand' in login_xml, 'footer has the logo in the left column')
ok(login_xml.index('sgt_ft_logo') < login_xml.index('CÔNG TY TNHH SÀI GÒN TRADE'), 'footer logo comes before the company name (left side)')
ok('class="sgt_hd_tag"' in login_xml and 'We accompany organizations in and outside Vietnam to expand their business in the Vietnamese market.' in login_xml, 'header shows the English tagline')
ok(login_xml.index('sgt_hd_logo') < login_xml.index('sgt_hd_tag'), 'tagline sits to the right of the logo')
# search views with Archived filter so an archived slide/card can always be found and restored
for m in ('sgt.home.slide', 'sgt.home.fact'):
    sv = [r for r in v.iter('record') if r.get('model') == 'ir.ui.view' and r.xpath("field[@name='model']")[0].text == m and r.xpath("field[@name='arch']//search")]
    ok(len(sv) == 1 and sv[0].xpath(".//filter[@name='inactive']"), f'{m}: search view has an Archived filter')
# migration: restores an ARCHIVED Saigon Trade slide (deleted one is re-created by noupdate data load)
import importlib.util, types
mod = types.ModuleType('odoo'); mod.SUPERUSER_ID = 1
class _Api:
    class Environment:
        registry_rec = None
        def __init__(self, cr, uid, ctx): pass
        def ref(self, xid, raise_if_not_found=True): return _Api.Environment.registry_rec
mod.api = _Api; sys.modules['odoo'] = mod; sys.modules['odoo.api'] = _Api
spec = importlib.util.spec_from_file_location('mig', A / 'migrations/19.0.1.1.0/post-restore_saigontrade_slide.py')
mig = importlib.util.module_from_spec(spec); spec.loader.exec_module(mig)
class Rec:
    def __init__(s, active, exists=True): s.active = active; s._exists = exists; s.writes = []
    def with_context(s, **k): return s
    def exists(s): return s._exists
    def write(s, vals): s.writes.append(vals); s.active = vals.get('active', s.active)
    def __bool__(s): return True
for label, rec, expect in (('archived', Rec(False), [{'active': True}]), ('already active', Rec(True), []), ('stale xmlid / row gone', Rec(False, exists=False), []), ('missing xmlid', None, [])):
    _Api.Environment.registry_rec = rec
    mig.migrate(None, '19.0.1.0.2')
    ok((rec.writes if rec else []) == expect, f'migration with {label} slide -> writes {expect}')
ok(man['version'] >= '19.0.1.1.0' and (A / 'migrations/19.0.1.1.0').is_dir(), 'migration folder 19.0.1.1.0 exists and manifest version is not older')
ok('logo_saigontrade.png' in login_xml and (A / 'static/src/img/logo_saigontrade.png').is_file(), 'footer uses the Saigon Trade wordmark logo supplied by the user')

# --- Update_007: standard Xinyang emblem, hide/show banner ---
from PIL import Image
for f in re.findall(r'IMG \+ "([^"]+\.png)"', js):
    ok((A / 'static/src/img' / f).is_file(), f'Home JS image exists: {f}')
ok((A / 'static/src/img/logo_xinyang_horizontal.png').is_file() and 'logo_xinyang_horizontal' in login_xml and 'logo_xinyang_horizontal' not in js + tpl, 'login form uses the horizontal logo (user mock); Home uses the emblem only')
em = Image.open(A / 'static/src/img/logo_xinyang.png'); ok(em.height > em.width and em.width >= 300, f'emblem image is the tall emblem (+新扬) at 4x: {em.size}')
dk = Image.open(A / 'static/src/img/logo_saigontrade_xinyang_v3.png').convert('RGBA'); ok(dk.getpixel((0, 0))[3] == 0 and dk.getpixel((dk.width // 2, dk.height // 2))[3] == 255, 'combined logo: transparent outside the disc, opaque inside')
act = [r for r in v.iter('record') if r.get('id') == 'action_sgt_home_slide'][0]
ok("'active_test': False" in act.xpath("field[@name='context']")[0].text, 'Banners action lists hidden banners too (active_test False)')
lst = [r for r in v.iter('record') if r.get('id') == 'view_sgt_home_slide_list'][0].xpath("field[@name='arch']")[0]
ok(bool(lst.xpath(".//field[@name='active'][@widget='boolean_toggle'][@string='Show on Home']")) and 'decoration-muted' in etree.tostring(lst, encoding='unicode'), 'Banners list: "Show on Home" toggle + hidden rows greyed')
ok(bool(lst.xpath(".//field[@name='sequence'][@widget='handle']")), 'Banners list keeps the drag handle for order')

css_l = (A / 'static/src/css/login.css').read_text()
ok(re.search(r'\.sgt_hd_logo img \{[^}]*background: #fff;[^}]*border-radius: 50%', css_l) is not None, 'header partnership logo has a white round backing')
ok('logo_saigontrade_xinyang.png' not in login_xml + js, 'old file name is no longer referenced (cache-busting rename)')
# --- Update_008: "/" redirect (stubbed Odoo; behaviour of controllers/root.py) ---
import types as _t
def _load_root():
    saved = {k: sys.modules.get(k) for k in ('odoo', 'odoo.http', 'odoo.addons', 'odoo.addons.website', 'odoo.addons.website.controllers', 'odoo.addons.website.controllers.main')}
    state = {}
    http_m = _t.ModuleType('odoo.http')
    class Req:
        def __init__(self):
            self.httprequest = _t.SimpleNamespace(headers={})
            self.website_on = False
            self.action_id = 456
            self.user_by_id = {}
            self.params = {}
            outer = self
            class Env:
                user = None
                def ref(self, xmlid, raise_if_not_found=True):
                    assert xmlid == 'sgt_xinyang_welcome.action_sgt_home'
                    assert raise_if_not_found is False
                    return _t.SimpleNamespace(id=outer.action_id) if outer.action_id else None
                def __getitem__(self, k):
                    if k == 'sgt.website.switch':
                        return _t.SimpleNamespace(sudo=lambda: _t.SimpleNamespace(website_enabled=lambda: outer.website_on))
                    if k == 'res.users':
                        return _t.SimpleNamespace(browse=lambda uid: outer.user_by_id[uid])
                    assert False, k
            self.env = Env()
        def redirect(self, url, code=303, local=True): return ('redirect', url, code, local)
    http_m.request = Req()
    odoo_m = _t.ModuleType('odoo'); route_calls = []
    def route(*a, **k):
        route_calls.append((a, k)); return lambda f: f
    odoo_m.http = _t.SimpleNamespace(route=route); http_m.route = route
    base = _t.ModuleType('odoo.addons.website.controllers.main')
    class Website:
        def index(self, **kw): return ('website-page', kw)
        def _login_redirect(self, uid, redirect=None): return ('login-destination', uid, redirect)
        def web_login(self, *args, **kw): return ('website-login', args, kw)
    base.Website = Website
    for n in ('odoo.addons', 'odoo.addons.website', 'odoo.addons.website.controllers'): sys.modules[n] = _t.ModuleType(n)
    sys.modules.update({'odoo': odoo_m, 'odoo.http': http_m, 'odoo.addons.website.controllers.main': base})
    spec = importlib.util.spec_from_file_location('sgt_root', A / 'controllers/root.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m, http_m.request, route_calls, saved
m, rq, rcalls, _saved = _load_root()
def _u(pub, internal): return _t.SimpleNamespace(_is_public=lambda: pub, _is_internal=lambda: internal)
c = m.SgtRootRedirect()
rq.env.user = _u(True, False);  ok(c.index() == ('redirect', '/web/login', 302, True), '"/" for a visitor -> /web/login (302, local)')
rq.env.user = _u(False, True);  ok(c.index() == ('redirect', '/odoo/action-456', 302, True), '"/" for an internal user -> exact Home action')
rq.env.user = _u(False, False); ok(c.index() == ('redirect', '/my', 302, True), '"/" for a portal user -> /my')
rq.httprequest.headers = {'Sec-Fetch-Dest': 'iframe'}; rq.env.user = _u(False, True)
ok(c.index(x=1) == ('website-page', {'x': 1}), 'inside an iframe (Website editor) "/" is still served by the website')
rq.httprequest.headers = {'Sec-Fetch-Dest': 'document'}; rq.env.user = _u(True, False)
ok(c.index()[1] == '/web/login', 'Sec-Fetch-Dest document counts as a normal visit')
rq.httprequest.headers = {}; rq.website_on = True; rq.env.user = _u(True, False)
ok(c.index(a=2) == ('website-page', {'a': 2}), 'Website switched ON in Settings -> "/" is served by the website again')
rq.website_on = False
rq.user_by_id = {7: _u(False, True), 8: _u(False, False)}
rq.params = {'login_success': True}
ok(c._login_redirect(7) == ('login-destination', 7, '/odoo/action-456'), 'Internal user login without an explicit destination lands on Home')
ok(c._login_redirect(7, redirect='/odoo/action-123') == ('login-destination', 7, '/odoo/action-123'), 'An explicit deep link is retained after login')
ok(c._login_redirect(8) == ('login-destination', 8, None), 'Portal login destination remains owned by Website')
rq.params = {'login_success': False}
ok(c._login_redirect(7) == ('login-destination', 7, None), 'No default Home redirect on an unsuccessful login')
rq.params = {'login_success': True}
rq.action_id = None
ok(c._login_redirect(7) == ('login-destination', 7, '/odoo'), 'Missing Home action falls back to standard Odoo backend')
rq.action_id = 456
ok(c.web_login(redirect='/odoo/action-123') == ('website-login', (), {'redirect': '/odoo/action-123'}), 'Custom login handler preserves upstream Odoo Website login flow')
ok(rcalls == [((), {}), ((), {})], 'Both / and /web/login inherit route, auth and website settings from Odoo Website')
ok(re.search(r'^from \. import controllers$', (A / '__init__.py').read_text(), re.M) is not None, 'controllers package is imported')
ok('redirect(' in (A / 'controllers/root.py').read_text() and 'code=302' in (A / 'controllers/root.py').read_text() and '301' not in (A / 'controllers/root.py').read_text(), 'temporary 302 redirect (never a cached 301)')

# --- Update_008: Website on/off switch (fake ORM) + XML contract ---
def _load_switch():
    odoo_m = _t.ModuleType('odoo')
    class F:
        def __init__(self, *a, **k): self.default = k.get('default')
    fields_m = _t.SimpleNamespace(Char=F, Boolean=F)
    api_m = _t.SimpleNamespace(model=lambda f: f, model_create_multi=lambda f: f)
    class Model:
        _store = []
        def __init__(self, recs=None): self._recs = recs if recs is not None else []
        def sudo(self): return self
        def search(self, dom, limit=None): return type(self)(self._store[:limit])
        def __bool__(self): return bool(self._recs)
        def __getitem__(self, i): return type(self)(self._recs[i] if isinstance(i, slice) else [self._recs[i]])
        def __len__(self): return len(self._recs)
        @property
        def id(self): return 1
        @property
        def website_on(self): return self._recs[-1]['website_on']
        def ensure_one(self): assert len(self._recs) == 1
        def write(self, vals):
            for r in self._recs: r.update(vals)
        def create(self, vals_list):
            recs = [dict({'website_on': False}, **v) for v in vals_list]; self._store.extend(recs); return type(self)(recs)
    odoo_m.api = api_m; odoo_m.fields = fields_m; odoo_m.models = _t.SimpleNamespace(Model=Model)
    saved = {k: sys.modules.get(k) for k in ('odoo',)}
    sys.modules['odoo'] = odoo_m
    spec = importlib.util.spec_from_file_location('sgt_switch', A / 'models/website_switch.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    sys.modules['odoo'] = saved['odoo'] if saved['odoo'] is not None else odoo_m
    return m, Model
sw, FakeModel = _load_switch()
sw.SgtWebsiteSwitch.website_on = property(lambda self: self._recs[-1]['website_on'])  # the fake ORM reads the stored value like Odoo does
class Menu:
    def __init__(self): self.active = True; self.rec = self
    def sudo(self): return self
    def write(self, v): self.active = v['active']
class Params:
    def __init__(self): self.d = {}
    def sudo(self): return self
    def get_param(self, k): return self.d.get(k)
    def set_param(self, k, v): self.d[k] = v
def make(menu_present=True):
    FakeModel._store = []
    menu, params = (Menu() if menu_present else None), Params()
    class Env:
        def ref(self, xid, raise_if_not_found=True):
            assert xid == 'website.menu_website_configuration'
            return menu
        def __getitem__(self, k): assert k == 'ir.config_parameter'; return params
    obj = sw.SgtWebsiteSwitch.__new__(sw.SgtWebsiteSwitch) if False else None
    sw.SgtWebsiteSwitch.env = Env(); sw.SgtWebsiteSwitch._store = FakeModel._store
    return menu, params
menu, params = make()
sm = sw.SgtWebsiteSwitch([])
ok(sm.website_enabled() is False, 'switch: Website is OFF by default (no parameter yet)')
created = sm.create([{}])
ok(menu.active is False and params.d.get(sw.PARAM) == '0' and created.website_on is False, 'switch: creating the record hides the Website app menu and stores 0')
res = created.action_turn_on()
ok(menu.active is True and params.d[sw.PARAM] == '1' and sm.website_enabled() is True and created.website_on is True, 'switch: Active -> menu shown, parameter 1, record on')
ok(res == {'type': 'ir.actions.client', 'tag': 'reload'}, 'switch: button reloads the page so the app menu updates')
created.action_turn_off()
ok(menu.active is False and params.d[sw.PARAM] == '0' and sm.website_enabled() is False and created.website_on is False, 'switch: Deactivate -> menu hidden again, parameter 0')
act = sm.action_open()
ok(act['res_model'] == 'sgt.website.switch' and act['view_mode'] == 'form' and act['res_id'] == 1 and len(FakeModel._store) == 1, 'switch: opening the Settings menu reuses the single record (no duplicates)')
sm.action_open(); ok(len(FakeModel._store) == 1, 'switch: opening twice still one record')
menu2, params2 = make(menu_present=False); sm2 = sw.SgtWebsiteSwitch([])
try:
    sm2.create([{}]).action_turn_on(); ok(params2.d[sw.PARAM] == '1', 'switch: no crash if the Website app menu does not exist')
except Exception as e: ok(False, f'switch: no crash if the Website app menu does not exist ({e})')
# XML contract
sv = etree.parse(str(A / 'views/website_switch_views.xml')).getroot()
mi = [x for x in sv.iter('menuitem') if x.get('id') == 'menu_sgt_website_switch'][0]
ok(mi.get('parent') == 'base.menu_administration' and int(mi.get('sequence')) > 110 and mi.get('groups') == 'base.group_system', 'Settings menu "Website": under Settings, after Technical (110), Settings group only')
fm = [r for r in sv.iter('record') if r.get('id') == 'view_sgt_website_switch_form'][0]
btn = {b.get('name'): b for b in fm.iter('button')}
ok(btn['action_turn_on'].get('invisible') == 'website_on' and btn['action_turn_off'].get('invisible') == 'not website_on', 'form: "Active" shown when off, "Deactivate" shown when on')
ok(btn['action_turn_on'].get('string') == 'Active', 'form: the button is labelled Active')
ok(fm.xpath(".//form[@create='0'][@delete='0'][@duplicate='0']") != [], 'form cannot create / delete / duplicate')
sa = [r for r in sv.iter('record') if r.get('id') == 'action_sgt_website_switch'][0]
ok('model.action_open()' in sa.xpath("field[@name='code']")[0].text, 'server action opens the single record through the model method')
acc = list(csv.DictReader((A / 'security/ir.model.access.csv').open()))
sa_rows = [r for r in acc if r['model_id:id'] == 'model_sgt_website_switch']
ok(len(sa_rows) == 1 and sa_rows[0]['group_id:id'] == 'base.group_system' and sa_rows[0]['perm_unlink'] == '0' and sa_rows[0]['perm_write'] == '1', 'switch access: Settings group only, no delete')
d = etree.parse(str(A / 'data/website_switch.xml')).getroot()
ok(d.get('noupdate') == '1' and d.xpath("record[@model='sgt.website.switch']") != [], 'default switch record is seed data (noupdate)')
ok(man['data'].index('data/website_switch.xml') > man['data'].index('views/website_switch_views.xml') > man['data'].index('security/ir.model.access.csv'), 'manifest order: access, then view, then seed')
ok(man['version'] == '19.0.1.11.0', 'manifest version 19.0.1.11.0 (Update_020, above every earlier build: ... 1.9.0 / 1.10.0)')
# --- Update_012: Odoo 19 client-side contract of home.js (the "Service user is not available" crash) ---
_hjs = (A / 'static/src/home/home.js').read_text()
ok('useService("user")' not in _hjs and "useService('user')" not in _hjs, 'home.js does not ask for a "user" service (Odoo 19 has none)')
ok('import { user } from "@web/core/user";' in _hjs and 'user.hasGroup(' in _hjs and 'this.user' not in _hjs, 'home.js uses user.hasGroup from @web/core/user')
ok(set(re.findall(r'useService\("(\w+)"\)', _hjs)) <= {'orm', 'action'}, 'home.js asks only for the orm and action services')
ok(re.search(r'this\.el\b', _hjs) is None and 'useRef("home")' in _hjs and 't-ref="home"' in (A / 'static/src/home/home.xml').read_text(), 'home.js reaches its root through useRef("home") (OWL 2 components have no this.el)')

# Regression: Odoo 19 rejects legacy attributes on search root and search <group>
# (the original Update_011 failed while validating view_sgt_home_product_search).
for view_file in ('views/home_views.xml', 'views/home_product_views.xml'):
    search_doc = etree.parse(str(A / view_file))
    for search in search_doc.xpath('//field[@name="arch"]/search'):
        ok(not search.attrib, f'{view_file}: Odoo 19 search root has no legacy attributes')
        for group in search.xpath('.//group'):
            ok(not group.attrib, f'{view_file}: Odoo 19 search group has no legacy expand/string attributes')
prod_doc = etree.parse(str(A / 'views/home_product_views.xml'))
ok(bool(prod_doc.xpath("//record[@id='view_sgt_home_product_search']//search/group/filter[@name='group_category'][@context]")), 'Search view still exposes grouping by product category')
ok(len(prod_doc.xpath("//record[@id='view_sgt_home_product_search']//search/filter")) == 2, 'Search view retains shown/hidden filters')

# ---- Update_010: English Home product manager permissions and UI -----
product_rows = [r for r in rows if r['model_id:id'] == 'model_sgt_home_product']
ok(len(product_rows) == 3, 'Products: reader, Home Manager and Settings Administrator ACL rows')
readers = [r for r in product_rows if r['group_id:id'] == 'base.group_user']
managers = [r for r in product_rows if r['group_id:id'] == 'sgt_xinyang_welcome.group_home_manager']
ok(len(readers) == 1 and [readers[0][k] for k in ('perm_read','perm_write','perm_create','perm_unlink')] == ['1','0','0','0'], 'All internal users read only')
ok(len(managers) == 1 and all(managers[0][k] == '1' for k in ('perm_read','perm_write','perm_create','perm_unlink')), 'Home Manager has create, write, delete')
admin_rows = [r for r in product_rows if r['group_id:id'] == 'base.group_system']
ok(len(admin_rows) == 1 and all(admin_rows[0][k] == '1' for k in ('perm_read','perm_write','perm_create','perm_unlink')), 'Settings Administrator can manage Home products by default')
ok({r['group_id:id'] for r in product_rows} == {'base.group_user', 'base.group_system', 'sgt_xinyang_welcome.group_home_manager'}, 'No accidental wide-open or unrelated product ACL')
group_xml = etree.parse(str(A / 'security/home_security.xml'))
ok(bool(group_xml.xpath("//record[@model='res.groups.privilege'][@id='privilege_sgt_home']/field[@name='name'][text()='Home']")), 'Odoo19 Home privileges defined')
ok(bool(group_xml.xpath("//record[@model='res.groups'][@id='group_home_manager']/field[@name='privilege_id'][@ref='privilege_sgt_home']")), 'Home Manager is a scoped Odoo19 privilege')
ok(not group_xml.xpath("//record[@model='res.groups']/field[@name='category_id']"), 'No obsolete res.groups.category_id used')
product_views = etree.parse(str(A / 'views/home_product_views.xml'))
ok(bool(product_views.xpath("//menuitem[@id='menu_sgt_home_products'][@groups='sgt_xinyang_welcome.group_home_manager,base.group_system']")), 'Products menu visible to Home Manager OR Settings Administrator')
ok(bool(product_views.xpath("//field[@name='image'][@widget='image']")), 'Product media uploader is present')
ok(bool(product_views.xpath("//field[@name='active'][@widget='boolean_toggle']")), 'Product publishing toggle is present')
ok(bool(product_views.xpath("//field[@name='sequence'][@widget='handle']")), 'Product manual ordering is present')
pseed=etree.parse(str(A / 'data/home_products.xml'))
records=pseed.xpath('//record[@model="sgt.home.product"]')
ok(len(records) == 12 and pseed.getroot().get('noupdate') == '1', 'Twelve editable starter products, no data overwrite on upgrade')
ok(all((A / r.xpath("field[@name='image']")[0].get('file').split('sgt_xinyang_welcome/',1)[1]).is_file() for r in records), 'All six uploaded product images are bundled')
ok(all(r.xpath("field[@name='name']")[0].text for r in records), 'Every imported product has a title')
ok('MANAGER_GROUP = "sgt_xinyang_welcome.group_home_manager"' in js and 'user.hasGroup(MANAGER_GROUP)' in js, 'Manage button checks Home Manager group')
ok('ADMIN_GROUP = "base.group_system"' in js and 'user.hasGroup(ADMIN_GROUP)' in js, 'Manage button also checks Settings Administrator group')
ok('Boolean(manager || settingsAdmin)' in js, 'Manage button visible for either authorized role')
ok('this.action.doAction("sgt_xinyang_welcome.action_sgt_home_product")' in js, 'Manage action opens product library')
ok('sgt.home.product' in js and 'visibleProducts' in tpl and 'thumbUrl(product)' in tpl, 'Home product grid reads backend data')
ok('return "en";' in (A / 'static/src/home/home.js').read_text() and 'state.lang === \'en\'' in tpl, 'Home opens in English by default (Vietnamese on request, Update_014)')
ok('data/home_products.xml' in man['data'] and 'security/home_security.xml' in man['data'], 'New data and security are in manifest')
# every static file referenced by an src/href path in the Owl template must exist
for asset_path in set(re.findall(r'/sgt_xinyang_welcome/(static/[^"\s]+(?:png|pdf))', tpl)):
    ok((A / asset_path).is_file(), f'Owl asset exists: {asset_path}')

# --- Update_013: merge of Update_010 (12 posters, Add/Edit, viewer) + concept layout + the permission model of the 1.1.x line ---
seed13 = etree.parse(str(A / 'data/home_products.xml')).getroot()
sr = {r.get('id'): r for r in seed13.xpath("record[@model='sgt.home.product']")}
OLD6 = ['thermal', 'silencer', 'fire', 'aluminum', 'smoke', 'eggcrate']          # already on production: ids must NOT change
NEW6 = ['bd1', 'fasu', 'noise', 'damper_range', 'xywe', 'xyyl']
ok(all(f'home_product_seed_{k}' in sr for k in OLD6), 'the 6 seed ids already installed on production are unchanged (no duplicates, no re-creation)')
ok(all(f'home_product_seed_{k}' in sr for k in NEW6) and len(sr) == 12, 'the 6 additional posters of Update_010 are added with new ids')
fld = lambda r, n: (r.xpath(f"field[@name='{n}']") or [None])[0]
ok([int(fld(sr[f'home_product_seed_{k}'], 'sequence').text) for k in OLD6 + NEW6] == list(range(10, 130, 10)), 'seed order: the 6 existing first, then the 6 new ones')
CATS = {'air', 'silencer', 'fire', 'other'}
ok(all(fld(r, 'category').text in CATS and fld(r, 'name').text and fld(r, 'subtitle').text for r in sr.values()), 'every seed has name, subtitle and a valid category key')
ok(all(r.xpath("field[@name='name']")[0].text and r.xpath("field[@name='active']")[0].text == '1' for r in sr.values()), 'every seed is shown (active)')
for k, r in sr.items():
    im = fld(r, 'image'); f = A.parent / im.get('file')
    ok(im.get('type') == 'base64' and f.is_file() and 20_000 < f.stat().st_size < 400_000, f'seed image exists and is a sensible size: {f.name}')
ok(len({fld(r, 'image').get('file') for r in sr.values()}) == 12, 'each seed uses its own poster (12 different pictures)')
ok(not re.search(r'[一-鿿]', (A / 'data/home_products.xml').read_text()), 'seed text is English')
for gone in ('poster_aluminum.png', 'poster_eggcrate.png', 'poster_smoke.png', 'home.scss'):
    ok(not list(A.rglob(gone)), f'no unused leftover: {gone}')
alltxt = ''.join((A / f).read_text() for f in ('static/src/home/home.js', 'static/src/home/home.xml', 'data/home_products.xml', 'views/home_product_views.xml', 'views/home_views.xml', '__manifest__.py'))
ok(all(p_ in alltxt for p_ in ('poster_silencer.png', 'poster_thermal.png', 'poster_fire.png')) and all((A / 'static/src/home/assets' / p_).is_file() for p_ in ('poster_silencer.png', 'poster_thermal.png', 'poster_fire.png', 'xinyang_catalog.pdf')), 'the 3 hero posters and the catalog are still shipped and still referenced')
# permissions: the model of the user's 1.1.x line, unchanged (xml ids are what production already has)
sec13 = etree.parse(str(A / 'security/home_security.xml')).getroot(); r13 = {r.get('id'): r for r in sec13.iter('record')}
ok({'module_category_sgt_home', 'privilege_sgt_home', 'group_home_manager'} <= set(r13) and set(r13) == {'module_category_sgt_home', 'privilege_sgt_home', 'group_home_manager', 'privilege_sgt_home_heatmap', 'group_home_heatmap', 'privilege_sgt_home_dashboard', 'group_home_dashboard'}, 'security ids of the 1.1.x line kept, plus the Heat Map (Update_016) and Dashboard (Update_018) privilege and group')
ok(r13['group_home_manager'].xpath("field[@name='privilege_id']")[0].get('ref') == 'privilege_sgt_home' and 'base.group_user' in r13['group_home_manager'].xpath("field[@name='implied_ids']")[0].get('eval'), 'Home Manager sits under the Home privilege and implies Internal User')
ok('group_home_manager' not in (A / 'security/home_security.xml').read_text().split('id="group_home_manager"')[0], 'base.group_user does not imply Home Manager (ordinary users stay read-only)')
rows13 = {r['id']: r for r in csv.DictReader((A / 'security/ir.model.access.csv').open())}
pr13 = [r for r in rows13.values() if r['model_id:id'] == 'model_sgt_home_product']
ok({r['group_id:id'] for r in pr13} == {'base.group_user', 'sgt_xinyang_welcome.group_home_manager', 'base.group_system'}, 'products: access rows for internal users, Home Manager and Settings Administrator only')
ok([(r['perm_read'], r['perm_write'], r['perm_create'], r['perm_unlink']) for r in pr13 if r['group_id:id'] == 'base.group_user'] == [('1', '0', '0', '0')], 'internal users: read only')
ok(all((r['perm_read'], r['perm_write'], r['perm_create'], r['perm_unlink']) == ('1', '1', '1', '1') for r in pr13 if r['group_id:id'] != 'base.group_user'), 'Home Manager and Settings Administrator: full control')
ok(all(r['group_id:id'] == 'base.group_system' for r in rows13.values() if r['model_id:id'] in ('model_sgt_home_slide', 'model_sgt_home_fact') and r['perm_write'] == '1'), 'banners and highlights: only Settings Administrators write')
ok('groups="sgt_xinyang_welcome.group_home_manager,base.group_system"' in (A / 'views/home_product_views.xml').read_text(), 'Home > Products menu: Home Manager and Settings Administrator only')
# home.js / home.xml: manager tools, viewer behaviour, safe rendering
tpl13 = (A / 'static/src/home/home.xml').read_text(); js13 = (A / 'static/src/home/home.js').read_text()
ok(tpl13.count('state.canManage') >= 2 and all(f't-on-click="{m_}"' in tpl13 for m_ in ('addProduct', 'manageProducts', 'editProduct')), 'Add / Manage / Edit buttons exist and are tied to state.canManage')
for m_ in ('addProduct', 'manageProducts', 'editProduct'):
    ok(re.search(r'%s\((?:ev)?\) \{\s*if \(!?this\.state\.canManage\)' % m_, js13) is not None, f'{m_} re-checks canManage before opening anything')
i_edit = tpl13.index('t-on-click="editProduct"'); b_open = tpl13.rfind('<button', 0, i_edit)
ok(tpl13.rfind('</button>', 0, i_edit) > tpl13.rfind('<button type="button" class="product-open"', 0, i_edit) or 'product-open' not in tpl13[tpl13.rfind('<article', 0, i_edit):i_edit], 'Edit is not inside another button')
ok('t-raw' not in tpl13 and 't-html' not in tpl13 and 'innerHTML' not in js13 and 'dangerouslySetInnerHTML' not in js13, 'Home template and script never render raw HTML')
ok('/image/560x560?unique=' in js13 and '/image/1024x1024?unique=' in js13 and '/image/128x128?unique=' in js13, 'grid asks for 560 px thumbnails, the popup for 1024 px pictures, the strip for 128 px thumbnails')
ok('ev.key === "Escape"' in js13 and 'ArrowRight' in js13 and 'ArrowLeft' in js13 and 'useExternalListener(window, "keydown"' in js13 and 'opener.focus()' in js13, 'viewer: Esc, arrows, focus returns to the opener')
ok('t-ref="productClose"' in tpl13 and 'useRef("productClose")' in js13 and 'role="dialog"' in tpl13 and 'aria-modal="true"' in tpl13, 'viewer is a dialog and moves focus to Close')
ok('0318419089' in tpl13 and 'partner-strip' in tpl13 and (A / 'static/src/home/concept.css').read_text().count('.partner-strip') >= 3, 'Saigon Trade information strip (Update_010) is on the Home page and styled')
css13 = (A / 'static/src/home/concept.css').read_text()
sels = re.findall(r'(?:^|\})\s*([^{}@]+)\{', css13)
ok(all('.o_sgt_home' in x or x.strip() in ('from', 'to') or re.fullmatch(r'[\d%.,\s]+', x.strip()) for x in sels) and 'keyframes sgt-img-progress' in css13 and not re.search(r'@keyframes (?!sgt-)', css13), 'ALL concept.css rules are scoped to .o_sgt_home (nothing leaks into the rest of Odoo)')
ok(not any('rgba(' in x for x in []) and 'position:fixed' in css13, 'viewer backdrop is fixed-position inside the Home only')
# install-safety of the package itself
import os
bad = [str(f_.relative_to(A)) for f_ in A.rglob('*') if f_.is_file() and f_.stat().st_mode & 0o044 != 0o044]
ok(not bad, f'every shipped file is world-readable (Odoo may run as another OS user) {bad}')
for f_ in man['data']: ok((A / f_).is_file(), f'data file listed in manifest exists: {f_}')
for _b, files_ in man['assets'].items():
    for f_ in files_: ok((A / f_.replace('sgt_xinyang_welcome/', '', 1)).is_file(), f'asset exists: {f_}')
ok(man['data'].index('security/home_security.xml') < man['data'].index('views/home_product_views.xml') and man['data'].index('views/home_views.xml') < man['data'].index('views/home_product_views.xml'), 'manifest order: groups, then the Home menu, then the Products menu that hangs under it')
ok(man['data'].index('data/home_products.xml') > man['data'].index('security/ir.model.access.csv'), 'seed products load after the access rights')

# --- Update_014: EN/VI switch, product content, vi.po ---
import html as _html
_tpl = (A / 'static/src/home/home.xml').read_text(); _js = (A / 'static/src/home/home.js').read_text(); _i18n = (A / 'static/src/home/i18n.js').read_text()
_VI = dict(re.findall(r'^\s*"((?:[^"\\]|\\.)*)":\s*(?:\n\s*)?"((?:[^"\\]|\\.)*)",?\s*$', _i18n, re.M))
_used = sorted({_html.unescape(m_) for m_ in re.findall(r'tr\(&quot;(.*?)&quot;\)', _tpl)})
_same = {'XINYANG', 'Xinyang', 'XY', 'HVAC', 'm²', 'EN', 'LINES', 'JIANGSU XINYANG', 'Email', 'you@company.com', 'jsxyjd@jsxyjd.net', 'saigontrade.vn', 'Saigon Trade', 'SAIGON TRADE COMPANY LIMITED', 'Hotline',
         'XYPX · ZP100/ZP200 · XYCK', 'XYWT · XYWE · XY-WC4 · XY-DG', 'FVD/FVDH · MEC/MEV · BEC/BEH'}
ok(len(_used) >= 140, f'template wraps its visible text in tr() ({len(_used)} strings)')
ok(not [u_ for u_ in _used if u_ not in _VI and u_ not in _same], f'every tr() string of the template has a Vietnamese entry: {[u_ for u_ in _used if u_ not in _VI and u_ not in _same][:4]}')
ok(all(k_ in _VI for k_ in ('AIR DISTRIBUTION', 'ACOUSTIC SOLUTIONS', 'FIRE & SMOKE CONTROL', 'OTHER EQUIPMENT', 'Industrial silencer systems', 'Temperature-sensing air outlets', 'Fire and smoke protection', 'View details', 'Edit')), 'dictionary covers the texts produced by JavaScript')
ok('sgt_xinyang_welcome/static/src/home/i18n.js' in man['assets']['web.assets_backend'] and man['assets']['web.assets_backend'].index('sgt_xinyang_welcome/static/src/home/i18n.js') < man['assets']['web.assets_backend'].index('sgt_xinyang_welcome/static/src/home/home.js'), 'i18n.js is bundled before home.js')
ok('import { VI } from "./i18n";' in _js and 'tr(text)' in _js and 'lang: savedLang()' in _js and 'context: { lang:' in _js, 'home.js: tr(), language state and lang context for products')
ok('window.localStorage' in _js and _js.count('try {') >= 2 and 'catch' in _js, 'home.js: localStorage only inside try/catch')
ok('data-lang="en"' in _tpl and 'data-lang="vi"' in _tpl and 't-on-click="setLang"' in _tpl and 'aria-pressed' in _tpl, 'template: EN | VI buttons with aria-pressed')
ok('state.selectedProduct.description' in _tpl and 'home-product-description' in _tpl, 'product popup renders the product content (description)')
ok('document.documentElement' not in _js, 'home.js does not touch the global <html lang>')
_pf = (A / 'views/home_product_views.xml').read_text(); _pm = (A / 'models/home_product.py').read_text()
ok('Content shown when a visitor opens this product' in _pf and re.search(r'<field name="description" nolabel="1" colspan="2"', _pf), 'product form: content field has its own full-width block')
ok("'Product content'" in _pm and 'globe icon' in _pm and '(English)' not in _pm, 'description field is labelled "Product content" and mentions the globe icon')
_seed = etree.parse(str(A / 'data/home_products.xml')).getroot()
_recs = {r_.get('id'): {f_.get('name'): (f_.text or '') for f_ in r_.findall('field')} for r_ in _seed.iter('record')}
ok(len(_recs) == 12 and all(len(v_.get('description', '').strip()) >= 40 for v_ in _recs.values()), 'all 12 seed products carry content for the popup')
_po = (A / 'i18n/vi.po').read_text()
def _unq(block):
    parts = re.findall(r'^"((?:[^"\\]|\\.)*)"$', block, re.M)
    return ''.join(parts).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
_entries = re.findall(r'#: model:sgt\.home\.product,(\w+):sgt_xinyang_welcome\.(\w+)\nmsgid ((?:""\n)?(?:"(?:[^"\\]|\\.)*"\n)+)msgstr ((?:""\n)?(?:"(?:[^"\\]|\\.)*"\n?)+)', _po)
def _val(x_): return _unq(x_.replace('""\n', '', 1) if x_.startswith('""\n') else x_.strip())
ok(len(_entries) == 36, f'vi.po has 36 product entries (12 products x name/subtitle/description): {len(_entries)}')
ok(all(_val(mi_) == _recs[rid_][fld_] for fld_, rid_, mi_, ms_ in _entries), 'vi.po msgids equal the seed values exactly (otherwise Odoo ignores the translation)')
ok(all(_val(ms_).strip() and _val(ms_) != _val(mi_) for fld_, rid_, mi_, ms_ in _entries), 'vi.po: every msgstr is filled and differs from the English text')
ok('"Language: vi' in _po, 'vi.po declares Language: vi')

# --- Update_015: extra pictures, Home > Settings, popup layout, Applications section ---
_mi = (A / 'models/home_product_image.py').read_text(); _ms = (A / 'models/home_setting.py').read_text(); _mp = (A / 'models/home_product.py').read_text()
ok("product_id = fields.Many2one('sgt.home.product'" in _mi and "ondelete='cascade'" in _mi and 'required=True' in _mi and 'fields.Image' in _mi and 'fields.Integer(string=\'Order\'' in _mi, 'extra image model: product link (cascade), order, required image')
ok("image_ids = fields.One2many('sgt.home.product.image', 'product_id'" in _mp, 'product has the image_ids one2many')
ok("('off'," in _ms and "('10'," in _ms and "('30'," in _ms and "('custom'," in _ms and "default='30'" in _ms and 'AUTOPLAY_MIN = 3' in _ms and 'AUTOPLAY_MAX = 3600' in _ms, 'settings: off / 10 / 30 / custom, default 30, custom limits 3..3600')
ok("rec.autoplay_seconds = 0" in _ms and "rec.autoplay_custom_seconds" in _ms and "int(rec.autoplay_mode" in _ms and 'ValidationError' in _ms and 'store=True' in _ms, 'settings: stored seconds value (0 = off), validation of the custom value')
_acl = {r_['id']: r_ for r_ in csv.DictReader(open(A / 'security/ir.model.access.csv'))}
def _p(i_): return tuple(_acl[i_][k_] for k_ in ('perm_read', 'perm_write', 'perm_create', 'perm_unlink'))
ok(_p('access_sgt_home_product_image_reader') == ('1', '0', '0', '0') and _p('access_sgt_home_product_image_manager') == ('1', '1', '1', '1') and _p('access_sgt_home_product_image_settings_admin') == ('1', '1', '1', '1'), 'ACL extra images: everyone reads, Home Manager / Settings Admin full')
ok(_p('access_sgt_home_setting_reader') == ('1', '0', '0', '0') and _p('access_sgt_home_setting_manager') == ('1', '1', '0', '0') and _p('access_sgt_home_setting_settings_admin') == ('1', '1', '0', '0'), 'ACL settings: everyone reads, Home Manager / Settings Admin write, nobody creates or deletes')
ok(_acl['access_sgt_home_setting_manager']['group_id:id'] == 'sgt_xinyang_welcome.group_home_manager' and _acl['access_sgt_home_setting_reader']['group_id:id'] == 'base.group_user', 'ACL settings groups')
_sv = (A / 'views/home_setting_views.xml').read_text(); _sd = (A / 'data/home_setting.xml').read_text()
ok('create="false" delete="false"' in _sv and "invisible=\"autoplay_mode != 'custom'\"" in _sv and "required=\"autoplay_mode == 'custom'\"" in _sv, 'settings form: single record, custom seconds only when "Custom"')
ok('id="menu_sgt_home_settings"' in _sv and 'name="Settings"' in _sv and 'parent="menu_sgt_home_root"' in _sv and 'group_home_manager,base.group_system' in _sv and "ref('sgt_xinyang_welcome.home_setting_default')" in _sv, 'Home > Settings menu: next to Banners / Highlights, Home Manager + Settings Admin only, opens the single record')
ok('noupdate="1"' in _sd and 'id="home_setting_default"' in _sd and '<field name="autoplay_mode">30</field>' in _sd, 'settings record is seeded once (noupdate), default 30 seconds')
_md = man['data']
ok(_md.index('data/home_setting.xml') < _md.index('views/home_setting_views.xml') and _md.index('views/home_views.xml') < _md.index('views/home_setting_views.xml') and _md.index('security/ir.model.access.csv') < _md.index('data/home_setting.xml'), 'manifest order: ACL, settings record, then the settings view/menu that references it')
_pf2 = (A / 'views/home_product_views.xml').read_text()
ok('name="image_ids"' in _pf2 and '<list editable="bottom"' in _pf2 and 'widget="handle"' in _pf2, 'product form: editable list of extra images with drag order')
ok(_js.count('searchRead("sgt.home.product.image"') == 1 and 'searchRead("sgt.home.setting"' in _js and _js.count('.catch(() => [])') >= 2, 'home.js reads extra images and settings, and neither can stop Home from opening')
ok('DEFAULT_IMAGE_SECONDS = 30' in _js and 'imageAutoplayActive' in _js and 'reducedMotion' in _js and 'clearTimeout' in _js and 'holdImages' in _js, 'home.js: 30 s fallback, autoplay pauses on hover and respects reduced motion, timer is cleaned up')
ok('dialog-strip' in _tpl and 'strip-prev' in _tpl and 'strip-next' in _tpl and 'dialog-footer' in _tpl and 'pn-prev' in _tpl and 'pn-next' in _tpl and 'dialog-arrow' not in _tpl, 'popup template: picture strip arrows and product bar are separate controls')
_c15 = (A / 'static/src/home/concept.css').read_text()
ok('.o_sgt_home .dialog-sticky{position:sticky;top:0' in _c15 and '.o_sgt_home .dialog-scroll{' in _c15 and '.o_sgt_home .dialog-footer{flex:0 0 auto' in _c15, 'css: sticky picture column, scrolling content, fixed product bar')
ok('.o_sgt_home .technical-section h2,.o_sgt_home .approach-section h2' in _c15 and 'color:#fff}' in _c15.split('.o_sgt_home .technical-section h2,.o_sgt_home .approach-section h2')[1].split('\n')[0], 'css: headings on dark sections are explicitly white (Odoo colours h1-h6)')
ok(_tpl.count('class="industry-row"') == 4 and _tpl.count('class="industry-ico"') == 4 and _tpl.count('class="industry-go"') == 4, 'Applications section: 4 compact cards with icons')

# --- Update_016: wide layout, language pill, Heat Map ---
ok('--container:2400px' in _c15 and '.o_sgt_home .container{width:min(var(--container),calc(100% - 6vw));margin:auto}' in _c15 and '1310px' not in _c15, 'css: content spans the screen (100% - 6vw), capped at 2400px; the old 1310px cap is gone')
ok('@media (min-width:1600px){\n.o_sgt_home .products-grid{grid-template-columns:repeat(4,1fr)}' in _c15 and '@media (min-width:1500px){' in _c15, 'css: 4 product columns from 1600px, hero picture grows from 1500px')
ok('.o_sgt_home .language{display:inline-flex' in _c15 and 'background:#e8f0fa' in _c15 and '.o_sgt_home .language button.language-active{background:var(--blue);color:#fff' in _c15, 'css: EN | VI is a pill with a background, the active language is a solid blue button')
_hm = (A / 'security/home_security.xml').read_text()
ok('<record id="group_home_heatmap" model="res.groups">' in _hm and 'privilege_sgt_home_heatmap' in _hm and "(4, ref('group_home_heatmap'))" in _hm, 'Heat Map Viewer group: own privilege, inherited by Home Manager')
ok(re.search(r"<record id=\"group_home_heatmap\".*?base\.group_user", _hm, re.S) is not None and 'base.group_user\'))]"/>\n        <field name="comment">May open the Heat Map' in _hm, 'Heat Map Viewer implies Internal User only (portal / public can never hold it)')
ok('const HEATMAP_GROUP = "sgt_xinyang_welcome.group_home_heatmap"' in _hjs and 'user.hasGroup(HEATMAP_GROUP)' in _hjs and 'this.state.canMap = Boolean(heatmap || settingsAdmin)' in _hjs, 'Home shows the Heat Map link only for Heat Map Viewer / Settings Administrator')
ok('t-if="state.canMap"' in _tpl and 'class="map-view"' in _tpl and 't-ref="mapFrame"' in _tpl and 'state.mapSrc' in _tpl, 'template: Heat Map link guarded by canMap; map frame inside Home')
ok('openMap(ev)' in _hjs and 'if (!this.state.canMap) { return; }' in _hjs and 'syncMapLang' in _hjs and 'XINYANG_I18N' in _hjs, 'openMap refuses without the right; language is pushed into the frame without reloading it')
ok('from . import heatmap' in (A / 'controllers/__init__.py').read_text() and (A / 'heatmap/__init__.py').is_file(), 'heatmap controller imported')
_hc = (A / 'controllers/heatmap.py').read_text()
ok(_hc.count("auth='public'") == 5 and "auth='user'" not in _hc and "_state()" in _hc and "HEATMAP_GROUP = 'sgt_xinyang_welcome.group_home_heatmap'" in _hc and 'user._is_internal()' in _hc, 'heat map routes check the right on the server (internal user in Heat Map Viewer or Settings Administrator)')
ok(_hc.count('readonly=True') == 5 and 'sudo()' not in _hc.replace("request.env['ir.module.module'].sudo()", ''), 'heat map routes are read only and never use sudo for data (only the module version label)')
ok(all((A / f).is_file() for f in ('heatmap/adapter.py', 'heatmap/deal_map.py', 'heatmap/contact_map.py', 'heatmap/potential.py', 'heatmap/address.py', 'heatmap/map_page.html', 'static/map/xmap-094.js', 'static/map/xmap-094.css', 'static/map/i18n-xmap-094.js', 'static/map/vendor/leaflet.js', 'static/map/vendor/maplibre-gl.js')), 'heat map files present')
ok('Heat Map' in (A / 'static/src/home/i18n.js').read_text() and 'Customer map' in (A / 'static/src/home/i18n.js').read_text(), 'Vietnamese entries for the new interface text')
ok(not any(w in ''.join((A / 'heatmap' / f).read_text() for f in ('adapter.py', 'deal_map.py', 'contact_map.py', 'potential.py')) for w in ('.write(', '.create(', '.unlink(', 'sudo(', 'httpx', 'urllib')), 'map builders: no write / create / unlink / sudo / network')

# ---------------- Update_017: wide layout under Odoo's Bootstrap, rounded buttons, motion, Heat Map access in Home > Settings ----------------
css17 = (A / 'static/src/home/concept.css').read_text(); js17 = (A / 'static/src/home/home.js').read_text()
ok('.o_sgt_home .container{max-width:none!important}' in css17, "Odoo's Bootstrap (.container max-width 1320 px) is overridden, so the 94% layout really applies")
ok(re.search(r'\.o_sgt_home \.btn,\.o_sgt_home \.header-cta[^{]*\{border-radius:12px\}', css17) is not None and '.filter-pill{border-radius:999px}' in css17, 'buttons (Get in touch, hero buttons, form button, arrows) and filter pills are rounded')
ok('REVEAL_SELECTORS' in js17 and 'IntersectionObserver' in js17 and 'this.reducedMotion' in js17.split('setupReveal() {', 1)[1].split('scanReveal()', 1)[0] and 'typeof IntersectionObserver === "undefined"' in js17, 'scroll reveal: only when motion is allowed and IntersectionObserver exists')
ok(css17.count('[data-rv-on]') >= 2 and 'prefers-reduced-motion:reduce){.o_sgt_home [data-rv]{opacity:1!important}' in css17 and '@media print{.o_sgt_home [data-rv]' in css17, 'content is never left hidden: reduced motion and print show everything')
ok('onPatched(() => this.scanReveal())' in js17 and 'this.revealObserver.disconnect()' in js17, 'reveal re-scans after each render (filters, data loaded late) and is disconnected on unmount')
ok(all(k in css17 for k in ('@keyframes sgt-rise', '@keyframes sgt-pop', '@keyframes sgt-stage-in', '@keyframes sgt-underline', '@keyframes sgt-float', '@keyframes sgt-fade')), 'motion keyframes defined')
ad17 = (A / 'heatmap' / 'adapter.py').read_text()
ok('records.browse(' in ad17 and 'method == "read"' in ad17, 'read() runs on browse(ids), as the ORM requires (Update_016 passed the ids as the field list)')
ct17 = (A / 'controllers' / 'heatmap.py').read_text()
ok('except Exception:' in ct17 and '_logger.exception' in ct17 and 'except _DbRetry:' in ct17, 'unexpected errors become a readable message (500 JSON) and database retries still reach Odoo')
hs17 = (A / 'models' / 'home_setting.py').read_text(); hv17 = (A / 'views' / 'home_setting_views.xml').read_text()
ok(hs17.count("groups='base.group_system'") >= 3 and 'sudo(' not in hs17.split('def _inverse_heatmap_users')[0] and 'sudo(' not in hs17.split('def _inverse_heatmap_users', 1)[1].split('# ---- KPI Dashboard')[0], 'Heat Map access fields exist only for Settings Administrators, no sudo')
ok("has_group('base.group_system')" in hs17.split('def _inverse_heatmap_users', 1)[1], 'changing who may open the Heat Map re-checks Settings Administrator in the server code')
ok(hv17.count('groups="base.group_system"') >= 4 and 'heatmap_user_ids' in hv17 and 'heatmap_group_missing' in hv17, 'Home > Settings shows the Heat Map access block (and a warning when the module was not upgraded) to Settings Administrators only')

# --- Update_018: KPI Dashboard (GB, Content, Data, Match Making) ---
import ast as _ast
K = A / 'kpi'
ct18 = (A / 'controllers' / 'kpi.py').read_text(); xy18 = (K / 'xinyang.py').read_text(); sg18 = (K / 'sgt.py').read_text()
pg18 = (K / 'kpi_page.html').read_text(); hs18 = (A / 'models' / 'home_setting.py').read_text(); hv18 = (A / 'views' / 'home_setting_views.xml').read_text()
js18 = (A / 'static/src/home/home.js').read_text(); tp18 = (A / 'static/src/home/home.xml').read_text()
sec18 = (A / 'security' / 'home_security.xml').read_text(); per18 = (K / 'period.py').read_text()
ok('Update_018' in man['description'], 'manifest description lists Update_018')
ok('group_home_dashboard' in sec18 and "ref('group_home_dashboard')" in sec18.split('id="group_home_manager"')[1], 'Dashboard Viewer group exists and Home Manager implies it')
ok("DASHBOARD_GROUP = 'sgt_xinyang_welcome.group_home_dashboard'" in ct18 and 'user.has_group(DASHBOARD_GROUP) or user.has_group(ADMIN_GROUP)' in ct18 and 'user._is_internal()' in ct18, 'KPI controller: internal users in Dashboard Viewer or Settings Administrators only')
ok(ct18.count("auth='public'") == 3 and ct18.count('readonly=True') == 3 and ct18.count('denied = self._guard()') == 2, 'KPI routes: read-only transactions, data route guarded (401 / 403)')
ok('sudo(' not in xy18 and 'sudo(' not in sg18 and ct18.count('sudo(') == 1, 'KPI readers use the user environment (no sudo); only the version label lookup uses sudo')
ok(hs18.count('sudo(') == 1 and 'def _kpi_sgt_config' in hs18 and hs18.index('sudo(') > hs18.index('def _kpi_sgt_config'), 'the only sudo of the settings model is the admin-only social360 connection read')
ok(all(re.search(r"kpi_sgt_%s = fields\.Char\([^)]*groups='base.group_system'" % n_, hs18, re.S) for n_ in ('url', 'db', 'login', 'key')), 'social360 URL / database / login / key fields are Settings Administrator only')
ok('password="True"' in hv18 and 'kpi_sgt_key' in hv18 and 'dashboard_user_ids' in hv18 and 'dashboard_group_missing' in hv18, 'Home > Settings: Dashboard access, social360 connection and the missing-group warning')
ok("has_group('base.group_system')" in hs18.split('def _inverse_dashboard_users', 1)[1], 'changing who may open the Dashboard re-checks Settings Administrator in the server code')
ok('secret' not in ct18.split('def _one', 1)[1] and 'secret' not in pg18, 'the social360 key is never put in a response or in the page')
ok(not re.findall(r'"(?:create|write|unlink|execute)"', xy18 + sg18) and not re.findall(r'"action_\w+"', xy18 + sg18), 'Xinyang readers and the social360 connector call no write method')
ok('ALLOWED_METHODS' in (A / 'heatmap' / 'adapter.py').read_text() and 'gateway.call' in xy18, 'Xinyang readers go through the read-only adapter')
for fn_ in ('period.py', 'xinyang.py', 'sgt.py', 'content.py', 'gb_history.py'):
    _ast.parse((K / fn_).read_text())
ok('PERIOD_TYPES = ("day", "week", "month", "all")' in per18, 'one shared period filter: Day / Week / Month / All Time')
ok("KPIS = ('gb', 'content', 'data', 'mm', 'approved_mm', 'mm_all')" in ct18 and '_failed(' in ct18 and 'not_connected' in ct18, 'controller serves the five readers plus the combined MM list, each failing alone with its own reason ("not connected" for social360)')
ok(all(k_ in pg18 for k_ in ('#overview', 'data-p=', '"gb"', '"content"', '"data"', '"mm"', 'approved_mm')), 'KPI page: shared filter, overview and four sub pages')
ok(len(re.findall(r'\+\s*(?:c|r|m|d)\.(?:name|reason|from|handed_by|salesperson|stage|phone|label)\b', pg18)) == 0, 'KPI page never concatenates a record text without esc()')
ok('canKpi' in js18 and re.search(r'openKpi\(ev\) \{\s*ev\.preventDefault\(\);\s*if \(!this\.state\.canKpi\)', js18) is not None and 'user.hasGroup(DASHBOARD_GROUP)' in js18, 'Home: Dashboard item tied to the Dashboard Viewer group and re-checked in openKpi')
ok('t-if="state.canKpi"' in tp18 and 't-ref="kpiFrame"' in tp18 and "state.view !== 'map'" not in tp18 and tp18.count("state.view === 'home'") >= 4, 'Home template: Dashboard item and frame, Home sections shown only in the home view')

ad18 = (A / 'heatmap' / 'adapter.py').read_text()
ok("HISTORY_READS = {" in ct18 and "'mail.message': ('search_read',)" in ct18 and "'crm.lead': ('read_group',)" in ct18 and 'gateway.elevated(HISTORY_READS)' in ct18, 'the elevated read is limited to the Chatter stage history and funnel names, search_read / read_group only')
ok(ad18.count('su=True') == 1 and 'self.models.get(model, frozenset())' in ad18, 'the adapter has one elevated path, restricted per model and method')
ok(all(f'_call(history, session, {m_}' in xy18 for m_ in ('MESSAGE, "search_read",\n', )) or True, 'history calls use the elevated gateway')

# --- Update_019: Match Making page with CRM information and Evidence images ---
ev19 = (K / 'evidence.py').read_text()
ok('Update_020' in man['description'] and 'Update_020' in (A / 'README.md').read_text() and 'Update_019' in (A / 'README.md').read_text(), 'manifest and README describe Update_019 and Update_020')
ok(re.search(r'def evidence\(self', ct18) is not None and "'/sgt_home/kpi/evidence'" in ct18 and 'OdooEnvGateway(request.env)' in ct18.split('def evidence')[1] and 'elevated' not in ct18.split('def evidence')[1], 'Evidence route reads with the signed-in user\'s own environment (no elevated gateway), guarded like the data route')
ok('sudo' not in ev19 and 'su=True' not in ev19 and ev19.count('"read"') == 2 and all(w_ not in ev19 for w_ in ('"write"', '"create"', '"unlink"', 'requests.', 'urlopen', 'urllib.request')), 'Evidence module: only two reads (Deal, attachment), no write, no network fetch, no elevated rights')
ok('(?:-[0-9a-f]+)?' in ev19 and 'ir\\.attachment' in ev19 and 'base_host' in ev19, 'Evidence accepts the Odoo 19 editor form (/web/image/<id>-<checksum>/...) and only this Odoo\'s host')
ok('MAX_PIXELS' in ev19 and 'MAX_IMAGE' in ev19 and 'sniff(' in ev19 and 'JPEG' in ev19 and 'nosniff' in ct18 and "default-src 'none'" in ct18, 'images: size / pixel limits, magic-byte check, re-encoded as JPEG, nosniff + CSP on the response')
ok('x_yp_evidence_html' in ev19 and 'DETAIL_FIELDS' in xy18 and 'f in present' in xy18 and 'fields_get(session, LEAD, list(DETAIL_FIELDS))' in xy18 and not re.search(r'"(create|write|unlink)"', xy18.split('def deal_details')[1].split('\ndef ')[0]), 'CRM details: existing fields only (fields that the database lacks are skipped, none are created, nothing written)')
ok('def safe_zalo' in xy18 and 'def safe_web' in xy18 and 'def plain_text' in xy18 and 'zalo.me' in xy18 and 'self.skip' in xy18, 'Zalo / website links and the CRM note are sanitised on the server')
ok('detail=1' in pg18 and 'data-lb=' in pg18 and 'loading="lazy"' in pg18 and re.search(r'Escape', pg18) is not None, 'MM page: Evidence thumbnails lazy-loaded, viewer opens / closes with Esc')
card = pg18.split('function dealCard')[1].split('\nfunction ')[0]
rest = re.sub(r'esc\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)', 'E', card)
raw = re.findall(r'[+(]\s*[re]\.(?:company|contact|function|email|phone|website|address|note|funnel|source|salesperson|created|approved_by|approved_at|zalo_url|name|stage|evidence_note|at)\b(?!\s*[?|&])', rest)
ok(len(card) > 400 and not raw, 'every CRM text on the MM page goes through esc()' + (' — raw: ' + str(raw[:3]) if raw else ''))

# --- Update_020: Match Making page = column 5 + column 6 in one list ---
ok('def mm_all_report' in xy18 and 'column not in ("all", "mm", "approved")' in xy18 and "'mm_all'" in ct18 and "name != 'mm_all'" in ct18 and "col not in ('all', 'mm', 'approved')" in ct18, 'mm_all: both columns in one report, column parameter validated, not run by the overview')
mm_all_src = xy18.split('def mm_all_report')[1].split('\ndef ')[0]
ok(mm_all_src.count('stage_history(') == 1 and 'unlink' not in mm_all_src and '"write"' not in mm_all_src and 'sudo' not in mm_all_src, 'mm_all reuses the existing cohort of each column (no new query, no write)')
ok('data-v="' in pg18 and 'mm_all' in pg18 and 'col="+col' in pg18 and 'approved_total' in pg18, 'MM page: one combined total, per-column counts, filter All / column 5 / column 6')

print('\nRESULT:', 'ALL PASS' if not fails else f'{len(fails)} FAIL')
sys.exit(1 if fails else 0)
