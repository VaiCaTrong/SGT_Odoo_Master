"""Run: python3 -I tests_update010_service_mock.py

Executes the REAL Update_010 service methods (explorer_crm_targets, explorer_push_images_to_crm,
_crm_link_folder) taken from models/folder.py on a minimal ORM fake.
"""
import ast
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent


class UserError(Exception):
    pass


class AccessError(Exception):
    pass


def extract(names):
    tree = ast.parse((BASE / 'models/folder.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ArgoDocumentFolder')
    out = {}
    for fn in cls.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in names:
            fn.decorator_list = []
            ns = dict(_=lambda s: s, AccessError=AccessError, UserError=UserError)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'folder.py', 'exec'), ns)
            out[fn.name] = ns[fn.name]
    assert set(out) == set(names), set(names) - set(out)
    return out


FUNCS = extract({'_crm_link_folder', 'explorer_crm_targets', 'explorer_push_images_to_crm'})


class RS(list):
    def __or__(self, other):
        return RS(list(dict.fromkeys(list(self) + list(other))))

    def __getitem__(self, i):
        r = list.__getitem__(self, i)
        return RS(r) if isinstance(i, slice) else r

    @property
    def id(self):
        return self[0].id if len(self) == 1 else False

    @property
    def ids(self):
        return [x.id for x in self]

    def sudo(self):
        return self

    def exists(self):
        return self

    def with_context(self, **kw):
        return self

    def filtered(self, f):
        return RS(x for x in self if f(x))

    def sorted(self, key=None):
        return RS(sorted(self, key=key))

    def check_access(self, mode):
        for x in self:
            x.check_access(mode)

    def browse(self, *a):
        return RS()


class Lead:
    def __init__(self, ident, partner_name='ACME', stage='New', readable=True, writable=True):
        self.id, self.partner_name, self.name, self.readable, self.writable = ident, partner_name, 'deal', readable, writable
        self.stage_id = type('S', (), {'name': stage})()

    def has_access(self, mode):
        return self.readable if mode == 'read' else self.writable

    def sudo(self):
        return self


class LeadModel:
    def __init__(self, leads, hook=True):
        self.leads = {l.id: l for l in leads}
        self.calls = []

    def browse(self, ident=None):
        if ident is None:
            return RS()
        return LeadView(self.leads[ident], self)

    def crm005_push_documents_to_gallery(self, ids):  # exists on the model => hasattr() is True
        raise AssertionError('must be called on a record')


class LeadView:
    def __init__(self, lead, model):
        self._lead, self._model = lead, model
        self.id = lead.id

    def __getattr__(self, k):
        return getattr(self._lead, k)

    def crm005_push_documents_to_gallery(self, ids):
        self._model.calls.append((self._lead.id, list(ids)))
        return {'added': len(ids), 'duplicate': 0, 'skipped': []}


class LeadModelNoHook:
    """crm.lead WITHOUT Update_064: attribute genuinely missing."""
    def __init__(self, leads):
        self.leads = {l.id: l for l in leads}

    def browse(self, ident=None):
        return RS() if ident is None else self.leads[ident]


class Doc:
    def __init__(self, ident, name, folder, file_type='image', readable=True):
        self.id, self.name, self.folder_id, self.file_type, self.readable = ident, name, folder, file_type, readable

    def check_access(self, mode):
        if not self.readable:
            raise AccessError('no read')


class DocModel:
    def __init__(self, docs):
        self.docs = {d.id: d for d in docs}

    def browse(self, ids):
        return RS(self.docs[i] for i in ids if i in self.docs)

    def search(self, domain, order=None, limit=None):
        want = dict((d[0], d[2]) for d in domain)
        rows = [d for d in self.docs.values()
                if d.folder_id.id == want['folder_id'] and d.file_type == want['file_type']]
        rows.sort(key=lambda d: (d.name, d.id))
        return RS(rows[:limit] if limit else rows)


class FM:
    """Folder model view used for sudo().browse()."""
    def __init__(self, reg):
        self.reg = reg

    def sudo(self):
        return self

    def with_context(self, **kw):
        return self

    def browse(self, ident=None):
        if ident is None or ident is False:
            return RS()
        f = self.reg.get(ident)
        return f if f else RS()


class Folder:
    def __init__(self, reg, ident, parent_path, leads=(), shared=()):
        self.reg, self.id, self.parent_path = reg, ident, parent_path
        self.lead_id = RS(leads)
        self.crm_lead_ids = RS(shared)
        self.readable = True
        reg[ident] = self

    def sudo(self):
        return self

    def with_context(self, **kw):
        return self

    def browse(self, ident=None):
        return FM(self.reg).browse(ident)

    def ensure_one(self):
        return self

    def __bool__(self):
        return True


class Svc:
    PUSH_IMAGE_LIMIT = 200

    def __init__(self, reg, leadmodel, docmodel, manager=False, internal=True):
        self.reg, self._manager, self._internal = reg, manager, internal
        user = type('U', (), {'has_group': lambda s, g: internal})()
        self.env = type('E', (), {'user': user})()
        self.env.__dict__['_m'] = {'crm.lead': leadmodel, 'argo.document': docmodel}
        self.env.__class__ = type('E2', (), {'user': user, '__getitem__': lambda s, k: s._m[k]})
        self.leadmodel = leadmodel

    def _is_manager(self):
        return self._manager

    def _get_folder(self, folder_id):
        if not folder_id:
            return RS()
        f = self.reg.get(int(folder_id))
        if not f:
            raise UserError('gone')
        if not f.readable:
            raise AccessError('folder')
        return f

    def sudo(self):
        return FM(self.reg)

    def browse(self, ident=None):
        return FM(self.reg).browse(ident)

    explorer_crm_targets = FUNCS['explorer_crm_targets']
    explorer_push_images_to_crm = FUNCS['explorer_push_images_to_crm']


def build(hook=True, internal=True):
    reg = {}
    leads = [Lead(11, 'ACME', 'New'), Lead(12, 'ACME 2', 'Qualified', writable=False), Lead(13, 'Hidden', readable=False)]
    # tree 1 / 2 / 3 / 4 :  1=CRM root, 2=deal folder (linked), 3=sub folder, 4=other deal folder (not linked)
    Folder(reg, 1, '1/')
    f2 = Folder(reg, 2, '1/2/', leads=[leads[0]], shared=[leads[1], leads[2]])
    f3 = Folder(reg, 3, '1/2/3/')
    f4 = Folder(reg, 4, '1/4/')
    docs = [
        Doc(101, 'b.jpg', f2), Doc(102, 'a.jpg', f2), Doc(103, 'catalog.pdf', f2, 'pdf'),
        Doc(104, 'sub.jpg', f3), Doc(105, 'other.jpg', f4), Doc(106, 'locked.jpg', f2, readable=False),
    ]
    lm = LeadModel(leads, hook) if hook else LeadModelNoHook(leads)
    svc = Svc(reg, lm, DocModel(docs), internal=internal)
    svc._link = None
    # bind the real helper as method of Folder records
    Folder._crm_link_folder = FUNCS['_crm_link_folder']
    return svc, lm, reg


class Targets(unittest.TestCase):
    def test_shared_folder_lists_visible_leads_with_write_flag(self):
        svc, lm, reg = build()
        res = svc.explorer_crm_targets(2)
        self.assertEqual(res['folder_id'], 2)
        self.assertEqual(res['link_folder_id'], 2)
        self.assertEqual([(l['id'], l['can_write']) for l in res['leads']], [(11, True), (12, False)])
        self.assertTrue(all(l['ref'].startswith('#') for l in res['leads']))

    def test_subfolder_uses_nearest_linked_ancestor(self):
        svc, lm, reg = build()
        res = svc.explorer_crm_targets(3)
        self.assertEqual(res['link_folder_id'], 2)
        self.assertEqual(len(res['leads']), 2)

    def test_unlinked_folder_and_root_have_no_targets(self):
        svc, lm, reg = build()
        self.assertEqual(svc.explorer_crm_targets(4)['leads'], [])
        self.assertEqual(svc.explorer_crm_targets(False), {'folder_id': False, 'leads': []})

    def test_unreadable_folder_and_non_internal_user(self):
        svc, lm, reg = build()
        reg[2].readable = False
        with self.assertRaises(AccessError):
            svc.explorer_crm_targets(2)
        svc2, _, _ = build(internal=False)
        with self.assertRaises(AccessError):
            svc2.explorer_crm_targets(2)


class Push(unittest.TestCase):
    def test_hook_missing_changes_nothing(self):
        svc, lm, reg = build(hook=False)
        with self.assertRaises(UserError) as cm:
            svc.explorer_push_images_to_crm(2, 11)
        self.assertIn('CRM-005', str(cm.exception))

    def test_lead_must_belong_to_folder(self):
        svc, lm, reg = build()
        for lead in (999, 13, 'x', None):
            with self.assertRaises((UserError, KeyError)):
                svc.explorer_push_images_to_crm(2, lead)
        with self.assertRaises(UserError):
            svc.explorer_push_images_to_crm(4, 11)  # folder 4 is not linked to deal 11
        self.assertEqual(lm.calls, [])

    def test_whole_folder_takes_only_direct_readable_images_sorted(self):
        svc, lm, reg = build()
        res = svc.explorer_push_images_to_crm(2, 11)
        # direct images: a.jpg(102), b.jpg(101), locked.jpg(106, search returns it, ACL is the hook's job)
        self.assertEqual(lm.calls, [(11, [102, 101, 106])])
        self.assertFalse(res['truncated'])
        self.assertEqual(res['lead_id'], 11)
        self.assertEqual(res['not_image'], 0)

    def test_selection_filters_outside_tree_and_counts_non_images(self):
        svc, lm, reg = build()
        # 105 belongs to another deal's folder -> dropped; 103 is a pdf; 104 is in a sub folder (allowed)
        res = svc.explorer_push_images_to_crm(2, 11, [104, 101, 105, 103, 102])
        self.assertEqual(lm.calls, [(11, [104, 101, 102])])  # selection order kept
        self.assertEqual(res['not_image'], 1)

    def test_selection_without_images_is_an_error(self):
        svc, lm, reg = build()
        with self.assertRaises(UserError):
            svc.explorer_push_images_to_crm(2, 11, [103])
        with self.assertRaises(UserError):
            svc.explorer_push_images_to_crm(2, 11, [105])  # only an outside file
        self.assertEqual(lm.calls, [])

    def test_unreadable_file_in_selection_blocks_the_call(self):
        svc, lm, reg = build()
        with self.assertRaises(AccessError):
            svc.explorer_push_images_to_crm(2, 11, [101, 106])
        self.assertEqual(lm.calls, [])

    def test_bad_document_ids(self):
        svc, lm, reg = build()
        for bad in ('abc', ['x'], list(range(2001))):
            with self.assertRaises(UserError):
                svc.explorer_push_images_to_crm(2, 11, bad)

    def test_limit_200(self):
        svc, lm, reg = build()
        extra = [Doc(1000 + i, 'z%03d.jpg' % i, reg[2]) for i in range(205)]
        svc.env['argo.document'].docs.update({d.id: d for d in extra})
        res = svc.explorer_push_images_to_crm(2, 11)
        self.assertTrue(res['truncated'])
        self.assertEqual(len(lm.calls[0][1]), 200)
        self.assertEqual(res['limit'], 200)

    def test_requires_a_folder(self):
        svc, lm, reg = build()
        with self.assertRaises(UserError):
            svc.explorer_push_images_to_crm(False, 11)


if __name__ == '__main__':
    unittest.main(verbosity=1)
