"""Odoo-free smoke tests executing extracted *actual* access computation + lock guard.

Only a stubbed recordset is used; full Odoo ACL integration still requires staging.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

SRC = (Path(__file__).resolve().parent / 'models/folder.py').read_text()
TREE = ast.parse(SRC)
CLASS = next(c for c in TREE.body if isinstance(c, ast.ClassDef) and c.name == 'ArgoDocumentFolder')

def extract(name, globals_dict=None):
    f = next(n for n in CLASS.body if isinstance(n, ast.FunctionDef) and n.name == name)
    copy = ast.FunctionDef(name=f.name, args=f.args, body=f.body, decorator_list=[], returns=None, type_comment=None)
    ns = {'UserError': ValueError, '_': lambda s: s}
    ns.update(globals_dict or {})
    exec(compile(ast.fix_missing_locations(ast.Module(body=[copy], type_ignores=[])), '<src>', 'exec'), ns)
    return ns[name]

class IDs:
    def __init__(self, ids=()): self.ids = list(ids)
    def __bool__(self): return bool(self.ids)
    @property
    def member_ids(self): return self
    @property
    def user_id(self): return self
    def sudo(self): return self
    def filtered(self, *_): return self

class Folder:
    def __init__(self, mode, owner=0, parent=None):
        self.access_mode=mode
        self.public_level='view'
        self.parent_id=parent
        self.crm_shared_root=False
        self.create_uid=SimpleNamespace(id=owner)
        for key in ('allowed_user_ids','editable_user_ids','full_user_ids',
                    'allowed_department_ids','editable_department_ids','full_department_ids',
                    'effective_user_ids','effective_edit_user_ids','effective_full_user_ids'):
            setattr(self,key,IDs())
    def __setattr__(self,k,v):
        if k.endswith('_ids') and k.startswith('effective_') and isinstance(v,list):
            v=IDs(v[0][2]);
        object.__setattr__(self,k,v)

class FakeLocked:
    def __init__(self, locked):
        self.locked=locked
    def __bool__(self): return True
    def sudo(self): return self
    def with_context(self, **k): return self
    def _all_descendants(self): return self
    def filtered(self, key):
        assert key in ('is_locked', 'system_root')
        return [1] if self.locked and key=='is_locked' else []

class TestRuntimeMock(unittest.TestCase):
    def test_private_child_can_edit_under_public_view_only_root(self):
        compute=extract('_compute_effective_access')
        root=Folder('public',owner=1)
        root.crm_shared_root=True
        compute([root])
        self.assertTrue(root.effective_read_public)
        self.assertFalse(root.effective_edit_public)
        child=Folder('private',owner=29,parent=root)
        compute([child])
        self.assertIn(29,child.effective_user_ids.ids)
        self.assertIn(29,child.effective_edit_user_ids.ids)
        self.assertNotIn(35,child.effective_user_ids.ids)
        self.assertFalse(child.effective_read_public)
        self.assertFalse(child.effective_full_public)

    def test_full_grant_on_child_does_not_grant_full_to_root(self):
        compute=extract('_compute_effective_access')
        root=Folder('public',owner=1)
        root.crm_shared_root=True
        compute([root])
        self.assertFalse(root.effective_full_public)
        child=Folder('restricted',owner=29,parent=root)
        child.allowed_user_ids=IDs([47])
        child.full_user_ids=IDs([47])
        compute([child])
        self.assertIn(47,child.effective_full_user_ids.ids)
        self.assertNotIn(47,root.effective_full_user_ids.ids)

    def test_legacy_child_does_not_become_public_under_crm_root(self):
        compute=extract('_compute_effective_access')
        root=Folder('public',owner=1)
        root.crm_shared_root=True
        compute([root])
        child=Folder('legacy',owner=29,parent=root)
        compute([child])
        self.assertEqual(child.effective_user_ids.ids,[29])
        self.assertEqual(child.effective_edit_user_ids.ids,[29])
        self.assertFalse(child.effective_read_public)

    def test_locked_folder_denies_delete_even_if_admin(self):
        guard=extract('_require_unlocked_subtree')
        with self.assertRaises(ValueError): guard(FakeLocked(True))
        guard(FakeLocked(False))

if __name__ == '__main__': unittest.main(verbosity=2)
