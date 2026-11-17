"""Update_004: the user removed the Saigon Trade banner by mistake and asked for it back.

* If the slide was only ARCHIVED, the data file (noupdate) leaves it alone -> re-activate it here.
* If it was DELETED, Odoo re-creates it from data/home_data.xml during the upgrade (noupdate records whose
  XML id no longer exists are created again), so there is nothing to do here.
Runs once, when upgrading from a version older than 19.0.1.1.0.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    slide = env.ref('sgt_xinyang_welcome.slide_saigontrade', raise_if_not_found=False)
    if slide:
        slide = slide.with_context(active_test=False)
        if slide.exists() and not slide.active:
            slide.write({'active': True})
