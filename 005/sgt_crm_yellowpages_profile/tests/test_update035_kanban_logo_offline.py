"""Offline tests only: do not claim Odoo staging/production is validated."""
from pathlib import Path
import ast
import csv
from io import TextIOWrapper
import zipfile

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SCAN = Path('/mnt/data/Xinyang_ODOO_SCAN_20261011_000504.zip')


def _extension():
    root = etree.parse(str(ROOT / 'views/crm_yp_lead_kanban.xml'))
    view = root.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']")[0]
    assert view.xpath("./field[@name='inherit_id'][@ref='crm.crm_case_kanban_view_leads']")
    return view


def test_xml_xpath_structure():
    view = _extension()
    xps = view.xpath('./field[@name="arch"]/xpath')
    assert len(xps) == 5
    assert xps[0].get('position') == 'attributes'
    assert xps[1].get('position') == 'before'
    assert xps[2].get('position') == 'replace'
    assert xps[3].get('position') == 'replace'
    assert xps[4].get('position') == 'replace'
    assert xps[2].xpath(".//span[contains(@class,'sgt_crm005_kanban_logo')]")
    assert xps[2].xpath(".//field[@name='x_company']")
    assert xps[2].xpath(".//img[@class='sgt_crm005_kanban_logo_img']")


def test_manifest_and_resources():
    m=ast.literal_eval((ROOT / '__manifest__.py').read_text())
    assert tuple(map(int,m['version'].split('.'))) >= (19,0,1,34,0)
    assert m['data'][-1]=='views/crm_yp_lead_kanban.xml'
    for asset in ['kanban_company_logo.css','kanban_company_logo_fallback.js']:
        assert any(x.endswith(asset) for x in m['assets']['web.assets_backend'])
    src=(ROOT/'views/crm_yp_lead_kanban.xml').read_text()
    assert 'x_yp_logo_upload' in src and 'x_image' in src
    assert 'fa-building-o' in src
    assert '/web/image/crm.lead/' in src
    js=(ROOT/'static/src/js/kanban_company_logo_fallback.js').read_text()
    assert 'addEventListener("error"' in js
    css=(ROOT/'static/src/css/kanban_company_logo.css').read_text()
    assert '52px' in css and 'object-fit: contain' in css


def test_inheritance_xpath_works_with_scanned_xinyang_opportunity_view():
    """Check only against the historical scan (2026-10-11), not current Odoo."""
    if not SCAN.exists():
        import pytest
        pytest.skip('Historical Xinyang scan not available')
    with zipfile.ZipFile(SCAN) as z:
        path=next(n for n in z.namelist() if n.endswith('/odoo_views.csv'))
        rows=csv.DictReader(TextIOWrapper(z.open(path), encoding='utf-8-sig', errors='replace'))
        row=next(x for x in rows if x['id']=='1042' and x['type']=='kanban')
        base=etree.fromstring(row['arch_db'].encode())
        ext=_extension().xpath('./field[@name="arch"]/xpath')
        replacements=base.xpath(ext[2].get('expr'))
        assert len(replacements)==1, 'Custom Xinyang company row no longer matches'
        assert replacements[0].xpath('.//field[@name="x_company"]')
        assert len(base.xpath(ext[1].get('expr')))==1
        # Simulate the two XML mutations (view inheritance in Odoo must be verified separately).
        target=replacements[0]
        parent=target.getparent()
        idx=parent.index(target)
        parent.remove(target)
        parent.insert(idx,ext[2][0])
        assert len(base.xpath('//t[@t-name="card"]//span[contains(@class,"sgt_crm005_kanban_logo")]'))==1
        assert len(base.xpath('//t[@t-name="card"]//field[@name="x_company"]'))==1
