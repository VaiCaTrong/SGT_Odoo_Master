"""CRM-007 Update_003 offline checks (no Odoo runtime needed).

Usage:
    python3 test_update001_offline.py <odoo_views.csv> <odoo_fields.csv>

* odoo_views.csv  : views of the 2026-10-11 Xinyang production Scan (res.partner form = view 127 and its extensions).
* odoo_fields.csv : fields of the same Scan.

Without the two Scan files only the checks that do not need them run.  The CRM-007 view is applied with a small
re-implementation of Odoo's inheritance engine (xpath positions inside/before/after/replace/attributes incl.
add/separator), depth first and ordered by (priority, id) like Odoo.
"""
import ast, copy, csv, os, re, sys, unittest
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, '..'))
XML = os.path.join(MOD, 'views', 'res_partner_views.xml')
SCSS = os.path.join(MOD, 'static', 'src', 'css', 'contact_company_profile.css')
VIEWS = FIELDS = None

NEW_FIELDS = {'x_type_contact', 'x_country', 'x_yp_employee_range', 'x_fb_industry', 'x_url_zalo_group',
              'x_url_fb_profile', 'x_group_link', 'x_group_post_link', 'x_yp_founded_year', 'x_yp_listing_url',
              'x_yp_intro_en', 'x_yp_gallery_html', 'x_yp_partners_html', 'x_sgt_crm_synced', 'x_sgt_crm007_company_logo'}
REUSED = {'vat', 'comment', 'image_1920', 'image_128', 'street', 'name', 'parent_id', 'is_company'}


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


class ApplyError(Exception):
    pass


def my_specs():
    arch = etree.parse(XML).getroot().xpath("//field[@name='arch']")[0]
    return [c for c in arch if isinstance(c.tag, str)]


def _locate(tree, expr):
    nodes = tree.xpath(expr)
    if not nodes:
        raise ApplyError('NO MATCH: ' + expr)
    return nodes[0]


def apply_specs(tree, specs):
    for spec in specs:
        if spec.tag == 'data':
            apply_specs(tree, [c for c in spec if isinstance(c.tag, str)])
            continue
        if spec.tag == 'xpath':
            expr = spec.get('expr')
        else:            # <field name="x" position="after"> style spec
            attrs = ' and '.join("@%s='%s'" % (k, v) for k, v in spec.attrib.items() if k != 'position')
            expr = '//%s[%s]' % (spec.tag, attrs)
        node = _locate(tree, expr)
        pos = spec.get('position', 'inside')
        parent = node.getparent()
        if pos == 'attributes':
            for a in spec.findall('attribute'):
                name = a.get('name')
                if a.get('add') is not None or a.get('remove') is not None:
                    sep = a.get('separator', ',')
                    cur = [x for x in (node.get(name) or '').split(sep) if x]
                    for x in (a.get('add') or '').split(sep):
                        if x and x not in cur:
                            cur.append(x)
                    for x in (a.get('remove') or '').split(sep):
                        if x in cur:
                            cur.remove(x)
                    node.set(name, sep.join(cur))
                else:
                    node.set(name, a.text or '')
            continue
        kids = [copy.deepcopy(c) for c in spec if isinstance(c.tag, str)]
        if pos == 'replace':
            idx = parent.index(node)
            for k in reversed(kids):
                parent.insert(idx, k)
            parent.remove(node)
        elif pos == 'inside':
            for k in kids:
                node.append(k)
        elif pos == 'before':
            for k in kids:
                node.addprevious(k)
        elif pos == 'after':
            for k in reversed(kids):
                node.addnext(k)
        else:
            raise ApplyError('unsupported position ' + pos)
    return tree


def _children(view_id):
    out = [r for r in VIEWS if r['inherit_id'].startswith('[%s,' % view_id)]
    return sorted(out, key=lambda r: (int(r['priority']), int(r['id'])))


def _apply_tree(tree, view_id, mine_id, mine_priority, with_ext):
    kids = _children(view_id) if with_ext else []
    entries = [(int(r['priority']), int(r['id']), r) for r in kids]
    if view_id == '127':
        entries.append((mine_priority, 5000, None))
    entries.sort(key=lambda x: (x[0], x[1]))
    for pr, i, r in entries:
        if r is None:
            apply_specs(tree, my_specs())
        else:
            apply_specs(tree, [c for c in etree.fromstring(('<data>%s</data>' % r['arch_db']).encode()) if isinstance(c.tag, str)])
            _apply_tree(tree, r['id'], mine_id, mine_priority, with_ext)
    return tree


def build(with_ext=True, mine_priority=95):
    base = [r for r in VIEWS if r['id'] == '127'][0]
    tree = etree.fromstring(base['arch_db'].encode())
    return _apply_tree(tree, '127', 5000, mine_priority, with_ext)


def view_arch():
    return etree.parse(XML).getroot().xpath("//field[@name='arch']")[0]


class Update001(unittest.TestCase):
    def need_scan(self):
        if not VIEWS or not FIELDS:
            self.skipTest('Scan files not provided')

    # ---------- applying the view ----------
    def test_applies_on_base_only(self):
        self.need_scan()
        build(with_ext=False)

    def test_applies_with_all_extensions(self):
        self.need_scan()
        build()

    def test_applies_whatever_the_priority(self):
        self.need_scan()
        for p in (1, 16, 50, 95, 200):
            build(mine_priority=p)

    # ---------- fields ----------
    def test_every_field_exists_in_scan_or_is_one_of_the_15_new(self):
        self.need_scan()
        have = {r['name'] for r in FIELDS if r['model'] == 'res.partner'}
        used = set(view_arch().xpath('.//field/@name'))
        missing = sorted(u for u in used if u not in have and u not in NEW_FIELDS)
        self.assertEqual(missing, [])

    def test_new_fields_do_not_clash_with_scan(self):
        self.need_scan()
        have = {r['name'] for r in FIELDS if r['model'] == 'res.partner'}
        self.assertFalse(NEW_FIELDS & have)

    def test_expressions_use_only_known_fields(self):
        self.need_scan()
        have = {r['name'] for r in FIELDS if r['model'] == 'res.partner'} | NEW_FIELDS
        bad = []
        for node in view_arch().iter():
            if not isinstance(node.tag, str):
                continue
            for att in ('invisible', 'readonly'):
                v = node.get(att)
                if v is None or v in ('1', '0', 'True', 'False'):
                    continue
                tree = ast.parse(v.strip(), mode='eval')          # must be a valid Python expression
                for n in ast.walk(tree):
                    if isinstance(n, ast.Name) and n.id not in have:
                        bad.append((att, v, n.id))
        self.assertEqual(bad, [])

    def test_exactly_15_new_fields_in_model(self):
        tree = ast.parse(read(os.path.join(MOD, 'models', 'res_partner.py')))
        names = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Call):
                kind = getattr(n.value.func, 'attr', '')
                if kind in ('Char', 'Integer', 'Html', 'Text', 'Binary', 'Boolean', 'Many2one', 'One2many', 'Float', 'Date', 'Selection', 'Image'):
                    names[n.targets[0].id] = kind
        self.assertEqual(set(names), NEW_FIELDS)
        self.assertEqual(names['x_yp_founded_year'], 'Integer')
        self.assertEqual(names['x_sgt_crm_synced'], 'Boolean')
        self.assertEqual(names['x_sgt_crm007_company_logo'], 'Image')
        for f in ('x_yp_intro_en', 'x_yp_gallery_html', 'x_yp_partners_html'):
            self.assertEqual(names[f], 'Html')
        for f in NEW_FIELDS - {'x_yp_founded_year', 'x_sgt_crm_synced', 'x_sgt_crm007_company_logo', 'x_yp_intro_en', 'x_yp_gallery_html', 'x_yp_partners_html'}:
            self.assertEqual(names[f], 'Char', f)

    def test_all_new_fields_are_not_copied_and_flag_is_readonly(self):
        src = read(os.path.join(MOD, 'models', 'res_partner.py'))
        self.assertEqual(src.count('copy=False'), 14)
        self.assertIn('readonly=True', src)

    def test_registry_lists_the_15_fields(self):
        rows = list(csv.DictReader(read(os.path.join(MOD, 'FIELD_REGISTRY_CRM007.csv')).splitlines()))
        self.assertEqual({r['technical_field'] for r in rows}, NEW_FIELDS)
        self.assertTrue(all(r['scan_20261011_checked_no_existing_field'] == 'YES' and r['reason_new_field'] for r in rows))

    # ---------- no JS / API / cron / extra data ----------
    def test_manifest_has_no_js_and_only_contacts_dependency(self):
        m = ast.literal_eval(read(os.path.join(MOD, '__manifest__.py')))
        self.assertEqual(m['depends'], ['contacts'])
        self.assertEqual(m['data'], ['views/res_partner_views.xml'])
        assets = m['assets']['web.assets_backend']
        self.assertEqual(assets, ['sgt_contact_company_profile/static/src/css/contact_company_profile.css'])

    def test_no_js_cron_api_files(self):
        found = []
        for root, _, files in os.walk(MOD):
            if '/tests' in root:
                continue
            for f in files:
                if f.endswith(('.js', '.owl', '.mjs')) or f in ('ir_cron.xml',):
                    found.append(f)
                if f.endswith('.py'):
                    t = read(os.path.join(root, f))
                    for bad in ('requests', 'urllib', 'http.client', 'ir.cron', '@http.route'):
                        if bad in t:
                            found.append((f, bad))
        self.assertEqual(found, [])

    def test_no_forbidden_markup_in_view(self):
        txt = read(XML)
        self.assertNotIn('data-tooltip', txt)
        self.assertNotIn('hasclass', txt)
        self.assertNotIn('<script', txt)
        self.assertNotIn('t-on-', txt)

    # ---------- layout ----------
    def test_profile_block_sits_between_main_fields_and_tabs(self):
        self.need_scan()
        t = build()
        sheet = t.xpath('//sheet')[0]
        kids = [k for k in sheet if isinstance(k.tag, str)]
        names = [k.get('name') for k in kids]
        i_root = [i for i, k in enumerate(kids) if k.xpath('./div[@name="sgt_contact007_profile"]') or k.get('name') == 'sgt_contact007_profile']
        self.assertEqual(len(i_root), 1)
        nb = [i for i, k in enumerate(kids) if k.tag == 'notebook'][0]
        self.assertEqual(i_root[0], nb - 2, 'profile block before the individual boxes and the notebook')
        boxes = [i for i, k in enumerate(kids) if k.get('name') == 'sgt_contact007_boxes']
        self.assertEqual(boxes, [nb - 1], 'individual profile boxes directly before the notebook')

    def test_individual_boxes_before_notebook_and_company_only_basic(self):
        arch = view_arch()
        boxes = arch.xpath(".//div[@name='sgt_contact007_boxes']")[0]
        self.assertIn('is_company', boxes.get('invisible'))
        pair = boxes.xpath("./div[contains(@class,'sgt_cp_pair')]")[0]
        self.assertEqual(len(pair.findall('section')), 2)
        details = boxes.findall('details')
        self.assertEqual(len(details), 2)
        self.assertTrue(all(d.get('open') == 'open' for d in details))
        root = arch.xpath(".//div[@name='sgt_contact007_profile']")[0]
        self.assertIn('is_company', root.get('invisible', ''))
        self.assertEqual(len(root.xpath("./div[contains(@class,'sgt_cp_hero')]")), 1)
        self.assertEqual(len(root.xpath("./div[contains(@class,'sgt_cp_duo')]//section")), 2)
        self.assertEqual(len(root.xpath(".//field[@name='partner_latitude']")), 1)
        self.assertEqual(len(root.xpath(".//field[@name='partner_longitude']")), 1)
        self.assertTrue(root.xpath(".//section[contains(@class,'sgt_cp_geo_panel')]"))

    def test_every_new_field_shown_read_only(self):
        arch = view_arch()
        for f in NEW_FIELDS - {'x_sgt_crm_synced'}:
            nodes = arch.xpath(".//field[@name='%s']" % f)
            self.assertTrue(nodes, f)
            for n in nodes:
                self.assertEqual(n.get('readonly'), '1', f)
        flag = arch.xpath(".//field[@name='x_sgt_crm_synced']")
        self.assertEqual([n.get('invisible') for n in flag], ['1'])
        for f in ('vat', 'comment'):
            for n in arch.xpath(".//field[@name='%s']" % f):
                self.assertEqual(n.get('readonly'), '1', f)

    def test_avatar_read_only_only_when_synced_and_only_main_form(self):
        self.need_scan()
        t = build()
        main = t.xpath('/form/sheet/div//field[@name="image_1920"]')
        self.assertEqual(len(main), 1)
        self.assertEqual(main[0].get('readonly'), 'is_company')
        nested = t.xpath('//sheet/notebook//field[@name="image_1920"]')
        self.assertEqual(len(nested), 1)
        self.assertIsNone(nested[0].get('readonly'))

    def test_native_address_not_restyled(self):
        self.need_scan()
        t = build()
        main = t.xpath('/form/sheet/group//div[contains(@class,"o_address_format")]')
        self.assertEqual(len(main), 1)
        self.assertNotIn('sgt_cp_address', main[0].get('class'))
        self.assertIn('o_address_format', main[0].get('class'))

    def test_address_fields_unchanged(self):
        self.need_scan()
        before = build(with_ext=False)
        base = etree.fromstring([r for r in VIEWS if r['id'] == '127'][0]['arch_db'].encode())
        f0 = [f.get('name') for f in base.xpath('/form/sheet/group//div[contains(@class,"o_address_format")]//field')]
        f1 = [f.get('name') for f in before.xpath('/form/sheet/group//div[contains(@class,"o_address_format")]//field')]
        self.assertEqual(f0, f1)

    # ---------- CSS ----------
    def test_all_critical_classes_are_styled(self):
        css = read(SCSS)
        for name in ('sgt_cp_root','sgt_cp_hero','sgt_cp_hero_person',
                     'sgt_cp_hero_company', 'sgt_cp_duo','sgt_cp_panel',
                     'sgt_cp_stats','sgt_cp_geo_coords', 'sgt_cp_pair',
                     'sgt_cp_gallery', 'sgt_cp_partners'):
            self.assertIn('.' + name, css)

    def test_css_is_scoped_and_plain_css_not_scss(self):
        css = read(SCSS)
        self.assertNotIn('min(100%', css)
        self.assertNotIn('@import', css)
        self.assertNotIn('@use', css)
        self.assertNotIn('.o_address_format', css)
        css_no_comments = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        for rule in re.findall(r'([^{}]+)\{', css_no_comments):
            for selector in rule.split(','):
                selector = selector.strip()
                if selector:
                    self.assertTrue(selector.startswith('.o_form_view') or selector.startswith('@media') or selector.startswith('@container'), selector)



if __name__ == '__main__':
    if len(sys.argv) > 2 and os.path.exists(sys.argv[1]) and os.path.exists(sys.argv[2]):
        csv.field_size_limit(10 ** 9)
        with open(sys.argv[1], encoding='utf-8-sig') as fh:
            VIEWS = list(csv.DictReader(fh))
        with open(sys.argv[2], encoding='utf-8-sig') as fh:
            FIELDS = list(csv.DictReader(fh))
        del sys.argv[1:3]
    unittest.main(verbosity=2)
