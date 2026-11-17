"""Xinyang Home product collection.

The public-facing Home is an internal Odoo client action. Every internal user may
read product metadata; only the Home Manager role may add/edit/archive/remove it.
Enforcement is via model ACLs, not through a hidden button alone.
"""
from odoo import api, fields, models


class SgtHomeProduct(models.Model):
    _name = 'sgt.home.product'
    _description = 'Xinyang Home product showcase'
    _order = 'sequence, id'

    name = fields.Char(string='Product title', required=True, translate=True,
                       help='Product name shown on Home. Write it in English, then use the globe icon '
                            'to add the Vietnamese title.')
    code = fields.Char(string='Model / product codes',
                       help='For example: XYPX, XYWT, ZP100 / ZP200.')
    subtitle = fields.Char(string='Short subtitle', translate=True,
                           help='One short line shown under the title in the product popup. Translate with the globe icon.')
    description = fields.Text(string='Product content', translate=True,
                              help='Content shown when a visitor clicks the product on Home: features, '
                                   'applications and notes. Type it by hand for every new product. '
                                   'One line per feature works well. Write it in English, then use the '
                                   'globe icon to add the Vietnamese text.')
    category = fields.Selection([
        ('air', 'Air distribution'),
        ('silencer', 'Acoustic solutions'),
        ('fire', 'Fire & smoke control'),
        ('other', 'Other technical equipment'),
    ], string='Product category', required=True, default='air')
    image = fields.Image(string='Product image', max_width=2200, max_height=2200,
                         help='Upload a clear product photo or designed product poster (square preferred).')
    image_ids = fields.One2many('sgt.home.product.image', 'product_id', string='Extra images',
                                help='More pictures of this product. They appear as small pictures under the main '
                                     'picture in the product popup, in this order.')
    has_image = fields.Boolean(compute='_compute_has_image')
    sequence = fields.Integer(string='Display order', default=10)
    active = fields.Boolean(string='Show on Home', default=True)
    internal_note = fields.Text(string='Internal notes (not shown on Home)',
                                help='Source reference, internal review notes, and production reminders.')

    @api.depends('image')
    def _compute_has_image(self):
        for rec in self:
            rec.has_image = bool(rec.image)
