"""Update_045: Only enable creating via full form and dragging Deal cards."""
import ast
from pathlib import Path
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]

def test_new_and_drag_are_enabled_but_quick_create_disabled():
    tree=etree.parse(str(ROOT/'views/crm_yp_lead_kanban.xml'))
    root=tree.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']/field[@name='arch']/xpath[@expr='//kanban' and @position='attributes']")
    assert len(root)==1
    a={x.get('name'): x.text for x in root[0].xpath('attribute')}
    assert a['create']=='true'
    assert a['records_draggable']=='true'
    for k in ('quick_create','edit','delete','groups_draggable','group_create','group_edit','group_delete'):
        assert a[k]=='false', k
    assert a['can_open']=='true'

def test_other_view_and_css_are_preserved():
    tree=etree.parse(str(ROOT/'views/crm_yp_lead_kanban.xml'))
    assert tree.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']/field[@name='arch']/xpath//a[@type='open']")
    css=(ROOT/'static/src/css/kanban_company_logo.css').read_text()
    assert 'margin-bottom: 16px !important;' in css
    manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text())
    assert manifest['version']=='19.0.1.45.0'
    assert 'argo_documents' in manifest['depends']
