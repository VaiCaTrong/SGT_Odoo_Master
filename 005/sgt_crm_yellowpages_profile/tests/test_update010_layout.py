"""CRM-005 Update_010 offline checks (no Odoo runtime needed).

Usage:
    python3 test_update010_layout.py <crm_forms.json> <odoo_fields.csv>

* crm_forms.json  : crm.lead form views of the 2026-10-11 Xinyang production Scan
                    (base view 1036 and its extensions).
* odoo_fields.csv : fields of the same Scan.

The CRM-005 view is applied with a small re-implementation of Odoo's
inheritance engine (xpath positions inside/before/after/replace/attributes and
the nested ``move`` position), in the same order as Odoo (priority, id).
"""
import ast, copy, csv, json, os, re, sys, unittest
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, '..'))
XML = os.path.join(MOD, 'views', 'crm_yp_lead_form.xml')
FORMS = FIELDS = None

NEW_FIELDS = {'x_yp_tax_code', 'x_yp_founded_year', 'x_yp_employee_range', 'x_yp_gallery_html', 'x_yp_intro_en', 'x_yp_partners_html', 'x_yp_logo_upload', 'x_yp_evidence_html'}
REMOVED = ['x_yp_company_logo', 'x_yp_business_type', 'x_yp_industries', 'x_yp_main_market',
           'x_yp_target_customers', 'x_yp_office_address', 'x_yp_zalo_phone',
           'x_yp_company_overview', 'x_yp_listing_url', 'x_yp_listing_id',
           'x_yp_projects_summary', 'x_yp_product_ids', 'x_yp_project_ids', 'x_yp_media_ids',
           'sgt.crm005.product', 'sgt.crm005.project', 'sgt.crm005.media']


class ApplyError(Exception):
    pass


def crm005_specs():
    arch = etree.parse(XML).getroot().xpath("//field[@name='arch']")[0]
    return [c for c in arch if isinstance(c.tag, str)]


def _locate(tree, expr):
    nodes = tree.xpath(expr)
    if not nodes:
        raise ApplyError('NO MATCH: ' + expr)
    return nodes[0]


def apply_specs(tree, spec_root_children):
    for spec in spec_root_children:
        if spec.tag == 'data':
            apply_specs(tree, [c for c in spec if isinstance(c.tag, str)])
            continue
        if spec.tag == 'xpath':
            expr = spec.get('expr')
        else:
            attrs = ' and '.join("@%s='%s'" % (k, v) for k, v in spec.attrib.items() if k != 'position')
            expr = '//%s[%s]' % (spec.tag, attrs)
        pos = spec.get('position', 'inside')
        node = _locate(tree, expr)
        parent = node.getparent()
        if pos == 'attributes':
            for a in spec.findall('attribute'):
                node.set(a.get('name'), a.text or '')
            continue
        kids = []
        for c in spec:
            if not isinstance(c.tag, str):
                continue
            if c.get('position') == 'move':
                src = _locate(tree, c.get('expr'))
                src.getparent().remove(src)
                src.tail = None
                kids.append(src)
            else:
                kids.append(copy.deepcopy(c))
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


def build(include_ext=True, include_1098=True, hide_legacy=True, demo2_sync=False, mine=True):
    base = [r for r in FORMS if r['id'] == '1036'][0]
    tree = etree.fromstring(base['arch_db'].encode())
    ext = [r for r in FORMS if r['inherit_id'].startswith('[1036')]
    ext.sort(key=lambda r: (int(r['priority']), int(r['id'])))
    items = []
    if include_ext:
        for r in ext:
            if r['id'] == '1098' and not include_1098:
                continue
            items.append((int(r['priority']), int(r['id']), etree.fromstring(('<data>%s</data>' % r['arch_db']).encode())))
            if r['id'] == '1098' and hide_legacy:
                items.append((95, int(r['id']) + 1, etree.fromstring(
                    b"<data><xpath expr=\"//notebook[page[.//field[@name='x_deal_id']]]\" position=\"replace\"/></data>")))
    if demo2_sync:
        items.append((16, 1904, etree.fromstring(
            b"<data><xpath expr=\"//sheet\" position=\"inside\"><group string=\"Contact Sync\"><field name=\"x_groupname\"/></group></xpath></data>")))
    if mine:
        items.append((95, 5000, None))
    items.sort(key=lambda x: (x[0], x[1]))
    for pr, i, spec in items:
        if spec is None:
            apply_specs(tree, crm005_specs())
        else:
            apply_specs(tree, [c for c in spec if isinstance(c.tag, str)])
    return tree


def hidden_for(node, record_type):
    for anc in [node] + list(node.iterancestors()):
        inv = (anc.get('invisible') or '').replace('"', "'")
        if inv == "type == '%s'" % record_type:
            return True
    return False


def idx_in_sheet(tree, node):
    sheet = tree.xpath('//sheet')[0]
    cur = node
    while cur.getparent() is not sheet:
        cur = cur.getparent()
    return sheet.index(cur)


class Update010(unittest.TestCase):
    def setUp(self):
        if not FORMS:
            self.skipTest('Scan files not provided')

    # ---------- applying the view ----------
    def test_applies_on_base_only_install_time(self):
        build(include_ext=False)

    def test_applies_with_all_extensions_and_hide_child(self):
        build()

    def test_applies_demo2_variant(self):
        build(demo2_sync=True)

    def test_applies_without_legacy_view_install_validation(self):
        """Install-time validation does not see the manual legacy view 1098."""
        build(include_1098=False, hide_legacy=False)

    # ---------- fields ----------
    def test_every_field_exists_in_scan_or_is_one_of_the_five_new(self):
        have = {r['name'] for r in FIELDS if r['model'] == 'crm.lead'}
        arch = etree.parse(XML).getroot().xpath("//field[@name='arch']")[0]
        used = set(arch.xpath('.//field/@name'))
        missing = sorted(u for u in used if u not in have and u not in NEW_FIELDS)
        self.assertEqual(missing, [], 'fields neither in Scan nor in the 4 new ones')
        self.assertEqual(used & {f for f in used if f.startswith('x_yp_')}, NEW_FIELDS & used)

    def test_exactly_five_new_fields_in_model(self):
        tree = ast.parse(open(os.path.join(MOD, 'models', 'crm_lead.py')).read())
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Call):
                if getattr(n.value.func, 'attr', '') in ('Char', 'Integer', 'Html', 'Text', 'Image', 'Many2one', 'One2many', 'Float', 'Boolean', 'Date', 'Datetime', 'Selection', 'Binary'):
                    names.add(n.targets[0].id)
        self.assertEqual(names, NEW_FIELDS)

    def test_new_fields_do_not_clash_with_scan(self):
        have = {r['name'] for r in FIELDS if r['model'] == 'crm.lead'}
        self.assertFalse(NEW_FIELDS & have)

    def test_no_reference_to_removed_models_or_fields(self):
        bad = []
        for root, _, files in os.walk(MOD):
            if '/tests' in root or '/upgrades' in root:
                continue
            for f in files:
                if f.endswith(('.py', '.xml', '.csv', '.scss', '.css')) and f != 'FIELD_REGISTRY_CRM005.csv':
                    txt = open(os.path.join(root, f), encoding='utf-8').read()
                    for r in REMOVED:
                        if r in txt:
                            bad.append((f, r))
        self.assertEqual(bad, [])

    # ---------- layout ----------
    def _final(self):
        return build(demo2_sync=True)

    def test_detail_fields_between_tabs_and_sync(self):
        t = self._final()
        details = t.xpath("//details[contains(@class,'sgt_crm005_import_details')]")
        self.assertEqual(len(details), 1)
        nb = t.xpath('//sheet/notebook')
        self.assertEqual(len(nb), 1, 'legacy notebook must be hidden, only the native one remains')
        sync = t.xpath("//sheet/group[@string='Sync']")[0]
        csync = t.xpath("//sheet/group[@string='Contact Sync']")[0]
        i_nb, i_det = idx_in_sheet(t, nb[0]), idx_in_sheet(t, details[0])
        self.assertLess(i_nb, i_det)
        self.assertLess(i_det, idx_in_sheet(t, sync))
        self.assertLess(i_det, idx_in_sheet(t, csync))

    def test_detail_fields_button_text(self):
        t = self._final()
        s = t.xpath("//details[contains(@class,'sgt_crm005_import_details')]/summary")[0]
        self.assertIn('Detail Fields', ''.join(s.itertext()))

    def test_group_post_image_moved_not_copied(self):
        # Update_020: the base "Group Post Image" group is gone; the picture is shown ONCE, in Detail Fields
        t = self._final()
        self.assertFalse(t.xpath("//group[@name='group_images_parent']"))
        img = t.xpath("//field[@name='x_group_image_binary']")
        self.assertEqual(len(img), 1)
        self.assertTrue(any(a.tag == 'details' and 'sgt_crm005_import_details' in a.get('class', '')
                            for a in img[0].iterancestors()))
        top = t.xpath("//sheet/group[1]")[0]
        self.assertFalse(top.xpath(".//field[@name='x_group_image_binary']"))

    def test_legacy_import_fields_all_present_inside_detail(self):
        t = self._final()
        det = t.xpath("//details[contains(@class,'sgt_crm005_import_details')]")[0]
        in_det = set(det.xpath('.//field/@name'))
        legacy = etree.fromstring(('<d>%s</d>' % [r for r in FORMS if r['id'] == '1098'][0]['arch_db']).encode())
        wanted = set(legacy.xpath('.//field/@name'))
        # Update_020: the 4 link fields live in the Profile Link box, not in Detail Fields
        self.assertEqual(sorted(wanted - in_det - set(('x_url_zalo_group', 'x_url_fb_profile', 'x_group_link', 'x_group_post_link'))), [])

    def test_old_customer_info_fields_kept_in_detail(self):
        t = self._final()
        det = t.xpath("//details[contains(@class,'sgt_crm005_import_details')]")[0]
        in_det = set(det.xpath('.//field/@name'))
        for f in ('x_getfly_id', 'x_group_image_binary', 'team_id', 'campaign_id', 'medium_id',
                  'contact_name', 'function', 'street2', 'city', 'country_id'):
            self.assertIn(f, in_det, f)

    def test_new_interface_blocks_present_above_tabs(self):
        t = self._final()
        top = t.xpath("//group[@name='customer_info']")
        self.assertEqual(len(top), 1)
        flds = set(top[0].xpath('.//field/@name'))
        for f in ('x_image', 'partner_name', 'street', 'x_type_contact', 'x_country', 'x_yp_employee_range',
                  'x_fb_industry', 'x_phone', 'email_from', 'website', 'x_yp_tax_code', 'x_yp_founded_year', 'referred'):
            self.assertIn(f, flds, f)
        # nothing from the Import tab leaks into the new interface
        leaked = [f for f in flds if f.startswith('x_') and f not in
                  {'x_image', 'x_type_contact', 'x_country', 'x_fb_industry', 'x_phone', 'x_yp_employee_range',
                   'x_yp_tax_code', 'x_yp_founded_year', 'x_yp_logo_upload'} | set(('x_url_zalo_group', 'x_url_fb_profile', 'x_group_link', 'x_group_post_link'))]
        self.assertEqual(leaked, [])
        self.assertFalse(top[0].xpath('.//details'))

    def test_mapping_of_user_decisions(self):
        t = self._final()
        card = t.xpath("//group[@name='customer_info']")[0]
        self.assertEqual(card.xpath(".//field[@name='x_image']/@widget")[0], 'image_url')
        self.assertEqual(card.xpath(".//field[@name='x_phone']/@widget")[0], 'phone')
        self.assertEqual(card.xpath(".//field[@name='referred']/@widget")[0], 'url')
        # referred keeps its native label: no string= override anywhere
        self.assertFalse(t.xpath("//field[@name='referred'][@string]"))
        # Update_017: introduction = description (native Notes field) MOVED into its own box; the Notes page is hidden
        page = t.xpath("//page[@name='internal_notes']")[0]
        self.assertEqual(page.get('invisible'), '1')
        self.assertFalse(page.xpath(".//field[@name='description']"))
        notes = t.xpath("//div[contains(@class,'sgt_yp_nbox')]")
        self.assertEqual(len(notes), 1)
        self.assertEqual(len(t.xpath("//field[@name='description']")), 1)           # moved, not copied
        self.assertTrue(notes[0].xpath("./field[@name='description'][@class='sgt_yp_notes']"))
        self.assertFalse(notes[0].xpath("./field[@name='description'][@readonly]"))  # still editable
        self.assertEqual(notes[0].tag, 'div')                                         # Update_022: always visible, not an accordion
        self.assertEqual(notes[0].xpath('./div')[0].get('class'), 'sgt_yp_gbox_head')
        # Update_014: no Products & Services tab, no Image Gallery tab; gallery = box below the tabs
        self.assertFalse(t.xpath("//page[@name='sgt_crm005_products']"))
        self.assertFalse(t.xpath("//page[@name='sgt_crm005_gallery']"))
        self.assertFalse(t.xpath("//page[@string='Products & Services']"))
        box = t.xpath("//details[@name='sgt_crm005_gallery_box']")
        self.assertEqual(len(box), 1)
        self.assertTrue(box[0].xpath(".//field[@name='x_yp_gallery_html'][@widget='html']"))
        # Update_015: read-only (no editor mounted, no dirty form, nothing sent on Save), collapsible, no inner scroll
        self.assertEqual(box[0].tag, 'details')
        self.assertEqual(box[0].xpath(".//field[@name='x_yp_gallery_html']/@readonly")[0], '1')
        # Update_016: English introduction box right under the tabs, then the gallery box, then Detail Fields
        en = t.xpath("//div[contains(@class,'sgt_yp_ebox')]")
        self.assertEqual(len(en), 1)
        self.assertTrue(en[0].xpath(".//field[@name='x_yp_intro_en'][@widget='html']"))
        self.assertFalse(en[0].xpath(".//field[@name='x_yp_intro_en'][@readonly]"))   # editable: the user pastes here
        self.assertEqual(en[0].tag, 'div')                                            # Update_022: always visible, not an accordion
        self.assertEqual(en[0].xpath('./div')[0].get('class'), 'sgt_yp_gbox_head')
        self.assertFalse(t.xpath("//details[@name='sgt_crm005_intro_pair']"))
        self.assertFalse(t.xpath('//*[@open and (contains(@class,"sgt_yp_ebox") or contains(@class,"sgt_yp_nbox"))]'))
        nb = t.xpath("//sheet/notebook[1]")[0]
        # Update_018: English (LEFT) and Vietnamese (RIGHT) side by side in one pair; one open at a time (shared name)
        pair = en[0].getparent()
        self.assertEqual(pair.get('class'), 'sgt_yp_pair')
        self.assertEqual(pair.getparent().get('class'), 'sgt_yp_pair_wrap')
        self.assertEqual([c.get('class').split()[-1] for c in pair if c.tag == 'div'], ['sgt_yp_ebox', 'sgt_yp_nbox'])
        self.assertEqual(en[0].get('name'), 'sgt_crm005_intro_en_box')
        self.assertEqual(notes[0].get('name'), 'sgt_crm005_intro_vi_box')
        self.assertIs(pair.getparent().getnext(), box[0])
        # Update_020: Partners box right under the gallery box, then the notebook
        pbox = t.xpath("//details[@name='sgt_crm005_partners_box']")
        self.assertEqual(len(pbox), 1)
        self.assertIs(box[0].getnext(), pbox[0])
        # Update_032: Evidence box right under Partners, then the notebook, then Detail Fields
        evbox = t.xpath("//div[@name='sgt_crm005_evidence_box']")
        self.assertEqual(len(evbox), 1)
        self.assertIs(pbox[0].getnext(), evbox[0])
        self.assertIs(evbox[0].getnext(), nb)
        self.assertTrue(nb.getnext().get('class', '').startswith('sgt_crm005_import_container'))
        self.assertEqual([c.get('name') for c in nb.getparent() if c.get('name', '').startswith('sgt_crm005_')],
                         ['sgt_crm005_gallery_box', 'sgt_crm005_partners_box', 'sgt_crm005_evidence_box'])
        for d in (en[0], notes[0]):
            self.assertTrue(d.xpath("./div[@class='sgt_yp_gbox_head']/span[@class='sgt_yp_gbox_title']"))
        # x_product_details is still reachable: Detail Fields > Product / Industry
        self.assertTrue(t.xpath("//div[@name='sgt_yp_detail_body']//field[@name='x_product_details']"))
        # Contacts page hidden, History page (third-party) untouched
        self.assertEqual(t.xpath("//page[@name='lead']/@invisible")[0], '1')

    def test_identifier_fields_under_source_and_address(self):
        """VN Odoo ID sits under Source (left), Deal ID under Address (right); Deal Identifiers group gone from Detail."""
        t = self._final()
        # Opportunity: VN Odoo ID immediately after Source
        nxt = t.xpath("//group[@name='opportunity_partner']/field[@name='source_id']/following-sibling::*[1]")[0]
        self.assertEqual(nxt.get('name'), 'x_getfly_id')
        self.assertEqual(nxt.get('string'), 'VN Odoo ID')
        self.assertFalse(hidden_for(nxt, 'opportunity'))
        # Lead: VN Odoo ID visible in the left group
        lead_ids = [f for f in t.xpath("//field[@name='x_getfly_id'][@string='VN Odoo ID']")
                    if not hidden_for(f, 'lead') and not f.xpath("ancestor::div[@name='sgt_yp_detail_body']")]
        self.assertEqual(len(lead_ids), 1)
        # Deal ID right after each Address field, visible once per type
        decks = t.xpath("//field[@name='street'][@string='Address']/following-sibling::*[1][@name='x_deal_id']")
        self.assertEqual(len(decks), 2)
        for typ in ('opportunity', 'lead'):
            self.assertEqual(len([d for d in decks if not hidden_for(d, typ)]), 1)
        # nothing left of the old Deal Identifiers group
        self.assertFalse(t.xpath("//group[@string='Deal Identifiers']"))

    def test_brand_colours_blue_red(self):
        s = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss')).read()
        for old in ('#f5b800', '#b88600', '245, 184, 0', '#0068ff'):
            self.assertNotIn(old, s.lower())
        self.assertIn('--o-xinyang-brand-blue, #0061BD', s)
        self.assertIn('--o-xinyang-brand-red, #E51922', s)

    def test_top_block_unchanged_source_and_address(self):
        t = self._final()
        src = t.xpath("//group[@name='opportunity_partner']/field[@name='source_id']")
        self.assertEqual(len(src), 1)
        self.assertFalse(hidden_for(src[0], 'opportunity'))
        streets = t.xpath("//field[@name='street'][@string='Address']")
        self.assertEqual(len(streets), 2)
        self.assertEqual(len([s for s in streets if not hidden_for(s, 'opportunity')]), 1)
        self.assertEqual(len([s for s in streets if not hidden_for(s, 'lead')]), 1)

    def test_widgets_whitelist(self):
        arch = etree.parse(XML).getroot().xpath("//field[@name='arch']")[0]
        used = set(arch.xpath('.//field/@widget'))
        self.assertLessEqual(used, {'image_url', 'phone', 'email', 'url', 'html', 'image', 'text', 'binary'})

    def test_no_new_mechanisms(self):
        """Nothing beyond views, CSS, the model and ONE approved plain script (Update_013 hover text slide):
        no other JS, no controller, no cron, no API call."""
        js = []
        for root, _, files in os.walk(MOD):
            for f in files:
                if f.endswith('.js'):
                    js.append(f)
        self.assertEqual(js, ['sgt_marquee.js'])
        src = open(os.path.join(MOD, 'static', 'src', 'js', 'sgt_marquee.js'), encoding='utf-8').read()
        for bad in ('fetch(', 'XMLHttpRequest', 'rpc', 'import ', 'export ', 'localStorage', 'sendBeacon', 'eval(', 'innerHTML', 'textContent ='):
            self.assertNotIn(bad, src, bad)
        txt = ''.join(open(os.path.join(root, f), encoding='utf-8').read()
                      for root, _, files in os.walk(MOD) if '/tests' not in root
                      for f in files if f.endswith(('.py', '.xml')))
        for bad in ('requests.', 'urllib', 'http.client', 'ir.cron', 'ir.actions.server', 'base.automation', '@http.route'):
            self.assertNotIn(bad, txt, bad)

    # ---------- packaging ----------
    def test_manifest(self):
        m = ast.literal_eval(open(os.path.join(MOD, '__manifest__.py')).read())
        self.assertGreaterEqual(tuple(map(int, m['version'].split('.'))), (19, 0, 1, 31, 0))
        for f in m['data']:
            self.assertTrue(os.path.exists(os.path.join(MOD, f)), f)
        for a in m['assets']['web.assets_backend']:
            self.assertTrue(os.path.exists(os.path.join(MOD, a.split('/', 1)[1])), a)

    def test_upgrade_script_and_hooks(self):
        p = os.path.join(MOD, 'upgrades', '19.0.1.9.0', 'post-10-update010.py')
        ast.parse(open(p).read())
        h = open(os.path.join(MOD, 'hooks.py')).read()
        self.assertNotIn('def ensure_sync_contact_relocation', h)
        self.assertIn('def remove_stale_contact_sync_relocation', h)
        self.assertIn("'noupdate': True", h)

    def test_css_has_detail_and_gallery_rules(self):
        s = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss')).read()
        for k in ('.sgt_yp_gallery', '.sgt_crm005_import_details', '.sgt_yp_profile', '.sgt_yp_side'):
            self.assertIn(k, s)
        self.assertNotIn('@container', s)
        gal = s[s.index('.o_form_view .sgt_yp_gallery {'):s.index('/* Evidence box (Update_032)')]   # gallery + partners only
        self.assertNotIn('max-height', gal)
        self.assertNotIn('overflow-y', gal)
        self.assertIn('content-visibility: auto', gal)
        self.assertIn('@container', open(os.path.join(MOD, 'static/src/css/yellowpages_container.css')).read())

    def test_update018_frame_and_pair_css(self):
        s = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss')).read()
        self.assertIn('.o_form_sheet:has(.sgt_yp_group)', s)
        # Update_022: two equal columns, equal height, no strips / carets / fold state
        self.assertIn('.sgt_yp_pair', s)
        pair = s[s.index('English | Vietnamese introductions side by side (Update_022)'):s.index('Vietnamese introduction box (Update_017)')]
        self.assertIn('repeat(2, minmax(0, 1fr))', pair)
        self.assertIn('align-items: stretch', pair)
        for k in ('writing-mode', '[open]', ':has('):
            self.assertNotIn(k, pair)
        self.assertNotIn('@container', s)
        c = open(os.path.join(MOD, 'static/src/css/yellowpages_container.css')).read()
        self.assertIn('@container sgt-yp-pair', c)
        pc = c[c.index('@container sgt-yp-pair'):]
        self.assertIn('grid-template-columns: minmax(0, 1fr)', pc)
        for k in ('writing-mode', '[open]', ':has('):
            self.assertNotIn(k, pc)
        self.assertNotIn('<script', open(os.path.join(MOD, 'views/crm_yp_lead_form.xml')).read())

    def test_update019_marquee_stops_when_editing(self):
        js = open(os.path.join(MOD, 'static/src/js/sgt_marquee.js'), encoding='utf-8').read()
        for k in ('function hasFocus', 'function onEdit', 'if (hasFocus(el)) { return; }',
                  "addEventListener('mousedown', onEdit", "addEventListener('focusin', onEdit",
                  'function stop(keep)'):
            self.assertIn(k, js)
        # still the one approved script: no import/export, no RPC / fetch
        for bad in ('import ', 'export ', 'fetch(', 'XMLHttpRequest', 'odoo.'):
            self.assertNotIn(bad, js)


    def test_update020_partners_box(self):
        t = self._final()
        pbox = t.xpath("//details[@name='sgt_crm005_partners_box']")[0]
        self.assertIn('sgt_yp_gbox', pbox.get('class'))
        self.assertIn('open', pbox.attrib)
        self.assertEqual(pbox.xpath('./summary/label/@string'), ['Partners'])
        f = pbox.xpath("./field[@name='x_yp_partners_html']")[0]
        self.assertEqual(f.get('widget'), 'html')
        self.assertEqual(f.get('readonly'), '1')                  # no Html editor mounted (as Image Gallery)
        self.assertIn('sgt_yp_gallery', f.get('class'))           # same grid CSS
        self.assertEqual(''.join(pbox.xpath("./div[@class='sgt_yp_partners_empty']")[0].itertext()), 'No partners yet.')
        self.assertEqual(len(t.xpath("//field[@name='x_yp_partners_html']")), 1)
        scss = open(os.path.join(MOD, 'static', 'src', 'scss', 'yellowpages_profile.scss')).read()
        self.assertIn('.sgt_yp_pbox:has(.sgt_yp_partners img) > .sgt_yp_partners_empty', scss)
        self.assertNotIn('@container', scss)
        py = open(os.path.join(MOD, 'models', 'crm_lead.py')).read()
        self.assertIn('x_yp_partners_html = fields.Html(', py)

    def test_update020_profile_link_box_and_wide_company(self):
        t = self._final()
        root = t.xpath("//div[contains(@class,'sgt_yp_root')]")[0]
        kids = [c for c in root if isinstance(c.tag, str)]
        cls = [c.get('class', '') for c in kids]
        i_company = next(i for i, c in enumerate(cls) if 'sgt_yp_profile' in c)
        i_page = next(i for i, c in enumerate(cls) if 'sgt_yp_page' in c)
        self.assertLess(i_company, i_page)                        # Company card = own full-width row
        page = kids[i_page]
        main = page.xpath(".//div[contains(@class,'sgt_yp_main')]")[0]
        side = page.xpath(".//div[contains(@class,'sgt_yp_side')]")[0]
        self.assertFalse(main.xpath(".//div[contains(@class,'sgt_yp_profile')]"))
        self.assertTrue(side.xpath(".//div[contains(@class,'sgt_yp_contact')]"))  # Contact level with the stats row
        self.assertTrue(main.xpath(".//div[contains(@class,'sgt_yp_stats')]"))
        box = main.xpath(".//div[contains(@class,'sgt_yp_links')]")[0]
        self.assertEqual(box.xpath(".//div[@class='sgt_yp_label']")[0].xpath('string(.)').strip(), 'Profile Link')
        self.assertEqual(box.xpath(".//field/@name"), ['x_url_zalo_group', 'x_url_fb_profile', 'x_group_link', 'x_group_post_link'])
        for f in box.xpath('.//field'):
            self.assertEqual(f.get('widget'), 'url')
        # no ID and no picture in the box
        self.assertFalse(box.xpath(".//field[@name='x_getfly_id' or @name='x_group_image_binary']"))
        # each of the 4 fields shown exactly once on the form (moved, not copied)
        for n in ('x_url_zalo_group', 'x_url_fb_profile', 'x_group_link', 'x_group_post_link'):
            self.assertEqual(len(t.xpath("//field[@name='%s']" % n)), 1, n)
        css = open(os.path.join(MOD, 'static', 'src', 'css', 'yellowpages_container.css')).read()
        self.assertIn('.sgt_yp_links_grid', css)

    def test_update021_every_profile_field_has_an_odoo_label(self):
        # 2026-10-28 15:51: Developer Mode shows the "?" (technical tooltip) only on real form labels
        # (<label for>), not on a <span>/<div> text.  Every field the profile layout shows must have one,
        # and each label must point at a field of this same view (explicit id) that comes with it.
        t = self._final()
        root = t.xpath("//div[contains(@class,'sgt_yp_root')]")[0]
        boxes = t.xpath("//details[contains(@class,'sgt_yp_gbox')] | //div[contains(concat(' ',normalize-space(@class),' '),' sgt_yp_gbox ')]")
        scope = [root] + boxes
        fields = [f for sc in scope for f in sc.xpath('.//field[@nolabel="1"]')]
        names = {f.get('name') for f in fields}
        self.assertTrue({'x_phone', 'email_from', 'website', 'contact_name', 'function', 'x_yp_tax_code',
                         'x_yp_founded_year', 'referred', 'x_type_contact', 'x_country', 'x_yp_employee_range',
                         'x_fb_industry', 'x_url_zalo_group', 'x_url_fb_profile', 'x_group_link',
                         'x_group_post_link', 'partner_name', 'street', 'street2', 'city', 'x_image',
                         'x_yp_intro_en', 'x_yp_gallery_html', 'x_yp_partners_html', 'x_yp_logo_upload', 'x_yp_evidence_html'} <= names)
        for f in fields:
            fid = f.get('id') or f.get('name')
            labs = [l for sc in scope for l in sc.xpath('.//label[@for]') if l.get('for') == fid]
            self.assertEqual(len(labs), 1, 'field %s has no label for' % f.get('name'))
        # the native Notes field moved into the Vietnamese box keeps its label (for = field name)
        self.assertTrue(t.xpath("//div[contains(@class,'sgt_yp_nbox')]//label[@for='description']"))
        self.assertTrue(t.xpath("//div[contains(@class,'sgt_yp_nbox')]//field[@name='description']"))
        # every label target exists in the final arch
        allnames = {(f.get('id') or f.get('name')) for f in t.xpath('//field')} | {f.get('name') for f in t.xpath('//field')}
        for l in t.xpath("//label[@for]"):
            self.assertIn(l.get('for'), allnames, l.get('for'))
        # explicit ids are unique
        ids = [f.get('id') for f in t.xpath('//field[@id]') if f.get('id', '').startswith('crm005_')]
        self.assertEqual(len(ids), len(set(ids)))
        css = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss'), encoding='utf-8').read()
        self.assertIn('label.o_form_label', css)


    def test_update023_manual_logo_upload(self):
        # 2026-10-30 14:15: the user can add the company logo by hand (upload from the computer)
        t = self._final()
        box = t.xpath("//div[@class='sgt_yp_logo']")[0]
        # shown logo: uploaded picture when there is one, otherwise the extension's x_image (as before)
        xi = box.xpath("./field[@name='x_image']")[0]
        up = box.xpath("./field[@name='x_yp_logo_upload']")[0]
        self.assertEqual(xi.get('invisible'), 'x_yp_logo_upload')
        self.assertEqual(xi.get('widget'), 'image_url')
        self.assertEqual(up.get('invisible'), 'not x_yp_logo_upload')
        self.assertEqual(up.get('widget'), 'image')
        self.assertEqual(up.get('readonly'), '1')
        # the upload control (editable) sits under the logo box, in the same column, with its own label
        col = box.getparent()
        self.assertEqual(col.get('class'), 'sgt_yp_logo_col')
        ctl = col.xpath("./div[@class='sgt_yp_logo_up']/field[@name='x_yp_logo_upload']")[0]
        self.assertEqual(ctl.get('widget'), 'binary')
        self.assertFalse(ctl.get('readonly'))
        self.assertTrue(col.xpath("./div[@class='sgt_yp_logo_up']/span[@class='sgt_yp_nolabel']/label[@for='%s']" % ctl.get('id')))
        # x_image itself stays read-only: the extension keeps writing it, nothing manual overwrites it
        self.assertEqual(xi.get('readonly'), '1')
        py = open(os.path.join(MOD, 'models', 'crm_lead.py'), encoding='utf-8').read()
        self.assertIn('x_yp_logo_upload = fields.Binary(', py)
        reg = open(os.path.join(MOD, 'FIELD_REGISTRY_CRM005.csv'), encoding='utf-8').read()
        self.assertIn('x_yp_logo_upload,Binary', reg)
        css = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss'), encoding='utf-8').read()
        self.assertIn('.sgt_yp_logo_col', css)
        self.assertIn('.sgt_yp_logo_up', css)
        # Update_025: the upload button is a brand-blue OUTLINE (border only, no fill) with an icon
        btn = css[css.index('.sgt_yp_logo_up .o_select_file_button {'):]
        btn = btn[:btn.index('}')]
        self.assertIn('border: 1px solid var(--sgt-yp-accent)', btn)
        self.assertIn('background: transparent', btn)
        self.assertIn('border-radius', btn)
        # Update_027: button can never collapse (Odoo's .btn rules must not shrink it) and the debug label shows only the "?"
        for k in ('min-height', 'padding: .4rem .5rem !important', 'display: flex !important'):
            self.assertIn(k, btn)
        self.assertIn('.sgt_yp_logo_up .sgt_yp_nolabel label.o_form_label {', css)
        # Update_028: after an upload Odoo prints the start of the base64 as text and squeezes the button -> hide the text,
        # button takes the free width, "Change logo" wording, square clear button, form font (Odoo's .btn leaves it unset = serif)
        self.assertIn('.sgt_yp_logo .sgt_yp_nolabel {', css)   # Update_030: no "?" inside the logo box ...
        self.assertNotIn('.sgt_yp_logo_up .sgt_yp_nolabel {\n    display: none !important', css)   # ... but the one above the upload buttons stays
        self.assertNotIn('Change logo', css)
        for k in ('.o_field_widget input', 'display: none !important', 'flex: 1 1 0', 'font-family: inherit !important',
                  ':has(.o_clear_file_button) .o_select_file_button::after', 'content: "\\f040"', '.o_clear_file_button {'):
            self.assertIn(k, css)
        self.assertNotIn('f093', css)                                  # Update_026: no icon, text centred and upright
        lab = css[css.index('.sgt_yp_logo_up .o_select_file_button::after {'):]
        lab = lab[:lab.index('}')]
        for k in ('text-align: center', 'font-style: normal', 'transform: none'):
            self.assertIn(k, lab)

    def test_update032_evidence_box(self):
        t = build()
        ev = t.xpath("//div[@name='sgt_crm005_evidence_box']")[0]
        self.assertEqual(ev.get('class'), 'sgt_yp_gbox sgt_yp_evbox')        # class used by CRM-002 for the red frame
        f = ev.xpath(".//field[@name='x_yp_evidence_html']")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].get('widget'), 'html')
        self.assertIsNone(f[0].get('readonly'))                            # pasted by hand: editable
        self.assertIn('Ctrl+V', f[0].get('placeholder'))
        self.assertTrue(ev.xpath(".//label[@for='crm005_x_yp_evidence_html'][@string='Evidence']"))
        self.assertEqual(len(t.xpath("//field[@name='x_yp_evidence_html']")), 1)
        s = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss')).read()
        self.assertIn('.o_form_view .sgt_yp_evbox:has(.sgt_yp_evidence img) .sgt_yp_ev_ok', s)
        self.assertIn('.o_form_view .sgt_yp_gbox.sgt_yp_evbox > .sgt_yp_gbox_head::after {\n    content: none;', s)
        m = open(os.path.join(MOD, 'models', 'crm_lead.py')).read()
        self.assertIn("x_yp_evidence_html = fields.Html(\n        string='Evidence', copy=False,", m)
        self.assertIn('x_yp_evidence_html', open(os.path.join(MOD, 'FIELD_REGISTRY_CRM005.csv')).read())

    def test_update031_full_address_on_company_card(self):
        # 2026-10-30 16:12/16:14: State, ZIP and Country move onto the Company card (design 3 of the mock-up)
        t = self._final()
        card = t.xpath("//div[contains(@class,'sgt_yp_profile')]")[0]
        l1 = card.xpath(".//div[contains(@class,'sgt_yp_line_street')]")[0]
        l2 = card.xpath(".//div[contains(@class,'sgt_yp_line_geo')]")[0]
        self.assertEqual(l1.xpath('./field/@name'), ['street'])
        self.assertEqual(l2.xpath('./field/@name'), ['street2', 'city', 'state_id', 'zip', 'country_id'])
        self.assertIs(l1.getnext(), l2)
        # only existing crm.lead fields, no new field, same options as the native Detail Fields entries
        self.assertEqual(l2.xpath("./field[@name='state_id']/@options")[0], "{'no_open': True}")
        self.assertEqual(l2.xpath("./field[@name='country_id']/@options")[0], "{'no_open': True, 'no_create': True}")
        for f in l2.xpath('./field'):
            self.assertEqual(f.get('nolabel'), '1')
            self.assertTrue(card.xpath(".//label[@for='%s']" % f.get('id')), f.get('name'))
        # Detail Fields keeps its copies (nothing removed)
        det = t.xpath("//details[contains(@class,'sgt_crm005_import_details')]")[0]
        for f in ('state_id', 'zip', 'country_id'):
            self.assertTrue(det.xpath(".//field[@name='%s']" % f), f)
        css = open(os.path.join(MOD, 'static/src/scss/yellowpages_profile.scss'), encoding='utf-8').read()
        self.assertIn('.sgt_yp_line_geo', css)

if __name__ == '__main__':
    if len(sys.argv) > 2 and os.path.exists(sys.argv[1]) and os.path.exists(sys.argv[2]):
        FORMS = json.load(open(sys.argv[1]))
        csv.field_size_limit(10 ** 9)
        FIELDS = list(csv.DictReader(open(sys.argv[2], encoding='utf-8-sig')))
        del sys.argv[1:3]
    unittest.main(verbosity=2)
