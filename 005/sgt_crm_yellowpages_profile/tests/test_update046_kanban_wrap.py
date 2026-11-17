"""Update_046: compact company title with multi-line wrapping, logo stays alongside."""
import ast
from pathlib import Path
from lxml import etree
ROOT = Path(__file__).resolve().parents[1]


def _view():
    tree = etree.parse(str(ROOT / 'views/crm_yp_lead_kanban.xml'))
    return tree.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']/field[@name='arch']/xpath")


def _block(css, selector):
    assert selector in css
    return css.split(selector, 1)[1].split('}', 1)[0]


def test_name_wraps_in_same_flex_row_as_logo_without_marquee():
    row = _view()[2].xpath('./a[@type="open"]')
    assert len(row) == 1
    logo = row[0].xpath('./span[contains(@class,"sgt_crm005_kanban_logo")]')
    title = row[0].xpath('./div[contains(@class,"sgt_crm005_kanban_company_name")]')
    assert len(logo) == len(title) == 1
    assert row[0].index(logo[0]) < row[0].index(title[0])
    assert 'sgt_marq' not in title[0].get('class', '').split()
    assert title[0].xpath('.//field[@name="x_company"]')
    css = (ROOT / 'static/src/css/kanban_company_logo.css').read_text()
    row_block = _block(css, '.o_opportunity_kanban .sgt_crm005_kanban_company {')
    title_block = _block(css, '.o_opportunity_kanban .sgt_crm005_kanban_company_name {')
    assert 'display: flex;' in row_block and 'align-items: center;' in row_block
    assert 'flex: 1 1 0%;' in title_block and 'min-width: 0;' in title_block
    assert 'white-space: normal;' in title_block
    assert 'overflow-wrap: anywhere;' in title_block
    assert 'font-size: 16px;' in title_block
    assert 'font-weight: 700;' in title_block
    assert 'white-space: nowrap;' not in title_block
    child_block = _block(css, '.o_opportunity_kanban .sgt_crm005_kanban_company_name .o_field_widget,')
    assert 'white-space: normal !important;' in child_block
    assert 'width: 100%;' in child_block
    assert 'overflow-wrap: anywhere;' in child_block


def test_mobile_font_logo_and_kanban_actions_remain():
    css = (ROOT / 'static/src/css/kanban_company_logo.css').read_text()
    assert 'font-size: 15px;' in css
    assert 'flex-basis: 44px;' in css
    assert 'flex: 0 0 52px;' in css
    assert 'margin-bottom: 16px !important;' in css
    attrs={x.get('name'): x.text for x in _view()[0].xpath('attribute')}
    assert attrs['create'] == attrs['records_draggable'] == 'true'
    assert attrs['quick_create'] == attrs['groups_draggable'] == 'false'
    manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text())
    assert manifest['version'] in ('19.0.1.45.0', '19.0.1.46.0')
    assert manifest['depends'][:3]==['crm', 'crm_sync_contact_odoo2', 'argo_documents']
    assert any(x.endswith('/sgt_marquee.js') for x in manifest['assets']['web.assets_backend'])
