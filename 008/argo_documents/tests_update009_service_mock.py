"""Run: python tests_update009_service_mock.py. Executes actual folder service method using a minimal ORM fake."""
import ast
import importlib.util
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parent
naming_path = BASE / 'models/crm_folder_naming.py'
spec = importlib.util.spec_from_file_location('naming', naming_path)
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)

class UserError(Exception):
    pass

class AccessError(Exception):
    pass

s = (BASE / 'models/folder.py').read_text()
root_ast = ast.parse(s)
cls = next(n for n in root_ast.body if isinstance(n, ast.ClassDef) and n.name=='ArgoDocumentFolder')
method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name=='explorer_create_deal_folder')
method.decorator_list = []
code = compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(BASE/'models/folder.py'), 'exec')
namespace = dict(_=lambda x: x, AccessError=AccessError, UserError=UserError, re=re,
                 normalize_company_tax=N.normalize_company_tax,
                 folder_name_for_company=N.folder_name_for_company,
                 matches_company_tax_folder=N.matches_company_tax_folder,
                 check_item_name=lambda s:s)
exec(code, namespace)
create_folder = namespace['explorer_create_deal_folder']

class Rec:
    def __init__(self, ident, name, parent_id=0, lead_id=0, active=True, can_edit=True):
        self.id = ident; self.name = name; self.parent_id = parent_id; self.lead_id = lead_id
        self.crm_lead_ids = set(); self.active = active; self.company_id = None
        self.can_edit = can_edit
    def sudo(self):return self
    def write(self, vals):
        for cmd in vals.get('crm_lead_ids', []):
            if cmd[0]==4:self.crm_lead_ids.add(cmd[1])
        return True
    def _can_level(self, x): return self.can_edit or x=='view'
    def check_access(self, x):return True
    def _log_permission(self, *args):return True

class RS(list):
    def __getattr__(self, key):
        if len(self)==1:return getattr(self[0], key)
        raise AttributeError(key)
    def sudo(self):return self
    def with_context(self, **kwargs):return self
    def filtered(self, pred):return RS([x for x in self if pred(x)])
    def write(self, vals):
        for x in self:x.write(vals)
        return True

class FakeLead:
    _fields = {'x_yp_tax_code':True}
    def __init__(self, ident, company, tax):
        self.id=ident;self.partner_name=company;self.tax=tax;self.company_id=None
    def __getitem__(self, name):
        assert name=='x_yp_tax_code'
        return self.tax
    def check_access(self, mode):return True

class FakeLeadModel:
    def __init__(self, lead):self.lead=lead
    def browse(self, ident):
        return self
    def exists(self): return self.lead

class FakeCr:
    def execute(self, query, args):
        assert 'pg_advisory_xact_lock' in query

class FakeUser:
    def has_group(self, name):return True

class FakeEnv:
    def __init__(self, lead):
        self.cr=FakeCr();self.user=FakeUser();self.models={'crm.lead':FakeLeadModel(lead)}
    def __getitem__(self,name):return self.models[name]

class Service:
    explorer_create_deal_folder=create_folder
    def __init__(self, lead, existing=()):
        self.env=FakeEnv(lead)
        self.root=Rec(90,'CRM Information')
        self.root.crm_shared_root=True;self.root.access_mode='public'
        self.records=list(existing)
        self.next_id=100
        self.created=[]
    def _is_manager(self):return False
    def _crm_root_folder(self):return self.root
    def sudo(self):return self
    def with_context(self, **kw):return self
    def search(self, domain, limit=None):
        if domain[0]=='|':
            lid=domain[1][2]
            rs=RS([r for r in self.records if r.lead_id==lid or lid in r.crm_lead_ids])
        else:
            tax=domain[1][2]
            rs=RS([r for r in self.records if r.parent_id==90 and tax.lower() in r.name.lower()])
        return RS(rs[:limit] if limit else rs)
    def browse(self, ident):return RS([r for r in self.records if r.id==ident])
    def _require_create_parent(self, root):return True
    def create(self, vals):
        self.next_id+=1
        record=Rec(self.next_id,vals['name'],parent_id=vals['parent_id'],lead_id=vals['lead_id'])
        self.records.append(record);self.created.append(record)
        return record

class ModelMethodTests(unittest.TestCase):
    def test_create_then_idempotent(self):
        svc=Service(FakeLead(2,'Công ty ABC','0312345678'))
        first=svc.explorer_create_deal_folder(2)
        self.assertEqual(first['name'],'Công ty ABC - 0312345678')
        self.assertFalse(first['already_exists'])
        second=svc.explorer_create_deal_folder(2)
        self.assertTrue(second['already_exists'])
        self.assertEqual(len(svc.created),1)
    def test_reuse_legacy_tax_folder(self):
        svc=Service(FakeLead(3,'Công ty ABC','0312345678'),[Rec(22,'0312345678',parent_id=90)])
        result=svc.explorer_create_deal_folder(3)
        self.assertEqual(result['id'],22)
        self.assertEqual(len(svc.created),0)
    def test_reuse_new_style_from_other_deal(self):
        svc=Service(FakeLead(3,'Công ty ABC MỚI','0312345678'),[Rec(22,'Công ty ABC - 0312345678',parent_id=90,lead_id=2)])
        result=svc.explorer_create_deal_folder(3)
        self.assertEqual(result['id'],22)
        self.assertIn(3,svc.records[0].crm_lead_ids)
    def test_detect_ambiguous_tax(self):
        records=[Rec(22,'0312345678',parent_id=90),Rec(23,'Công ty ABC - 0312345678',parent_id=90)]
        svc=Service(FakeLead(3,'Công ty ABC','0312345678'),records)
        with self.assertRaises(UserError):svc.explorer_create_deal_folder(3)
        self.assertFalse(svc.created)
    def test_never_reuse_partial_tax(self):
        svc=Service(FakeLead(3,'Công ty ABC','0312345678'),[Rec(22,'Công ty ABC - 00312345678',parent_id=90)])
        result=svc.explorer_create_deal_folder(3)
        self.assertNotEqual(result['id'],22)
    def test_missing_tax_or_company(self):
        for company, tax in [('Công ty ABC',''),('','0312345678')]:
            svc=Service(FakeLead(3,company,tax))
            with self.assertRaises(UserError):svc.explorer_create_deal_folder(3)

if __name__ == '__main__':unittest.main(verbosity=2)
