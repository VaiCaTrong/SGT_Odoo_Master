"""Release 061: validate additive inherited Kanban modifications without needing Odoo."""
from pathlib import Path
from lxml import etree
import ast
import unittest

ROOT=Path(__file__).resolve().parents[1]
XML=ROOT/'views/crm_yp_lead_kanban.xml'
JS=ROOT/'static/src/js/kanban_shortcuts_safe.js'
CSS=ROOT/'static/src/css/kanban_safe_links.css'
SCAN=ROOT/'tests/fixtures/odoo_scan_opportunity_base.xml'


def simulate_arch(base):
    original=etree.parse(str(XML))
    root=etree.fromstring(base.encode('utf-8'))
    for spec in original.xpath('//field[@name="arch"]//xpath'):
        hits=root.xpath(spec.attrib['expr'])
        assert len(hits)==1, f"XPath missed/multiple: {spec.attrib['expr']}, hits={len(hits)}"
        element=hits[0]
        if spec.get('position')=='attributes':
            for attr in spec.findall('attribute'):
                name=attr.get('name')
                if attr.get('add') is not None:
                    sep=attr.get('separator',' ')
                    original=element.get(name,'')
                    addition=attr.get('add','')
                    element.set(name,(original+sep+addition).strip(sep))
                else:
                    element.set(name,attr.text or '')
        elif spec.get('position')=='before':
            parent=element.getparent(); n=parent.index(element)
            for child in spec:
                if isinstance(child.tag,str):
                    parent.insert(n,etree.fromstring(etree.tostring(child))); n+=1
        elif spec.get('position')=='after':
            parent=element.getparent(); n=parent.index(element)+1
            for child in spec:
                if isinstance(child.tag,str):
                    parent.insert(n,etree.fromstring(etree.tostring(child))); n+=1
        elif spec.get('position')=='inside':
            for child in spec:
                if isinstance(child.tag,str):
                    element.append(etree.fromstring(etree.tostring(child)))
        elif spec.get('position')=='replace':
            parent=element.getparent(); n=parent.index(element); parent.remove(element)
            for child in spec:
                if isinstance(child.tag,str):
                    parent.insert(n,etree.fromstring(etree.tostring(child))); n+=1
        else:
            raise AssertionError(spec.get('position'))
    return root


class SafeKanban(unittest.TestCase):
    def test_scan_20261011_legacy_view(self):
        assert SCAN.exists(), 'the actual scanned base kanban is expected'
        r=simulate_arch(SCAN.read_text())
        self.assertEqual(len(r.xpath('//*[contains(@class,"sgt_crm005_safe_shortcuts")]')),1)
        self.assertEqual(len(r.xpath('//footer[contains(@class,"sgt_crm005_compact_footer")]/div[contains(@class,"sgt_crm005_safe_source")]')), 1)
        self.assertEqual(len(r.xpath('//footer/div[contains(@class,"sgt_crm005_safe_shortcuts")]')), 1)
        self.assertEqual(len(r.xpath('//field[@widget="kanban_color_picker"]')),1)
        self.assertEqual(len(r.xpath('//field[@name="user_id" and @widget="many2one_avatar_user"]')),1)
        self.assertEqual(len(r.xpath('//field[@name="tag_ids"]')),1)
        self.assertEqual(r.xpath('//kanban')[0].get('edit'),'true')
    def test_modified_view_missing_facebook_and_website_blocks(self):
        r=etree.parse(str(SCAN))
        for node in r.xpath("//t[@t-name='card']/t[@t-if='record.x_url_fb_profile and record.x_url_fb_profile.raw_value'] | //t[@t-name='card']/t[@t-elif='record.x_website and record.x_website.raw_value']"):
            node.getparent().remove(node)
        root=simulate_arch(etree.tostring(r).decode())
        self.assertEqual(len(root.xpath('//*[contains(@class,"sgt_crm005_safe_links")]')),1)
        self.assertEqual(len(root.xpath('//field[@name="user_id"]')),1)
    def test_no_fragile_xpaths_or_model_redefinitions(self):
        r=etree.parse(str(XML))
        paths=[x.get('expr') for x in r.xpath('//xpath')]
        self.assertEqual(len(paths),7)
        self.assertEqual(paths[-1],"//kanban/templates/t[@t-name='card']/footer")
        self.assertEqual([x.get('position') for x in r.xpath('//xpath')][-3:], ['attributes','inside','inside'])
        for p in paths:
            self.assertNotIn('x_url_fb_profile and',p)
            self.assertNotIn('x_website and',p)
            self.assertNotIn('kanban_color_picker',p)
        self.assertEqual(len(r.xpath('//xpath[contains(@expr,"x_url_fb_profile")]')),0)
        self.assertEqual(len(r.xpath('//xpath[contains(@expr,"x_website")]')),0)
        self.assertEqual((ROOT/'models/crm_lead.py').read_text().count('def action_crm005_kanban_open_folder'), 1)
        self.assertIn('from odoo import api,', (ROOT/'models/crm_lead.py').read_text())
    def test_links_have_class_and_record_fields(self):
        r=etree.parse(str(XML))
        kinds={x.get('data-sgt-crm005-kind') for x in r.xpath('//a[@data-sgt-crm005-kind]')}
        self.assertEqual(kinds,{'website','facebook','yellowpages','zalo'})
        used={'source_id','website','referred','x_url_fb_profile','x_link_fanpage','x_website','x_url_zalo_group'}
        fields={x.get('name') for x in r.xpath('//xpath[@position="before" and @expr="//kanban/templates"]/field')}
        self.assertTrue(used.issubset(fields))
        self.assertIn('readonly="1"',XML.read_text())
    def test_no_unsafe_redirect_or_global_patch(self):
        script=JS.read_text()
        for token in ['validatedUrl','"http:"','"https:"','YP_HOSTS','FB_HOSTS','ZALO_HOSTS','crm005_kanban_documents_available','sgtCrm005Ready']:
            self.assertIn(token,script)
        self.assertNotIn('KanbanRecord.prototype',script)
        self.assertNotIn('window.location.href =',script)
        self.assertIn('o_opportunity_kanban',CSS.read_text())
    def test_release_manifest_version(self):
        manifest=ast.literal_eval((ROOT/'__manifest__.py').read_text())
        self.assertEqual(manifest['version'],'19.0.1.67.0')
        self.assertIn('sgt_crm_yellowpages_profile/static/src/js/kanban_shortcuts_safe.js',manifest['assets']['web.assets_backend'])

if __name__=='__main__':unittest.main()
