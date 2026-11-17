"""CRM-005 Update_037: offline static and mocked JS hover checks (no Odoo runtime)."""
import ast
import shutil
import subprocess
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_no_new_security_models():
    manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text())
    assert tuple(map(int, manifest['version'].split('.'))) >= (19, 0, 1, 36, 0)
    assert manifest['depends'] == ['crm', 'crm_sync_contact_odoo2', 'argo_documents']
    assert 'security/ir.model.access.csv' not in manifest['data']


def test_title_size_and_responsive_weight():
    css = (ROOT / 'static/src/css/kanban_company_logo.css').read_text()
    assert 'font-size: 16px;' in css
    assert 'font-size: 15px;' in css
    assert 'font-weight: 700;' in css
    assert 'object-fit: contain;' in css
    assert '.sgt_crm005_activity_readonly' in css


def test_kanban_still_opens_deal_and_disables_inline_edits():
    tree=etree.parse(str(ROOT / 'views/crm_yp_lead_kanban.xml'))
    xpath_nodes=tree.xpath("//record[@id='view_crm005_yellowpages_lead_kanban']/field[@name='arch']/xpath")
    assert len(xpath_nodes) == 5
    attrs={el.get('name'):el.text for el in xpath_nodes[0].xpath('attribute')}
    assert attrs['can_open']=='true'
    assert attrs['records_draggable']=='true'  # restored in Update_045
    assert attrs['create']=='true'  # restored in Update_045
    for k in ('edit','delete','quick_create'):
        assert attrs[k]=='false'
    assert xpath_nodes[2].xpath('.//a[@type="open"]')
    assert not xpath_nodes[2].xpath('.//div[contains(@class,"sgt_marq")]')


def test_legacy_marquee_and_card_hover_handlers_exist():
    js=(ROOT / 'static/src/js/sgt_marquee.js').read_text()
    for fragment in ("function findCompanyCard", "node.closest('.o_kanban_record')", "card.closest('.o_opportunity_kanban')",
                     "card.querySelector('.sgt_crm005_kanban_company_name.sgt_marq')",
                     "if (to && active.card.contains(to))", "var scope = node.closest('.sgt_marq')",
                     "prefers-reduced-motion: reduce"):
        assert fragment in js


def test_mocked_dom_hover_runtime():
    if not shutil.which('node'):
        pytest.skip('Node.js unavailable')
    result=subprocess.run(['node', str(Path(__file__).with_name('node_update037_hover_smoke.js'))], capture_output=True, text=True, timeout=10)
    assert result.returncode==0, result.stderr
    assert 'PASS' in result.stdout
