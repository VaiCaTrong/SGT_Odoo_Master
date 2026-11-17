"""CRM-005 Update_009 offline check: Source/Address are VISIBLE for an Opportunity.

Update_008 attached Address to group lead_priority, which Odoo hides when
type == 'opportunity'.  This test applies the real XPath specs of the CRM-005 form
to the base Deal form (2026-10-11 Scan, argv[1]) and checks, for every ancestor of
the inserted fields, that no `invisible` rule hides it for an Opportunity.
"""
import copy, json, os, sys, unittest
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
XML = os.path.join(HERE, '..', 'views', 'crm_yp_lead_form.xml')
BASE = None


def specs():
    arch = etree.parse(XML).getroot().xpath("//field[@name='arch']")[0]
    return [c for c in arch if c.tag == 'xpath' and (
        "opportunity_partner" in c.get('expr', '') or 'tag_ids' in c.get('expr', ''))]


def combined():
    t = etree.fromstring(BASE.encode())
    for spec in specs():
        n = t.xpath(spec.get('expr'))
        assert len(n) == 1, ('anchor not unique', spec.get('expr'), len(n))
        for k in reversed([copy.deepcopy(c) for c in spec]):
            n[0].addnext(k)
    return t


def hidden_for(node, record_type):
    """True if an ancestor `invisible` rule of the exact form type == 'X' hides it."""
    for anc in node.iterancestors():
        inv = (anc.get('invisible') or '').replace('"', "'")
        if inv == "type == '%s'" % record_type: 
            return True
    return False


class OpportunityVisibility(unittest.TestCase):
    def setUp(self):
        if not BASE: self.skipTest('no base arch')

    def test_both_new_anchors_unique(self):
        combined()

    def test_source_visible_for_opportunity(self):
        t = combined()
        src = t.xpath("//group[@name='opportunity_partner']/field[@name='source_id']")
        self.assertEqual(len(src), 1)
        self.assertFalse(hidden_for(src[0], 'opportunity'))

    def test_address_visible_for_opportunity_and_lead(self):
        t = combined()
        streets = [f for f in t.xpath("//field[@name='street'][@string='Address']")]
        self.assertEqual(len(streets), 2)
        opp = [f for f in streets if not hidden_for(f, 'opportunity')]
        lead = [f for f in streets if not hidden_for(f, 'lead')]
        self.assertEqual(len(opp), 1, 'Address must be visible for an Opportunity')
        self.assertEqual(len(lead), 1, 'Address must be visible for a Lead')
        # directly after tag_ids in the Opportunity group
        self.assertEqual(opp[0].getprevious().get('name'), 'tag_ids')

    def test_update008_bug_would_have_been_caught(self):
        """Only the lead_priority insertion -> hidden for an Opportunity."""
        t = etree.fromstring(BASE.encode())
        n = t.xpath("//group[@name='lead_priority']/field[@name='tag_ids']")[0]
        f = etree.Element('field', name='street'); n.addnext(f)
        self.assertTrue(hidden_for(f, 'opportunity'))


if __name__ == '__main__':
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        BASE = [r for r in json.load(open(sys.argv[1])) if r['id'] == '1036'][0]['arch_db']
        del sys.argv[1:]
    unittest.main(verbosity=2)
