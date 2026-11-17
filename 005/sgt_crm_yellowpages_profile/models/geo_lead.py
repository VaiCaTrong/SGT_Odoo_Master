"""CRM-005 Update_047: independent geolocation of CRM Deals.

Extension import stays fast: create/write only queue the address; Odoo cron
geocodes a small batch later via base_geolocalize's standard base.geocoder.
No res.partner is created or modified.
"""
import logging
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .geo_utils import address_is_usable, address_signature, valid_coordinates, geocoder_postal_code

_logger = logging.getLogger(__name__)
_ADDRESS_FIELDS = frozenset(('street', 'street2', 'city', 'state_id', 'zip', 'country_id'))
_INTERNAL_CONTEXT = 'sgt_crm005_geo_internal'


class CrmLeadGeolocation(models.Model):
    _inherit = 'crm.lead'

    x_yp_latitude = fields.Float(string='Latitude', digits=(10, 7), copy=False)
    x_yp_longitude = fields.Float(string='Longitude', digits=(10, 7), copy=False)
    x_yp_geo_status = fields.Selection([
        ('missing', 'Thiếu địa chỉ'),
        ('pending', 'Chờ định vị tự động'),
        ('estimated', 'Đã định vị (chưa xác minh)'),
        ('manual', 'Tọa độ nhập thủ công'),
        ('review', 'Địa chỉ đổi — cần kiểm tra tọa độ thủ công'),
        ('failed', 'Không tìm thấy tọa độ'),
    ], string='Geolocation Status', default='missing', copy=False, readonly=True)
    # Store confidence tier separately from the numeric coordinate. A returned
    # city/province centroid is NEVER asserted as the company's exact address.
    x_yp_geo_precision = fields.Selection([
        ('address', 'Address match (unverified)'),
        ('neighborhood', 'Neighborhood / ward (approximate)'),
        ('city', 'City (approximate)'),
        ('region', 'Province / state (approximate)'),
        ('manual', 'Manually entered (not provider-verified)'),
    ], string='Geolocation Precision', copy=False, readonly=True)
    x_yp_geo_updated_at = fields.Datetime(string='Geolocated At', copy=False, readonly=True)
    x_yp_geo_attempted_at = fields.Datetime(string='Last Geolocation Attempt', copy=False, readonly=True)
    x_yp_geo_attempt_count = fields.Integer(string='Geolocation Attempts', default=0, copy=False, readonly=True)
    x_yp_geo_address_key = fields.Char(string='Last Geolocation Address Signature', copy=False, readonly=True)

    def _crm005_geo_address(self):
        self.ensure_one()
        # Access the persisted Deal address, never a Contact / res.partner.
        # with_context(lang) is used only when resolving state/country names.
        return {
            'street': self.street or '',
            'street2': self.street2 or '',
            'city': self.city or '',
            'state': self.state_id.name if self.state_id else '',
            'zip_code': self.zip or '',
            'country': self.country_id.name if self.country_id else '',
        }

    def _crm005_geo_signature(self):
        d = self._crm005_geo_address()
        return address_signature(**d)

    def _crm005_geo_is_usable(self):
        return address_is_usable(**self._crm005_geo_address())

    def _crm005_geo_internal_write(self, vals):
        return self.with_context(**{_INTERNAL_CONTEXT: True}).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        if self.env.context.get(_INTERNAL_CONTEXT):
            return leads
        # Do not geocode during Extension import. Only enqueue persisted records.
        for lead, initial_values in zip(leads, vals_list):
            # Initial manual coordinates (including an Extension that imports
            # explicit GPS) must not be silently overwritten by the worker.
            manually_supplied = 'x_yp_latitude' in initial_values or 'x_yp_longitude' in initial_values
            if manually_supplied and valid_coordinates(lead.x_yp_latitude, lead.x_yp_longitude):
                lead._crm005_geo_internal_write({
                    'x_yp_geo_status': 'manual',
                    'x_yp_geo_precision': 'manual',
                    'x_yp_geo_updated_at': fields.Datetime.now(),
                    'x_yp_geo_address_key': lead._crm005_geo_signature(),
                })
                continue
            state = 'pending' if lead._crm005_geo_is_usable() else 'missing'
            if lead.x_yp_geo_status != state:
                lead._crm005_geo_internal_write({'x_yp_geo_status': state})
        return leads

    def write(self, vals):
        if self.env.context.get(_INTERNAL_CONTEXT):
            return super().write(vals)
        address_changed_in_payload = bool(_ADDRESS_FIELDS.intersection(vals))
        geo_fields_in_payload = bool({'x_yp_latitude', 'x_yp_longitude'}.intersection(vals))
        # CRM forms/importers may resend unchanged GPS fields alongside a new
        # address. Do NOT classify unchanged values as manually entered GPS:
        # that would suppress the scheduled geocode and hide an outdated pin.
        previous_coordinates = {
            rec.id: (rec.x_yp_latitude, rec.x_yp_longitude) for rec in self
        } if geo_fields_in_payload else {}
        old_signature = {rec.id: rec._crm005_geo_signature() for rec in self} if address_changed_in_payload else {}
        previous_status = {rec.id: rec.x_yp_geo_status for rec in self} if address_changed_in_payload else {}
        result = super().write(vals)
        for lead in self:
            coordinates_changed = (
                geo_fields_in_payload and
                previous_coordinates[lead.id] != (lead.x_yp_latitude, lead.x_yp_longitude)
            )
            if coordinates_changed:
                # Explicitly modified GPS takes precedence over the new
                # address (including an intentional clear of the GPS fields).
                is_valid = valid_coordinates(lead.x_yp_latitude, lead.x_yp_longitude)
                lead._crm005_geo_internal_write({
                    'x_yp_geo_status': ('manual' if is_valid else ('pending' if lead._crm005_geo_is_usable() else 'missing')),
                    'x_yp_geo_precision': 'manual' if is_valid else False,
                    'x_yp_geo_address_key': lead._crm005_geo_signature() if is_valid else False,
                    'x_yp_geo_updated_at': fields.Datetime.now() if is_valid else False,
                    'x_yp_geo_attempt_count': 0,
                })
                continue
            if not address_changed_in_payload:
                continue
            if old_signature[lead.id] == lead._crm005_geo_signature():
                continue  # Re-imported identical address; no API work.
            if previous_status[lead.id] in ('manual', 'review') and valid_coordinates(
                    lead.x_yp_latitude, lead.x_yp_longitude):
                lead._crm005_geo_internal_write({'x_yp_geo_status': 'review'})
            else:
                # P0 fix: NEVER erase a successful GPS pair merely because
                # an importer/user changed the address. Keep last-known GPS,
                # precision, date and *old* address signature for audit; mark
                # the new address pending and replace the pair atomically ONLY
                # when geocoding returns a valid result. CRM-006 refuses
                # pending/failed records, preventing stale Contact sync.
                lead._crm005_geo_internal_write({
                    'x_yp_geo_status': 'pending' if lead._crm005_geo_is_usable() else 'missing',
                    'x_yp_geo_attempt_count': 0,
                    'x_yp_geo_attempted_at': False,
                })
        return result

    def _crm005_geo_lookup(self):
        """Progressive geocoding through Odoo's configured base.geocoder.

        All candidate queries use the SAME provider/configuration as Contacts.
        Unlike res.partner._geo_localize(), this method also returns the tier
        of the FIRST successful query, so approximate pins are not mislabelled
        as a company's actual building. Never create or edit res.partner.

        Returns (latitude, longitude, precision) or None.
        """
        self.ensure_one()
        address = self.with_context(lang='en_US')._crm005_geo_address()
        if not address_is_usable(**address):
            return None
        street, ward, city, state, country = (
            address['street'], address['street2'], address['city'],
            address['state'], address['country'])
        zip_code = geocoder_postal_code(address['zip_code'], country)
        full_street = ', '.join(part for part in (street, ward) if part)
        geocoder = self.env['base.geocoder'].sudo()

        candidates = []
        def add(level, **params):
            # Never silently geocode a country alone. Keep country enforced in
            # geo_find to avoid an identical locality name in another country.
            if params.get('country') and any(params.get(k) for k in ('street','city','state')):
                candidates.append((level, params))

        if full_street:
            add('address', street=full_street, zip=zip_code,
                city=city, state=state, country=country)
            if city or zip_code:
                add('address', street=full_street, state=state, country=country)
        # Some map providers understand a ward/industrial area even when the
        # street number or industrial lot is missing. Mark this approximate.
        if ward and (city or state):
            add('neighborhood', street=ward, city=city, state=state, country=country)
            if city:
                add('neighborhood', street=ward, state=state, country=country)
        if city:
            add('city', city=city, state=state, country=country)
        if state:
            add('region', state=state, country=country)

        seen = set()
        for level, params in candidates:
            query = geocoder.geo_query_address(**params)
            if not query or query in seen:
                continue
            seen.add(query)
            coords = geocoder.geo_find(query, force_country=country)
            if coords and len(coords) >= 2 and valid_coordinates(coords[0], coords[1]):
                return float(coords[0]), float(coords[1]), level
        return None

    def _crm005_geo_process(self, manual=False):
        self.ensure_one()
        # Caller must enforce record write ACL. Cron acts as configured cron user.
        if not self._crm005_geo_is_usable():
            if not (self.x_yp_geo_status in ('manual', 'review') and not manual):
                self._crm005_geo_internal_write({'x_yp_geo_status': 'missing'})
            return 'missing'
        provider_error = False
        try:
            coords = self._crm005_geo_lookup()
        except Exception:
            _logger.exception('CRM-005 geolocation provider failed for Deal id=%s', self.id)
            coords = None
            provider_error = True
        now = fields.Datetime.now()
        if not coords:
            # Never discard manually-verified coordinates when a provider fails.
            if manual and self.x_yp_geo_status in ('manual', 'review'):
                return 'failed_preserved'
            self._crm005_geo_internal_write({
                'x_yp_geo_status': 'failed',
                'x_yp_geo_attempted_at': now,
                'x_yp_geo_attempt_count': self.x_yp_geo_attempt_count + 1,
            })
            return 'provider_error' if provider_error else 'failed'
        # New lookup returns the precision tier as a third component.
        # Accept old 2-number stub results for compatibility with existing
        # offline regressions; production returns three components.
        precision = coords[2] if len(coords) >= 3 else 'address'
        self._crm005_geo_internal_write({
            'x_yp_latitude': coords[0],
            'x_yp_longitude': coords[1],
            'x_yp_geo_status': 'estimated',
            'x_yp_geo_precision': precision,
            'x_yp_geo_updated_at': now,
            'x_yp_geo_attempted_at': now,
            'x_yp_geo_attempt_count': 0,
            'x_yp_geo_address_key': self._crm005_geo_signature(),
        })
        return 'estimated'

    def action_crm005_geolocate_now(self):
        """Immediate feedback on the button, never a silently disappearing toast.

        A successful geocode uses a native reload to show the saved values.
        A no-match/provider failure uses a persistent warning without a reload.
        """
        self.ensure_one()
        self.check_access('write')
        if self.x_yp_geo_status in ('manual', 'review') and valid_coordinates(
                self.x_yp_latitude, self.x_yp_longitude):
            raise UserError(_('Manual coordinates are protected. To replace them, clear both Latitude and Longitude, save the Deal, then use Get Coordinates.'))
        if not self._crm005_geo_is_usable():
            raise UserError(_('Please provide at least the country and a city or province/state before geolocating.'))
        status = self._crm005_geo_process(manual=True)
        if status == 'estimated':
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        if status == 'provider_error':
            message = _('The geolocation service did not respond successfully. Check the Odoo geolocation provider settings and server logs.')
            kind = 'danger'
        elif status == 'failed_preserved':
            message = _('No coordinates found. The previously entered coordinates have been preserved. Check the address or the geolocation provider.')
            kind = 'warning'
        elif status == 'missing':
            message = _('The address is insufficient. Provide a country and a city or province/state.')
            kind = 'warning'
        else:
            message = _('No coordinates found at street, neighborhood, city or province level. Check the Odoo geolocation provider and country/state fields.')
            kind = 'warning'
        # Provider information helps distinguish an address not indexed in the
        # chosen map service from an Odoo UI problem. The provider itself can
        # silently translate network errors into None; never claim certainty.
        try:
            provider = self.env['base.geocoder'].sudo()._get_provider()
            provider_name = (provider.name or provider.tech_name or '').strip()
        except Exception:
            provider_name = ''
        if provider_name:
            message = (_('%(message)s\nGeolocation provider: %(provider)s.') %
                       {'message': message, 'provider': provider_name})
        
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _('Get Coordinates'), 'message': message,
            'type': kind, 'sticky': True,
        }}

    def action_crm005_find_on_map(self):
        """Open a company/address search for a human to pick the exact pin.

        This does NOT geocode or save an estimated point to the Deal.
        Only a deliberate click sends the search terms to Google Maps.
        """
        self.ensure_one()
        self.check_access('read')
        d = self._crm005_geo_address()
        # The company name is important for industrial parks whose lot numbers
        # are not in the street-address index; use standard address fields too.
        parts = [self.partner_name or '', d['street'], d['street2'],
                 d['city'], d['state'], d['country']]
        query = ', '.join(dict.fromkeys(
            p.strip() for p in parts if p and p.strip()))
        if not query:
            raise UserError(_('Please enter a company name or address before searching on the map.'))
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.google.com/maps/search/?api=1&query=' + quote(query, safe=''),
            'target': 'new',
        }

    @api.model
    def _cron_crm005_geolocate_pending(self):
        """Bounded worker. Extension writes queue a job; never HTTP in write()."""
        leads = self.search([('x_yp_geo_status', '=', 'pending')],
                            order='write_date asc, id asc', limit=5)
        processed = 0
        for lead in leads:
            try:
                with self.env.cr.savepoint():
                    # A concurrent user may edit the address; only auto-process pending.
                    if lead.x_yp_geo_status == 'pending':
                        lead._crm005_geo_process(manual=False)
                        processed += 1
            except Exception:
                _logger.exception('CRM-005 background geolocation failed for Deal id=%s', lead.id)
                # Do not keep a poison record at the head of the queue forever.
                with self.env.cr.savepoint():
                    lead._crm005_geo_internal_write({
                        'x_yp_geo_status': 'failed',
                        'x_yp_geo_attempted_at': fields.Datetime.now(),
                    })
        return processed
