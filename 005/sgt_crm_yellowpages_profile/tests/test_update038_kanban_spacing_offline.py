"""CRM-005 Update_038 offline-only regression checks for Kanban spacing."""
import ast
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_bump_and_existing_css_asset():
    m = ast.literal_eval((ROOT / '__manifest__.py').read_text())
    assert tuple(map(int, m['version'].split('.'))) >= (19, 0, 1, 37, 0)
    assert m['depends'] == ['crm', 'crm_sync_contact_odoo2', 'argo_documents']
    assert m['data'] == ['views/crm_yp_lead_form.xml', 'views/crm_yp_lead_kanban.xml']
    assert any(path.endswith('/kanban_company_logo.css') for path in m['assets']['web.assets_backend'])


def test_spacing_is_on_rendered_cards_and_scoped_to_crm_opportunities():
    css = (ROOT / 'static/src/css/kanban_company_logo.css').read_text()
    assert '.o_opportunity_kanban .o_kanban_group .o_kanban_record {' in css
    block = css.split('.o_opportunity_kanban .o_kanban_group .o_kanban_record {', 1)[1].split('}', 1)[0]
    assert 'margin-bottom: 16px !important;' in block
    assert 'margin-left' not in block and 'margin-right' not in block
    assert 'padding' not in block


def test_kanban_data_and_actions_preserved():
    tree = etree.parse(str(ROOT / 'views/crm_yp_lead_kanban.xml'))
    xpaths = tree.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']/field[@name='arch']/xpath")
    assert len(xpaths) == 5
    attrs = {a.get('name'): a.text for a in xpaths[0].xpath('attribute')}
    for k in ('create', 'records_draggable'):
        assert attrs[k] == 'true'  # restored in Update_045
    for k in ('edit','delete','quick_create'):
        assert attrs[k] == 'false'
    assert xpaths[2].xpath('.//a[@type="open"]')
    assert xpaths[2].xpath('.//field[@name="x_company"]')
    assert xpaths[2].xpath('.//img[@class="sgt_crm005_kanban_logo_img"]')
