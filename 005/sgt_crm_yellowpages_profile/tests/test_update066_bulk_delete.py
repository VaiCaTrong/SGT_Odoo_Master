"""Update_066: Image Gallery multi-select delete. Odoo-free: the REAL model methods run on a tiny ORM fake.

Run: python3 -I tests/test_update066_bulk_delete.py
"""
import ast
import re
import unittest
from pathlib import Path

from lxml import html as lxml_html
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]


class AccessError(Exception):
    pass


class ValidationError(Exception):
    pass


class UserError(Exception):
    pass


def _extract(names):
    tree = ast.parse((ROOT / 'models/crm_lead.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CrmLead')
    body = []
    for n in cls.body:
        if isinstance(n, ast.FunctionDef) and n.name in names:
            n.decorator_list = [d for d in n.decorator_list if getattr(d, 'id', '') == 'staticmethod']
            body.append(n)
        elif isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'GALLERY_BULK_DELETE_MAX':
            body.append(n)
    klass = ast.ClassDef(name='Impl', bases=[], keywords=[], body=body, decorator_list=[])
    mod = ast.fix_missing_locations(ast.Module(body=[klass], type_ignores=[]))
    ns = dict(_=lambda s: s, lxml_html=lxml_html, UserError=UserError, ValidationError=ValidationError,
              AccessError=AccessError)
    exec(compile(mod, 'crm_lead.py', 'exec'), ns)
    return ns['Impl']


Impl = _extract({'_crm005_remove_gallery_node', 'action_crm005_delete_gallery_images',
                 'action_crm005_delete_gallery_image'})


class _Env:
    def __init__(self, system):
        self._system = system

    def is_system(self):
        return self._system


class Lead(Impl):
    def __init__(self, html, can_write=True, system=True):
        self._html = str(html)
        self.can_write = can_write
        self.writes = []
        self.env = _Env(system)

    @property
    def x_yp_gallery_html(self):
        return Markup(self._html)  # Odoo hands Html values back as Markup

    def ensure_one(self):
        return self

    def check_access(self, mode):
        if mode == 'write' and not self.can_write:
            raise AccessError('write denied')

    def write(self, vals):
        self.writes.append(vals)
        self._html = str(vals['x_yp_gallery_html'])


def tile(n, caption=True):
    cap = '<figcaption>cap %d</figcaption>' % n if caption else ''
    return '<figure><img src="https://cdn.example.com/p/%d.jpg">%s</figure>' % (n, cap)


def gallery(n):
    return ''.join(tile(i) for i in range(n))


def srcs(html):
    return re.findall(r'/p/(\d+)\.jpg', str(html))


def prefix(n):
    return 'https://cdn.example.com/p/%d.jpg' % n


class BulkDelete(unittest.TestCase):
    def test_deletes_selected_in_one_write(self):
        lead = Lead(gallery(6))
        n = lead.action_crm005_delete_gallery_images([1, 3, 4], [prefix(1), prefix(3), prefix(4)], 6)
        self.assertEqual(n, 3)
        self.assertEqual(len(lead.writes), 1)
        self.assertEqual(srcs(lead.x_yp_gallery_html), ['0', '2', '5'])
        self.assertNotIn('cap 1', lead._html)  # the caption goes with its tile

    def test_order_of_indexes_does_not_matter(self):
        lead = Lead(gallery(5))
        lead.action_crm005_delete_gallery_images([4, 0, 2], [prefix(4), prefix(0), prefix(2)], 5)
        self.assertEqual(srcs(lead._html), ['1', '3'])

    def test_delete_everything_leaves_empty_gallery(self):
        lead = Lead(gallery(3))
        lead.action_crm005_delete_gallery_images([0, 1, 2], [prefix(i) for i in range(3)], 3)
        self.assertEqual(srcs(lead._html), [])
        self.assertEqual(len(lead.writes), 1)

    def test_images_in_plain_paragraph_wrappers(self):
        html = ''.join('<p><img src="%s"></p>' % prefix(i) for i in range(4)) + '<p>keep this text</p>'
        lead = Lead(html)
        lead.action_crm005_delete_gallery_images([0, 2], [prefix(0), prefix(2)], 4)
        self.assertEqual(srcs(lead._html), ['1', '3'])
        self.assertIn('keep this text', lead._html)
        self.assertEqual(lead._html.count('<p></p>'), 0)  # empty wrappers are cleaned

    def test_two_images_in_one_figure_keep_the_figure(self):
        html = '<figure><img src="%s"><img src="%s"></figure>' % (prefix(0), prefix(1))
        lead = Lead(html)
        lead.action_crm005_delete_gallery_images([0], [prefix(0)], 2)
        self.assertEqual(srcs(lead._html), ['1'])
        self.assertIn('<figure>', lead._html)

    def test_selecting_both_images_of_a_shared_figure(self):
        html = '<figure><img src="%s"><img src="%s"></figure>' % (prefix(0), prefix(1)) + tile(2)
        lead = Lead(html)
        lead.action_crm005_delete_gallery_images([0, 1], [prefix(0), prefix(1)], 3)
        self.assertEqual(srcs(lead._html), ['2'])

    def test_same_result_as_repeated_single_delete(self):
        a, b = Lead(gallery(7)), Lead(gallery(7))
        a.action_crm005_delete_gallery_images([5, 1, 3], [prefix(5), prefix(1), prefix(3)], 7)
        # single delete, from the highest index down so earlier indexes stay valid
        count = 7
        for i in (5, 3, 1):
            b.action_crm005_delete_gallery_image(i, prefix(i), count)
            count -= 1
        self.assertEqual(a._html, b._html)

    def test_single_delete_unchanged(self):
        lead = Lead(gallery(3))
        self.assertTrue(lead.action_crm005_delete_gallery_image(1, prefix(1), 3))
        self.assertEqual(srcs(lead._html), ['0', '2'])
        with self.assertRaises(UserError):
            lead.action_crm005_delete_gallery_image(0, 'wrong', 2)

    def test_result_is_not_escaped_with_markup_input(self):
        lead = Lead(gallery(3))
        lead.action_crm005_delete_gallery_images([0], [prefix(0)], 3)
        self.assertNotIn('&lt;', lead._html)
        self.assertEqual(lead._html.count('<figure>'), 2)


class BulkDeleteRefusals(unittest.TestCase):
    def assert_untouched(self, lead, exc, *args):
        before = lead._html
        with self.assertRaises(exc):
            lead.action_crm005_delete_gallery_images(*args)
        self.assertEqual(lead.writes, [])
        self.assertEqual(lead._html, before)

    def test_no_write_permission(self):
        self.assert_untouched(Lead(gallery(3), can_write=False), AccessError, [0], [prefix(0)], 3)

    def test_not_administrator_cannot_bulk_delete(self):
        # Update_067: group "Settings" only, even with write access on the Deal
        self.assert_untouched(Lead(gallery(3), system=False), AccessError, [0], [prefix(0)], 3)

    def test_administrator_check_runs_before_parsing_and_payload_checks(self):
        lead = Lead(gallery(3), system=False)
        with self.assertRaises(AccessError):
            lead.action_crm005_delete_gallery_images('garbage', None, 'x')
        self.assertEqual(lead.writes, [])

    def test_single_delete_still_open_to_non_administrators(self):
        lead = Lead(gallery(3), system=False)
        self.assertTrue(lead.action_crm005_delete_gallery_image(1, prefix(1), 3))
        self.assertEqual(srcs(lead._html), ['0', '2'])

    def test_gallery_count_changed(self):
        self.assert_untouched(Lead(gallery(3)), UserError, [0], [prefix(0)], 4)

    def test_fingerprint_mismatch_on_any_one(self):
        self.assert_untouched(Lead(gallery(4)), UserError, [0, 1], [prefix(0), prefix(3)], 4)

    def test_index_out_of_range(self):
        self.assert_untouched(Lead(gallery(3)), UserError, [0, 3], [prefix(0), prefix(3)], 3)

    def test_bad_payloads(self):
        lead = Lead(gallery(3))
        for idx, pre, cnt in (
            ([], [], 3),                              # nothing selected
            ([0, 0], [prefix(0), prefix(0)], 3),      # duplicate
            ([0, 1], [prefix(0)], 3),                 # length mismatch
            ([-1], [prefix(0)], 3),                   # negative
            ([True], [prefix(1)], 3),                 # bool is not an index
            (['0'], [prefix(0)], 3),                  # string index
            ([0.0], [prefix(0)], 3),                  # float index
            ([0], [None], 3),                         # prefix not a string
            ([0], ['x' * 129], 3),                    # prefix too long
            ([0], [prefix(0)], True),                 # bool count
            ([0], [prefix(0)], '3'),                  # string count
            ('0', prefix(0), 3),                      # not lists
            (None, None, 3),
        ):
            self.assert_untouched(lead, ValidationError, idx, pre, cnt)

    def test_limit_500(self):
        n = Impl.GALLERY_BULK_DELETE_MAX
        self.assertEqual(n, 500)
        lead = Lead(gallery(5))
        self.assert_untouched(lead, ValidationError, list(range(n + 1)), ['x'] * (n + 1), 5)

    def test_unparsable_gallery(self):
        lead = Lead('')
        lead._html = ''
        self.assert_untouched(lead, UserError, [0], [prefix(0)], 0)

    def test_server_checks_write_before_anything_else(self):
        src = (ROOT / 'models/crm_lead.py').read_text()
        body = src.split('def action_crm005_delete_gallery_images', 1)[1].split('def action_crm005_delete_gallery_image(', 1)[0]
        self.assertLess(body.index("check_access('write')"), body.index('lxml_html.fragment_fromstring'))
        self.assertEqual(body.count('self.write('), 1)  # one write only


if __name__ == '__main__':
    unittest.main()
