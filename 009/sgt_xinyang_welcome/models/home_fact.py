from odoo import fields, models


class SgtHomeFact(models.Model):
    _name = 'sgt.home.fact'
    _description = 'Home highlight card'
    _order = 'sequence, id'

    name = fields.Char(string='Label', required=True, help='Small text under the number, e.g. "Year founded".')
    value = fields.Char(string='Value', required=True, help='Big text, e.g. a year, a number or a short phrase.')
    source = fields.Char(string='Source', help='Where this fact comes from (internal note, not shown).')
    accent = fields.Selection(
        [('blue', 'Blue'), ('red', 'Red')], string='Colour', default='blue', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
