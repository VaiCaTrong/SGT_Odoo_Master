"""Update_059: scoped Kanban link navigation, no change to other modules."""
import ast
import re
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "views/crm_yp_lead_kanban.xml"
JS = ROOT / "static/src/js/kanban_deal_new_tab.js"
MANIFEST = ROOT / "__manifest__.py"


def _root():
    return etree.parse(str(VIEW))


def test_company_anchor_real_record_url_preserves_odoo_normal_click():
    anchors = _root().xpath("//a[@type='open' and contains(@class,'sgt_crm005_kanban_company')]")
    assert len(anchors) == 1
    anchor = anchors[0]
    assert anchor.get("t-att-href") == "'/odoo/crm.lead/' + record.id.raw_value"
    assert anchor.get('target') is None
    assert anchor.xpath("./span[contains(@class,'sgt_crm005_kanban_logo')]")
    assert anchor.xpath("./div[contains(@class,'sgt_crm005_kanban_company_name')]")


def test_script_handles_modifier_and_middle_click_without_global_patch():
    code = JS.read_text()
    for token in ('event.ctrlKey', 'event.metaKey', '"auxclick"', 'event.button !== 1',
                  'event.stopImmediatePropagation()', 'window.open(info.url',
                  'event.preventDefault()', '.o_opportunity_kanban .o_kanban_record'):
        assert token in code
    assert 'KanbanRecord.prototype' not in code
    assert 'patch(' not in code
    assert 'window.location.href =' not in code


def test_other_controls_are_excluded():
    code = JS.read_text()
    for token in ('"button"', '"input"', '"select"', '"textarea"',
                  '".dropdown"', '".oe_kanban_action"'):
        assert token in code
    assert 'isOtherControl(event.target, info.link)' in code


def test_version_and_legacy_features_unchanged():
    tree = _root()
    attrs = {
        el.get('name'): (el.text or '')
        for el in tree.xpath("//xpath[@expr='//kanban'][@position='attributes']/attribute")
    }
    assert attrs['can_open'] == attrs['create'] == attrs['records_draggable'] == 'true'
    assert attrs['quick_create'] == attrs['groups_draggable'] == attrs['delete'] == 'false'
    manifest = ast.literal_eval(MANIFEST.read_text())
    assert manifest['version'] == '19.0.1.58.0'
    assets = manifest['assets']['web.assets_backend']
    assert 'sgt_crm_yellowpages_profile/static/src/js/kanban_deal_new_tab.js' in assets
    assert 'sgt_crm_yellowpages_profile/static/src/js/geo_coordinate_actions.js' in assets
    assert 'sgt_crm_yellowpages_profile/static/src/js/documents_panel.js' in assets


def test_no_server_or_geo_changes():
    assert JS.exists()
    assert not re.search(r"href=[\"']#[\"']", VIEW.read_text())
