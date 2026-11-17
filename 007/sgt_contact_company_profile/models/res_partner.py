from odoo import fields, models


class ResPartner(models.Model):
    """CRM-007 Update_002: 14 stored profile/marker fields and one non-stored related company logo.

    The production Scan of res.partner (176 fields) has no field able to hold this data.  The 13 profile
    fields are the same data as on the CRM Deal (CRM-005) and are only DISPLAYED (read-only) on the Contact:
    they are written by the CRM-006 button "Cập nhật Contact".  x_sgt_crm_synced is set by that button and
    tells the form which Contacts come from CRM (Person avatar stays editable).

    Reused, NOT created: Tax Code = vat, Vietnamese introduction = comment (Notes), logo = image_1920.
    """
    _inherit = 'res.partner'

    x_type_contact = fields.Char(string='Business Type', copy=False)
    x_country = fields.Char(string='Main Market', copy=False)
    x_yp_employee_range = fields.Char(string='Employee Size', copy=False)
    x_fb_industry = fields.Char(string='Business Industries', copy=False)
    x_url_zalo_group = fields.Char(string='Link Zalo Group', copy=False)
    x_url_fb_profile = fields.Char(string='Link Profile', copy=False)
    x_group_link = fields.Char(string='Group URL', copy=False)
    x_group_post_link = fields.Char(string='Post URL', copy=False)
    x_yp_founded_year = fields.Integer(string='Founded Year', copy=False)
    x_yp_listing_url = fields.Char(string='Yellow Pages Link', copy=False)
    x_yp_intro_en = fields.Html(string='Company Introduction (English)', copy=False)
    x_yp_gallery_html = fields.Html(string='Image Gallery', copy=False)
    x_yp_partners_html = fields.Html(string='Partners', copy=False)
    x_sgt_crm007_company_logo = fields.Image(
        string='Company Logo', related='parent_id.image_128', store=False, readonly=True,
        help='Only a live read of the linked Company logo; no duplicate picture is stored on the Person.')
    x_sgt_crm_synced = fields.Boolean(
        string='Synced from CRM', copy=False, readonly=True,
        help='Set by CRM-006 on successful synchronization. Does not lock the Person avatar.')
