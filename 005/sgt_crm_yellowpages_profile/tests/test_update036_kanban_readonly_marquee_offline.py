"""Update_036: offline XML, CSS and historical-scanned Kanban structure checks.

Does NOT validate current production Odoo registry, authorization, JS/browser runtime.
"""
from pathlib import Path
import ast
import csv
from io import TextIOWrapper
from zipfile import ZipFile

import pytest
from lxml import etree

MOD = Path(__file__).resolve().parents[1]
SCAN = Path('/mnt/data/Xinyang_ODOO_SCAN_20261011_000504.zip')


def _xml():
    p = etree.parse(str(MOD / 'views/crm_yp_lead_kanban.xml'))
    view = p.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']")
    assert len(view) == 1
    return view[0].xpath("./field[@name='arch']/xpath")


def test_read_only_is_kanban_view_only():
    xml = _xml()
    root = xml[0]
    assert root.get('expr') == '//kanban'
    assert root.get('position') == 'attributes'
    attrs = {a.get('name'): a.text for a in root.xpath('attribute')}
    assert attrs['can_open'] == 'true'
    # Update_045 deliberately restores New and drag (Update_036 was stricter).
    assert attrs['create'] == 'true'
    assert attrs['records_draggable'] == 'true'
    for name in ('edit','delete','quick_create','groups_draggable',
                 'group_create','group_edit','group_delete'):
        assert attrs[name] == 'false'
    # Do not change permissions, existing form, or the CRM-002 addon.
    manifest = ast.literal_eval((MOD/'__manifest__.py').read_text())
    assert tuple(map(int, manifest['version'].split('.'))) >= (19, 0, 1, 35, 0)
    assert manifest['depends'] == ['crm','crm_sync_contact_odoo2','argo_documents']
    assert 'security/ir.model.access.csv' not in manifest.get('data', [])


def test_company_row_click_opens_deal_and_logo_fallback_kept():
    xml = _xml()
    company = xml[2]
    assert company.get('position') == 'replace'
    link = company.xpath('./a[@type="open"]')
    assert len(link) == 1
    assert not link[0].xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " sgt_marq ")]')
    assert len(link[0].xpath('.//field[@name="x_company"]')) == 1
    assert link[0].xpath('.//img[@class="sgt_crm005_kanban_logo_img"]')
    assert link[0].xpath('.//i[contains(@class, "fa-building-o")]')
    assert link[0].xpath('.//span[contains(@class, "sgt_crm005_kanban_no_company")]')


def test_wrapped_company_and_existing_legacy_marquee_asset():
    manifest = ast.literal_eval((MOD / '__manifest__.py').read_text())
    assets = manifest['assets']['web.assets_backend']
    assert any(x.endswith('/sgt_marquee.js') for x in assets)
    css = (MOD / 'static/src/css/kanban_company_logo.css').read_text()
    assert 'font-size: 16px' in css
    assert 'font-weight: 700' in css
    assert 'overflow-wrap: anywhere' in css
    assert 'white-space: normal' in css
    js = (MOD / 'static/src/js/sgt_marquee.js').read_text()
    assert "node.closest('.sgt_marq')" in js
    assert "el.scrollLeft" in js
    assert "prefers-reduced-motion: reduce" in js


def test_activity_widget_is_passive_on_kanban():
    xml = _xml()
    activity = xml[3]
    assert activity.get('position') == 'replace'
    assert 'kanban_activity' in activity.get('expr')
    assert activity.xpath('./span[contains(@class,"sgt_crm005_activity_readonly")]')
    assert 'activity_state' in etree.tostring(xml[1]).decode()


def test_menu_color_change_disabled():
    xml = _xml()
    color = xml[4]
    assert color.get('position') == 'replace'
    assert "kanban_color_picker" in color.get('expr')
    assert not len(color)


def test_xpath_matches_historical_scan():
    if not SCAN.exists():
        pytest.skip('Historical Scan unavailable')
    with ZipFile(SCAN) as z:
        p = next(x for x in z.namelist() if x.endswith('/odoo_views.csv'))
        rows = csv.DictReader(TextIOWrapper(z.open(p), encoding='utf-8-sig', errors='replace'))
        row = next(x for x in rows if x['id'] == '1042' and x['type'] == 'kanban')
        base = etree.fromstring(row['arch_db'].encode())
    xml = _xml()
    for n in xml:
        nodes = base.xpath(n.get('expr'))
        assert len(nodes) == 1, (n.get('expr'), len(nodes))
    # Simulate part of inherited view replacing existing company node.
    old = base.xpath(xml[2].get('expr'))[0]
    parent = old.getparent()
    idx = parent.index(old)
    parent.remove(old)
    parent.insert(idx, xml[2][0])
    assert len(base.xpath('//t[@t-name="card"]//a[@type="open"]')) == 1
    assert len(base.xpath('//t[@t-name="card"]//field[@name="x_company"]')) == 1
