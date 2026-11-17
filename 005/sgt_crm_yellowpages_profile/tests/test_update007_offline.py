"""CRM-005 Update_007 offline checks (pure unittest, no Odoo, no database).

The fake ORM below reproduces ONLY what matters for this bug: External IDs
created in code survive ir.model.data._process_end() if and only if
noupdate is True.  This is a model of Odoo 19 behaviour read from its source
(odoo/addons/base/models/ir_model.py::_process_end); it does NOT replace a real
Upgrade on Demo 2.
"""
import importlib.util
import os
import unittest

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('crm005_hooks', os.path.join(HERE, '..', 'hooks.py'))
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)

LEGACY_ARCH = """<data><xpath expr="//sheet" position="inside"><notebook>
<page string="Deal Import Fields"><group><field name="x_deal_id"/></group></page>
</notebook></xpath></data>"""
SYNC_ARCH = "<data><xpath expr='//header' position='inside'><button name='x'/></xpath></data>"


class Rs:
    """Tiny recordset."""
    def __init__(self, store, model, ids):
        self.store, self.model, self.ids = store, model, list(ids)

    def __bool__(self): return bool(self.ids)
    def __len__(self): return len(self.ids)
    def __iter__(self): return iter(Rs(self.store, self.model, [i]) for i in self.ids)
    def __getitem__(self, i): return Rs(self.store, self.model, [self.ids[i]])
    @property
    def id(self): return self.ids[0] if self.ids else False
    def _rec(self): return self.store.tables[self.model][self.ids[0]]
    def __getattr__(self, name):
        if name in ('store', 'model', 'ids'): raise AttributeError(name)
        return self._rec()[name]
    def sudo(self): return self
    def with_context(self, **kw): return self
    def exists(self): return Rs(self.store, self.model, [i for i in self.ids if i in self.store.tables[self.model]])
    def browse(self, ids=None):
        if ids is None or ids is False: ids = []
        return Rs(self.store, self.model, ids if isinstance(ids, list) else [ids])
    def search(self, domain, limit=None):
        out = []
        for rid, rec in self.store.tables[self.model].items():
            ok = True
            for field, op, val in domain:
                assert op == '=', op
                if rec.get(field) != val: ok = False; break
            if ok: out.append(rid)
        return Rs(self.store, self.model, out[:limit] if limit else out)
    def write(self, vals):
        for i in self.ids:
            rec = self.store.tables[self.model][i]
            for k, v in vals.items(): rec[k] = v
        return True
    def unlink(self):
        for i in self.ids: self.store.tables[self.model].pop(i, None)
    def create(self, vals):
        rid = self.store.next_id(); self.store.tables[self.model][rid] = dict(vals); return Rs(self.store, self.model, [rid])
    def _get_combined_arch(self):
        return etree.fromstring('<form><details class="sgt_crm005_import_details"/></form>')


class Store:
    def __init__(self):
        self._n = 2000
        self.tables = {'ir.ui.view': {}, 'ir.model.data': {}}
        self.tables['ir.ui.view'][1036] = {'name': 'crm.lead.form', 'model': 'crm.lead', 'type': 'form', 'inherit_id': False, 'active': True, 'arch_db': '<form/>'}
        self.tables['ir.ui.view'][1098] = {'name': 'SGT - CRM Lead Import Fields (Auto)', 'model': 'crm.lead', 'type': 'form', 'inherit_id': 1036, 'active': True, 'arch_db': LEGACY_ARCH}
        self.tables['ir.ui.view'][1903] = {'name': 'sync', 'model': 'crm.lead', 'type': 'form', 'inherit_id': 1036, 'active': True, 'arch_db': SYNC_ARCH}
        self.env = Env(self)
    def next_id(self):
        self._n += 1; return self._n


class Env:
    def __init__(self, store): self.store = store
    def __getitem__(self, model): return Rs(self.store, model, [])
    def ref(self, xmlid, raise_if_not_found=True):
        assert xmlid == 'crm.crm_lead_view_form'
        return Rs(self.store, 'ir.ui.view', [1036])


def process_end(store, module, loaded_xmlids=()):
    """Faithful model of ir.model.data._process_end deletion rule."""
    for rid, imd in list(store.tables['ir.model.data'].items()):
        if imd['module'] != module or imd.get('noupdate') is True: continue
        if '%s.%s' % (imd['module'], imd['name']) in loaded_xmlids: continue
        store.tables[imd['model']].pop(imd['res_id'], None)
        store.tables['ir.model.data'].pop(rid)


def hide_views(store):
    return [r for r in store.tables['ir.ui.view'].values() if r['name'] == hooks.HIDE_VIEW_NAME]


class Update007(unittest.TestCase):
    def test_old_behaviour_is_deleted_by_cleanup(self):
        """Reproduces the Update_002..006 bug: noupdate=False -> deleted."""
        s = Store()
        v = s.env['ir.ui.view'].create({'name': hooks.HIDE_VIEW_NAME, 'model': 'crm.lead', 'inherit_id': 1098, 'active': True})
        s.env['ir.model.data'].create({'module': hooks.MODULE, 'name': hooks.HIDE_VIEW_XMLID_NAME, 'model': 'ir.ui.view', 'res_id': v.id, 'noupdate': False})
        process_end(s, hooks.MODULE)
        self.assertEqual(hide_views(s), [])

    def test_fresh_upgrade_survives_cleanup(self):
        s = Store()
        self.assertTrue(hooks.ensure_hide_legacy_import(s.env))
        process_end(s, hooks.MODULE)
        views = hide_views(s)
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]['inherit_id'], 1098)
        self.assertIn("//notebook[page[.//field[@name='x_deal_id']]]", views[0]['arch_db'])
        self.assertEqual(len(s.tables['ir.model.data']), 1)
        self.assertIs(list(s.tables['ir.model.data'].values())[0]['noupdate'], True)

    def test_second_upgrade_is_idempotent(self):
        s = Store()
        hooks.ensure_hide_legacy_import(s.env); process_end(s, hooks.MODULE)
        hooks.ensure_hide_legacy_import(s.env); process_end(s, hooks.MODULE)
        self.assertEqual(len(hide_views(s)), 1)
        self.assertEqual(len(s.tables['ir.model.data']), 1)

    def test_existing_noupdate_false_is_repaired(self):
        s = Store()
        v = s.env['ir.ui.view'].create({'name': hooks.HIDE_VIEW_NAME, 'model': 'crm.lead', 'type': 'form', 'inherit_id': 1098, 'active': False, 'arch_db': 'x'})
        s.env['ir.model.data'].create({'module': hooks.MODULE, 'name': hooks.HIDE_VIEW_XMLID_NAME, 'model': 'ir.ui.view', 'res_id': v.id, 'noupdate': False})
        hooks.ensure_hide_legacy_import(s.env); process_end(s, hooks.MODULE)
        views = hide_views(s)
        self.assertEqual(len(views), 1)
        self.assertTrue(views[0]['active'])

    def test_dangling_external_id_is_replaced(self):
        s = Store()
        s.env['ir.model.data'].create({'module': hooks.MODULE, 'name': hooks.HIDE_VIEW_XMLID_NAME, 'model': 'ir.ui.view', 'res_id': 99999, 'noupdate': False})
        self.assertTrue(hooks.ensure_hide_legacy_import(s.env)); process_end(s, hooks.MODULE)
        self.assertEqual(len(hide_views(s)), 1)

    def test_orphan_view_without_external_id_is_adopted(self):
        s = Store()
        s.env['ir.ui.view'].create({'name': hooks.HIDE_VIEW_NAME, 'model': 'crm.lead', 'type': 'form', 'inherit_id': 1098, 'active': True, 'arch_db': 'x'})
        hooks.ensure_hide_legacy_import(s.env); process_end(s, hooks.MODULE)
        self.assertEqual(len(hide_views(s)), 1)

    def test_two_legacy_views_does_not_raise_or_touch_data(self):
        s = Store()
        s.tables['ir.ui.view'][1999] = dict(s.tables['ir.ui.view'][1098], name='dup')
        self.assertFalse(hooks.ensure_hide_legacy_import(s.env))
        self.assertEqual(hide_views(s), [])

    def test_legacy_view_missing_does_not_raise(self):
        s = Store(); del s.tables['ir.ui.view'][1098]
        self.assertFalse(hooks.ensure_hide_legacy_import(s.env))

    def test_notebook_with_other_pages_removes_only_import_page(self):
        s = Store()
        s.tables['ir.ui.view'][1098]['arch_db'] = LEGACY_ARCH.replace('</notebook>', '<page string="Other"/></notebook>')
        hooks.ensure_hide_legacy_import(s.env)
        self.assertIn("//page[.//field[@name='x_deal_id']]", hide_views(s)[0]['arch_db'])


class StaticChecks(unittest.TestCase):
    def test_manifest_and_files(self):
        src = open(os.path.join(HERE, '..', '__manifest__.py'), encoding='utf-8').read()
        self.assertRegex(src, r"'version': '19\.0\.1\.\d+\.0'")
        self.assertIn('static/src/css/hide_legacy_import.css', src)
        self.assertTrue(os.path.exists(os.path.join(HERE, '..', 'static/src/css/hide_legacy_import.css')))
        self.assertTrue(os.path.exists(os.path.join(HERE, '..', 'upgrades/19.0.1.6.0/post-10-hide-legacy-import.py')))

    def test_no_view_creation_with_noupdate_false_left_in_hide_helper(self):
        src = open(os.path.join(HERE, '..', 'hooks.py'), encoding='utf-8').read()
        helper = src.split('def ensure_sync_contact_relocation')[0]
        self.assertNotIn("'noupdate': False", helper)


if __name__ == '__main__':
    unittest.main(verbosity=2)
