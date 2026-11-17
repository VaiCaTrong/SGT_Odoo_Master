"""Update_064: Documents -> Image Gallery. Odoo-free: real Pillow + the real model method run on a tiny ORM fake.

Run: python3 -I tests/test_update064_documents_to_gallery.py
"""
import ast
import base64
import hashlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path

from PIL import Image
from markupsafe import Markup
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


U = _load('gpush_utils', 'models/gallery_push_utils.py')
SYNC = _load('gsync_utils', 'models/gallery_sync_utils.py')


def img_bytes(fmt='JPEG', size=(40, 30), color=(200, 30, 30), **kw):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, fmt, **kw)
    return buf.getvalue()


def noisy_jpeg(side):
    import os
    raw = os.urandom(side * side * 3)
    im = Image.frombytes('RGB', (side, side), raw)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=95)
    return buf.getvalue()


class UtilsTests(unittest.TestCase):
    def test_accepts_jpeg_png_webp_verbatim(self):
        for fmt, mime in (('JPEG', 'image/jpeg'), ('PNG', 'image/png'), ('WEBP', 'image/webp')):
            data = img_bytes(fmt)
            out, got = U.prepare_image(data)
            self.assertEqual(out, data)
            self.assertEqual(got, mime)

    def test_rejects_gif_svg_garbage_empty(self):
        for data in (img_bytes('GIF'), b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
                     b'not an image', b''):
            with self.assertRaises(U.PushImageError):
                U.prepare_image(data)

    def test_name_extension_is_not_trusted(self):
        # a PNG renamed .jpg is judged by content (stored mime = image/png)
        out, mime = U.prepare_image(img_bytes('PNG'))
        self.assertEqual(mime, 'image/png')

    def test_pixel_cap(self):
        old = U.PUSH_MAX_PIXELS
        U.PUSH_MAX_PIXELS = 100
        try:
            with self.assertRaises(U.PushImageError):
                U.prepare_image(img_bytes('PNG', size=(20, 20)))
        finally:
            U.PUSH_MAX_PIXELS = old

    def test_heavy_image_is_shrunk_to_jpeg(self):
        data = noisy_jpeg(1700)
        self.assertGreater(len(data), U.PUSH_MAX_BYTES)
        out, mime = U.prepare_image(data)
        self.assertEqual(mime, 'image/jpeg')
        self.assertLessEqual(len(out), U.PUSH_MAX_BYTES)
        self.assertLessEqual(max(Image.open(io.BytesIO(out)).size), U.PUSH_SHRINK_EDGE)
        # deterministic: pushing the same heavy file again gives the same bytes (duplicate detection works)
        self.assertEqual(out, U.prepare_image(data)[0])

    def test_heavy_image_still_too_big_is_refused(self):
        old = U.PUSH_MAX_BYTES
        U.PUSH_MAX_BYTES = 200
        try:
            with self.assertRaises(U.PushImageError):
                U.prepare_image(noisy_jpeg(300))
        finally:
            U.PUSH_MAX_BYTES = old

    def test_existing_hashes_reads_inline_images_only(self):
        a, b = img_bytes('JPEG', color=(1, 2, 3)), img_bytes('PNG', color=(9, 9, 9))
        html = ('<figure><img src="data:image/jpeg;base64,%s" alt="x"></figure>'
                "<p><img src='data:image/png;base64,%s'></p>"
                '<img src="https://example.com/a.jpg"><img src="/web/image/5">'
                % (base64.b64encode(a).decode(), base64.b64encode(b).decode()))
        self.assertEqual(U.existing_hashes(html), {hashlib.sha1(a).hexdigest(), hashlib.sha1(b).hexdigest()})
        self.assertEqual(U.existing_hashes(''), set())
        self.assertEqual(U.existing_hashes(None), set())
        self.assertEqual(U.existing_hashes('<img src="data:image/png;base64,@@@@">'), set())

    def test_caption_and_escape(self):
        self.assertEqual(U.caption_from_name('Chữ Y.jpg'), 'Chữ Y')
        self.assertEqual(U.caption_from_name('a.b.c.png'), 'a.b.c')
        self.assertEqual(U.caption_from_name('x' * 300 + '.jpg'), 'x' * 100)
        self.assertEqual(U.caption_from_name('ab\x00c\n.jpg'), 'abc')
        fig = U.figure_html('"><script>alert(1)</script>.jpg', 'image/jpeg', b'abc')
        self.assertNotIn('<script', fig)
        self.assertEqual(fig.count('<figure>'), 1)
        root = etree.fromstring('<d>%s</d>' % fig.replace('<img src', '<img src').replace('">', '"/>', 1)
                                if False else '<d>' + fig + '</d>', etree.HTMLParser())
        self.assertEqual(len(root.xpath('//script')), 0)

    def test_figure_is_compatible_with_gallery_to_documents_sync(self):
        # figure > img + figcaption is what Update_058 reads: caption must come back as the file stem
        data = img_bytes('JPEG')
        html = U.merge_gallery_html('', [U.figure_html('Cút 90 độ.jpg', 'image/jpeg', data)])
        entries = SYNC.gallery_entries(html)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1], 'Cút 90 độ')
        self.assertTrue(entries[0][0].startswith('data:image/jpeg;base64,'))

    def test_merge_keeps_existing_untouched(self):
        old = '<p>old</p><figure><img src="data:image/png;base64,AAAA"></figure>'
        merged = U.merge_gallery_html(old, ['<figure>N1</figure>', '<figure>N2</figure>'])
        self.assertTrue(merged.startswith(old))
        self.assertTrue(merged.endswith('<figure>N1</figure><figure>N2</figure>'))
        self.assertEqual(U.merge_gallery_html(None, []), '')


# ---- run the REAL model method on a tiny ORM fake -------------------------------------------
class AccessError(Exception):
    pass


class ValidationError(Exception):
    pass


def _extract_method():
    src = (ROOT / 'models/gallery_push.py').read_text()
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CrmLeadGalleryPush')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'crm005_push_documents_to_gallery')
    fn.decorator_list = []
    mod = ast.Module(body=[fn], type_ignores=[])
    ns = dict(_=lambda s: s, hashlib=hashlib, AccessError=AccessError, ValidationError=ValidationError,
              PushImageError=U.PushImageError, existing_hashes=U.existing_hashes, figure_html=U.figure_html,
              merge_gallery_html=U.merge_gallery_html, heal_escaped_figures=U.heal_escaped_figures, prepare_image=U.prepare_image,
              PUSH_MAX_IMAGES=U.PUSH_MAX_IMAGES, PUSH_MAX_HTML_BYTES=U.PUSH_MAX_HTML_BYTES)
    exec(compile(ast.fix_missing_locations(mod), 'gallery_push.py', 'exec'), ns)
    return ns['crm005_push_documents_to_gallery']


METHOD = _extract_method()


class Doc:
    def __init__(self, ident, name, data, file_type='image', readable=True):
        self.id, self.name, self._data, self.file_type, self.readable = ident, name, data, file_type, readable
        self.sudo_used = False

    def check_access(self, mode):
        if mode != 'read' or not self.readable:
            raise AccessError('no')

    def sudo(self):
        self.sudo_used = True
        return self

    @property
    def raw(self):
        return self._data


class DocModel:
    def __init__(self, docs):
        self.docs = {d.id: d for d in docs}

    def browse(self, ids):
        return Recs([self.docs.get(i, _Missing(i)) for i in ids])


class _Missing:
    def __init__(self, i):
        self.id = i


class Recs(list):
    def exists(self):
        return Recs([d for d in self if not isinstance(d, _Missing)])


class Lead:
    # Odoo returns Html field values as markupsafe.Markup: the fake does the same unless markup=False
    def __init__(self, html='', can_write=True, docs=(), markup=True):
        self._markup = markup
        self.x_yp_gallery_html = html
        self.can_write = can_write
        self.writes = []
        self.env = {'argo.document': DocModel(docs)}

    @property
    def x_yp_gallery_html(self):
        return Markup(self._html) if self._markup else self._html

    @x_yp_gallery_html.setter
    def x_yp_gallery_html(self, value):
        self._html = str(value)

    def ensure_one(self):
        return self

    def check_access(self, mode):
        if mode == 'write' and not self.can_write:
            raise AccessError('write denied')

    def write(self, vals):
        self.writes.append(vals)
        self.x_yp_gallery_html = vals['x_yp_gallery_html']


class MarkupRegressionTests(unittest.TestCase):
    """Update_065: Odoo's Markup value + a plain str used to escape the new tile into visible text."""

    def setUp(self):
        self.a = Doc(1, 'Thi công kho lạnh (4).jpg', img_bytes('JPEG', color=(10, 10, 10)))
        self.b = Doc(2, 'Cút 90 độ.png', img_bytes('PNG', color=(20, 20, 20)))

    def test_markup_existing_gallery_does_not_escape_new_tile(self):
        old = '<p><img src="data:image/png;base64,AAAA"></p>'
        lead = Lead(old, docs=[self.a])
        self.assertIsInstance(lead.x_yp_gallery_html, Markup)
        push(lead, [1])
        html = lead.x_yp_gallery_html
        self.assertNotIn('&lt;', html)
        self.assertNotIn('&#34;', html)
        self.assertTrue(html.startswith(old))
        self.assertEqual(html.count('<figure>'), 1)
        self.assertEqual([e[1] for e in SYNC.gallery_entries(html)][-1], 'Thi công kho lạnh (4)')

    def test_utils_merge_with_markup_is_plain_concat(self):
        merged = U.merge_gallery_html(Markup('<p>x</p>'), ['<figure>N</figure>'])
        self.assertEqual(merged, '<p>x</p><figure>N</figure>')
        self.assertNotIn('&lt;', merged)
        self.assertIs(type(merged), str)

    def test_repairs_tile_already_escaped_by_update_064(self):
        good = U.figure_html('Kho lạnh (4).jpg', 'image/jpeg', img_bytes('JPEG'))
        from markupsafe import escape as mescape
        broken = str(mescape(good))           # exactly what Markup + str produced
        self.assertIn('&lt;figure&gt;', broken)
        keep = '<figure><img src="data:image/png;base64,AAAA"><figcaption>keep</figcaption></figure>'
        legit_text = '<p>giá &lt;figure&gt; là thẻ HTML</p>'
        lead = Lead(keep + broken + legit_text, docs=[self.b])
        res = push(lead, [2])
        html = lead.x_yp_gallery_html
        self.assertEqual(res['added'], 1)
        self.assertIn(good, html)
        self.assertNotIn('&lt;figure&gt;&lt;img', html)
        self.assertIn(legit_text, html)       # unrelated text is untouched
        self.assertEqual(html.count('<figure>'), 3)

    def test_repair_alone_writes_even_when_all_pushed_images_are_duplicates(self):
        good = U.figure_html('A.jpg', 'image/jpeg', self.a._data)
        from markupsafe import escape as mescape
        lead = Lead(str(mescape(good)), docs=[self.a])
        res = push(lead, [1])                 # same picture again -> duplicate, but the page must be repaired
        self.assertEqual((res['added'], res['duplicate']), (0, 1))
        self.assertEqual(len(lead.writes), 1)
        self.assertEqual(lead.x_yp_gallery_html, good)
        self.assertEqual(U.heal_escaped_figures(good), good)   # healthy HTML: no change, no extra write
        again = push(lead, [1])
        self.assertEqual(len(lead.writes), 1)

    def test_heal_ignores_escaped_figure_that_is_not_our_tile(self):
        txt = '&lt;figure&gt;&lt;img src=&#34;http://x/y.png&#34;&gt;&lt;/figure&gt;'
        self.assertEqual(U.heal_escaped_figures(txt), txt)


def push(lead, ids):
    return METHOD(lead, ids)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.a = Doc(1, 'Chữ Y.jpg', img_bytes('JPEG', color=(10, 10, 10)))
        self.b = Doc(2, 'Cút 90 độ.png', img_bytes('PNG', color=(20, 20, 20)))
        self.c = Doc(3, 'Cửa gió.webp', img_bytes('WEBP', color=(30, 30, 30)))

    def test_adds_in_requested_order_and_writes_once(self):
        lead = Lead('', docs=[self.a, self.b, self.c])
        res = push(lead, [3, 1, 2])
        self.assertEqual((res['added'], res['duplicate'], res['skipped']), (3, 0, []))
        self.assertEqual(len(lead.writes), 1)
        caps = [e[1] for e in SYNC.gallery_entries(lead.x_yp_gallery_html)]
        self.assertEqual(caps, ['Cửa gió', 'Chữ Y', 'Cút 90 độ'])
        self.assertTrue(self.a.sudo_used)

    def test_keeps_existing_and_skips_duplicates_on_repeat(self):
        old = '<p>keep me</p>'
        lead = Lead(old, docs=[self.a, self.b])
        push(lead, [1, 2])
        self.assertTrue(lead.x_yp_gallery_html.startswith(old))
        again = push(lead, [1, 2])
        self.assertEqual((again['added'], again['duplicate']), (0, 2))
        self.assertEqual(len(lead.writes), 1)  # no second write when nothing is new

    def test_duplicate_of_existing_inline_picture_is_skipped(self):
        existing = '<figure><img src="data:image/jpeg;base64,%s"></figure>' % base64.b64encode(self.a._data).decode()
        lead = Lead(existing, docs=[self.a, self.b])
        res = push(lead, [1, 2])
        self.assertEqual((res['added'], res['duplicate']), (1, 1))

    def test_same_bytes_twice_in_one_push_added_once(self):
        twin = Doc(9, 'copy.jpg', self.a._data)
        lead = Lead('', docs=[self.a, twin])
        res = push(lead, [1, 9])
        self.assertEqual((res['added'], res['duplicate']), (1, 1))

    def test_non_image_unreadable_and_broken_are_reported_not_fatal(self):
        pdf = Doc(4, 'catalog.pdf', b'%PDF', file_type='pdf')
        locked = Doc(5, 'secret.jpg', img_bytes(), readable=False)
        broken = Doc(6, 'broken.jpg', b'garbage')
        gif = Doc(7, 'anim.gif', img_bytes('GIF'))
        lead = Lead('', docs=[self.a, pdf, locked, broken, gif])
        res = push(lead, [1, 4, 5, 6, 7])
        self.assertEqual(res['added'], 1)
        reasons = {s['name']: s['reason'] for s in res['skipped']}
        self.assertEqual(set(reasons), {'catalog.pdf', '#5', 'broken.jpg', 'anim.gif'})
        self.assertEqual(reasons['catalog.pdf'], 'Không phải file ảnh.')
        self.assertNotIn('secret', ' '.join(reasons))  # name of an unreadable file is not leaked

    def test_requires_write_on_deal_and_does_not_touch_data(self):
        lead = Lead('x', can_write=False, docs=[self.a])
        with self.assertRaises(AccessError):
            push(lead, [1])
        self.assertEqual(lead.writes, [])

    def test_input_validation(self):
        lead = Lead('', docs=[self.a])
        for bad in (None, [], 'abc', [0], [-1], ['x'], [True and 'z'], list(range(1, 202))):
            with self.assertRaises(ValidationError):
                push(lead, bad)
        self.assertEqual(lead.writes, [])

    def test_unknown_ids_ignored(self):
        lead = Lead('', docs=[self.a])
        res = push(lead, [1, 999])
        self.assertEqual(res['added'], 1)

    def test_total_html_cap(self):
        old = U.PUSH_MAX_HTML_BYTES
        # patch the cap inside the extracted function's namespace
        ns = METHOD.__globals__
        ns['PUSH_MAX_HTML_BYTES'] = 300
        try:
            lead = Lead('', docs=[self.a])
            res = push(lead, [1])
            self.assertEqual(res['added'], 0)
            self.assertIn('quá lớn', res['skipped'][0]['reason'])
            self.assertEqual(lead.writes, [])
        finally:
            ns['PUSH_MAX_HTML_BYTES'] = old

    def test_mutation_guard_dedupe_uses_stored_bytes(self):
        # if the method hashed something else than the stored bytes, a second push would duplicate
        big = Doc(8, 'big.jpg', noisy_jpeg(1700))
        lead = Lead('', docs=[big])
        first = push(lead, [8])
        second = push(lead, [8])
        self.assertEqual((first['added'], second['added'], second['duplicate']), (1, 0, 1))


class ContractTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding='utf-8')

    def test_registered_and_versioned(self):
        self.assertIn('from . import gallery_push', self.read('models/__init__.py'))
        self.assertIn("'version': '19.0.1.66.0'", self.read('__manifest__.py'))

    def test_model_has_no_new_fields_or_sudo_write(self):
        src = self.read('models/gallery_push.py')
        self.assertNotIn('fields.', src)
        self.assertNotIn('sudo().write', src)
        self.assertNotIn('urlopen', src)
        self.assertNotIn('requests', src)
        self.assertEqual(src.count('sudo()'), 1)  # only the raw read, mirrors the 008 download controller

    def test_view_xml_and_css(self):
        tree = etree.parse(str(ROOT / 'views/crm_yp_lead_form.xml'))
        boxes = tree.xpath('//details[contains(@class,"sgt_yp_gallerybox")]')
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].get('name'), 'sgt_crm005_gallery_box')
        self.assertEqual(len(boxes[0].xpath('.//field[@name="x_yp_gallery_html"][@widget="sgt_gallery_manage"][@readonly="1"]')), 1)
        # Documents (Create Folder) and Evidence boxes are NOT hidden by class
        self.assertEqual(len(tree.xpath('//div[@name="crm005_documents_box"]')), 1)
        css = self.read('static/src/scss/yellowpages_profile.scss')
        self.assertIn('.o_form_view .sgt_yp_gallerybox:not(:has(.sgt_yp_gallery img))', css)
        self.assertIn('.o_form_view .sgt_yp_pbox:not(:has(.sgt_yp_partners img))', css)
        block = css[css.index('Update_064'):]
        self.assertNotIn('documents_box', block)
        self.assertNotIn('evbox', block)

    def test_documents_panel_button(self):
        xml = etree.parse(str(ROOT / 'static/src/xml/documents_panel.xml'))
        btn = xml.xpath('//button[@t-on-click="pushToGallery"]')
        self.assertEqual(len(btn), 1)
        js = self.read('static/src/js/documents_panel.js')
        self.assertIn('explorer_push_images_to_crm', js)
        self.assertIn('this.props.record.load()', js)


if __name__ == '__main__':
    unittest.main(verbosity=1)
