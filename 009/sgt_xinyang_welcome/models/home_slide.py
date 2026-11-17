import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Only http(s) links or site-relative links (single leading /) are allowed on a banner button.
_SAFE_URL_RE = re.compile(r'^(https?://\S+|/(?!/)\S*)$', re.I)


class SgtHomeSlide(models.Model):
    _name = 'sgt.home.slide'
    _description = 'Home banner slide'
    _order = 'sequence, id'

    name = fields.Char(string='Title', required=True)
    tag = fields.Char(string='Small label', help='Short red label above the title, e.g. the company name.')
    text = fields.Text(string='Text')
    button_label = fields.Char(string='Button label')
    button_url = fields.Char(string='Button link', help='Full https:// address, or a path starting with /.')
    theme = fields.Selection(
        [('blue', 'Xinyang (blue)'), ('red', 'Saigon Trade (red)')],
        string='Colour', default='blue', required=True)
    image = fields.Image(
        string='Picture', max_width=1920, max_height=1200,
        help='Optional. Recommended 960 x 560 px. When empty the company logo is shown.')
    has_image = fields.Boolean(compute='_compute_has_image')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.depends('image')
    def _compute_has_image(self):
        for rec in self:
            rec.has_image = bool(rec.image)

    @api.constrains('button_url')
    def _check_button_url(self):
        for rec in self:
            url = (rec.button_url or '').strip()
            if url and not _SAFE_URL_RE.match(url):
                raise ValidationError(
                    'The button link must start with https://, http:// or /. Got: %s' % url)
