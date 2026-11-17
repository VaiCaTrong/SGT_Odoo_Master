"""Update_030: both CRM and native CRM-002 funnels show stage-age counts."""
from pathlib import Path
import ast
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ColumnProgressMirrors(unittest.TestCase):
    def test_progress_bars_mirrored_in_native_and_crm_templates(self):
        tree = ET.parse(ROOT / "static/src/xml/column_progress.xml")
        patches = {n.attrib["t-inherit"]: n for n in tree.getroot()}
        self.assertEqual(set(patches), {"crm.ColumnProgress", "web.ColumnProgress"})
        for template in patches.values():
            xpaths = template.findall("xpath")
            self.assertEqual([(xp.get("expr"), xp.get("position")) for xp in xpaths], [
                ("//div[hasclass('progress-bar')]", "attributes"),
                ("//div[hasclass('progress-bar')]", "inside"),
                ("//div[hasclass('o_column_progress')]", "after"),
            ])
            tooltip = xpaths[0].find("attribute")
            self.assertEqual(tooltip.get("name"), "t-attf-data-tooltip")
            self.assertIn("bar.count", tooltip.text)
            seg = xpaths[1].find("t")
            self.assertEqual(seg.attrib.get("t-if"), "['fresh', 'warn', 'late'].includes(bar.value)")
            self.assertEqual(seg.find("span").attrib["t-esc"], "bar.count")
            total = xpaths[2].find("span")
            self.assertEqual(total.attrib["t-esc"], "props.group.count")
            self.assertIn("['fresh', 'warn', 'late'].includes", total.attrib["t-if"])
        self.assertEqual([ET.tostring(x, encoding="unicode") for x in patches["crm.ColumnProgress"]],
                         [ET.tostring(x, encoding="unicode") for x in patches["web.ColumnProgress"]])

    def test_data_and_sale_still_use_native_controller_and_same_age_source(self):
        src = (ROOT / 'static/src/js/native_pipeline.js').read_text()
        self.assertIn('withCrm002Sidebar(kanbanView.Controller)', src)
        view = (ROOT / 'views/intake_kanban.xml').read_text()
        self.assertEqual(view.count('js_class">sgt_crm002_intake'), 2)
        age = (ROOT / 'views/lead_age_bell.xml').read_text()
        self.assertIn('name="sgt_crm002_age_bucket"', age)
        self.assertIn('"fresh": "success"', age)
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text())
        self.assertEqual(manifest['version'], '19.0.1.26.0')
        self.assertIn('sgt_crm_campaign/static/src/xml/column_progress.xml', manifest['assets']['web.assets_backend'])


if __name__ == '__main__':
    unittest.main()
