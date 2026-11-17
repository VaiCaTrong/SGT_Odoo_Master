"""Extra pictures of a Home product (shown under the main picture in the product popup)."""
from odoo import fields, models


class SgtHomeProductImage(models.Model):
    _name = 'sgt.home.product.image'
    _description = 'Xinyang Home product extra image'
    _order = 'sequence, id'

    product_id = fields.Many2one('sgt.home.product', string='Product', required=True,
                                 ondelete='cascade', index=True)
    sequence = fields.Integer(string='Order', default=10)
    image = fields.Image(string='Image', max_width=2200, max_height=2200, required=True)
