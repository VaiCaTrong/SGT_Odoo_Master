import logging

from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import UserError, AccessError
from odoo.tools import html_escape

from . import push

_logger = logging.getLogger(__name__)

_RELATIONAL = ('state_id', 'country_id', 'user_id')


class CrmLead(models.Model):
    """CRM-006: after the existing "Create Contact" button (addon
    crm_sync_contact_odoo2), copy the Deal data into the Contact.

    No new field, no JS, no cron.  The old addon is not modified: when it ends a
    successful "Create Contact" it writes x_groupname / x_getfly_id on the Deal.
    Update_006 also watches partner_id linking (in either write order), and uses
    the existing x_sgt_crm_synced flag to avoid repeating the first full push.
    The full first push and the explicit button overwrite nonempty Deal fields;
    ordinary writes do not trigger that push.  Update_002: the company profile of CRM-007 (13 fields + Vietnamese introduction + logo) is MIRRORED on the
    Contact and on its parent Company (see push.py). Update_003 preserves Individual avatars and only mirrors logo to Company.
    """
    _inherit = 'crm.lead'

    # ------------------------------------------------------------------ trigger
    def write(self, vals):
        """Run the first *full* push after the legacy Create Contact links a partner.

        The legacy wizard can write partner_id and its result markers in separate
        orders.  Watch both transitions without modifying crm_sync_contact_odoo2.
        x_sgt_crm_synced is the existing per-partner marker; it prevents duplicate
        pushes when x_groupname / x_getfly_id are written again.

        IMPORTANT: No generic res.partner.create hook. Other Deal writes must not
        perform a full overwrite.  Legacy result-field writes are the best
        observable signal available without overriding the old wizard.
        """
        if self.env.context.get('sgt_crm006_skip'):
            return super().write(vals)
        relevant = bool(push.TRIGGER_FIELDS.intersection(vals) or 'partner_id' in vals)
        before = {}
        if relevant:
            for lead in self:
                before[lead.id] = {
                    'partner': lead.partner_id.id if lead.partner_id else False,
                    'markers': {key: (lead[key] if key in lead._fields else False)
                                for key in push.TRIGGER_FIELDS},
                }
        result = super().write(vals)
        if not relevant:
            return result
        for lead in self:
            partner = lead.partner_id
            if not partner or 'x_sgt_crm_synced' not in partner._fields:
                continue
            old = before.get(lead.id, {})
            just_linked = bool(partner.id and partner.id != old.get('partner'))
            # Writing a result marker after the partner was linked is the
            # normal sequence; no ordinary Deal edit should trigger the push.
            marker_changed = any(
                key in vals and bool(lead[key]) and lead[key] != old.get('markers', {}).get(key)
                for key in push.TRIGGER_FIELDS if key in lead._fields
            )
            # Other valid order: the legacy result marker was stored first,
            # and partner_id is assigned as the final step.
            linked_after_result = (just_linked and any(
                bool(lead[key]) for key in push.TRIGGER_FIELDS if key in lead._fields
            ))
            if not (marker_changed or linked_after_result):
                continue
            if not partner.x_sgt_crm_synced:
                try:
                    with self.env.cr.savepoint():
                        # Retain the existing first-contact synchronization.
                        lead._sgt_crm006_push_to_partner(overwrite_native=True, force_geo=False)
                except Exception:  # never block the legacy Create Contact flow
                    _logger.warning('CRM-006: first full push failed for lead %s', lead.id, exc_info=True)
            # The legacy button has completed: ensure CRM Information folder
            # independently of CRM-006 profile sync success. A folder error is
            # non-blocking and must not roll back the Contact or Deal.
            try:
                with self.env.cr.savepoint():
                    self.env['argo.document.folder'].explorer_create_deal_folder(lead.id)
            except (UserError, AccessError) as exc:
                _logger.info('CRM-006: Documents folder not created for Deal %s: %s', lead.id, exc)
                try:
                    with self.env.cr.savepoint():
                        lead.message_post(body=Markup(html_escape(
                            _('Documents: chưa thể tự tạo folder công ty/MST. %s', exc))),
                            message_type='comment', subtype_xmlid='mail.mt_note')
                except Exception:
                    _logger.warning('CRM-006: cannot post folder warning for Deal %s', lead.id, exc_info=True)
            except Exception:
                _logger.warning('CRM-006: automatic Documents folder failed for Deal %s', lead.id, exc_info=True)
        return result

    # ------------------------------------------------------------------ button
    def action_sgt_crm006_push_contact(self):
        """Button "Cập nhật Contact": run the same copy by hand (old Contacts)."""
        messages = []
        for lead in self:
            if not lead.partner_id:
                raise UserError(_('Deal "%s" chưa có Contact. Hãy bấm Create Contact trước.', lead.display_name))
            changed, failed, company_name, company_changed = lead._sgt_crm006_push_to_partner(force_note=True, overwrite_native=True, force_geo=True)
            messages.append(push.summary(changed, failed, company_name, company_changed))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cập nhật Contact'),
                'message': ' '.join(messages),
                'type': 'success' if not any('Không ghi được' in m for m in messages) else 'warning',
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------ data
    def _sgt_crm006_lead_data(self):
        """Deal values as plain data for push.build_wanted()."""
        self.ensure_one()
        fields_ = self._fields

        def opt(name):
            return self[name] if name in fields_ else False

        return {
            'partner_name': self.partner_name,
            # Person's contact coordinates. Keep Create Contact conservative; only the
            # explicit button may overwrite the values installed by the legacy wizard.
            'contact_name': self.contact_name,
            'email_from': self.email_from, 'x_email01': opt('x_email01'),
            'phone': self.phone, 'x_phone': opt('x_phone'),
            'x_mobilephone': opt('x_mobilephone'),
            'street': self.street, 'street2': self.street2, 'city': self.city, 'zip': self.zip,
            'state_id': self.state_id.id, 'country_id': self.country_id.id,
            'website': self.website, 'x_website': opt('x_website'),
            'function': self.function, 'x_jobtitle': opt('x_jobtitle'),
            'x_yp_tax_code': opt('x_yp_tax_code'),
            'user_id': self.user_id.id,
            'x_getfly_id': opt('x_getfly_id'),
            'tag_names': self.tag_ids.mapped('name'),
            # CRM-005 Update_054 GPS; never create or modify a Contact here.
            'x_yp_latitude': opt('x_yp_latitude'),
            'x_yp_longitude': opt('x_yp_longitude'),
            'x_yp_geo_status': opt('x_yp_geo_status'),
            'x_yp_geo_precision': opt('x_yp_geo_precision'),
            'x_yp_geo_address_key': opt('x_yp_geo_address_key'),
            'crm005_geo_current_key': self._crm005_geo_signature()
                if callable(getattr(self, '_crm005_geo_signature', None)) else False,
            # Update_002: profile (soft: a Deal field that does not exist is simply empty), logo
            'x_yp_logo_upload': opt('x_yp_logo_upload'),
            'x_image': opt('x_image'),
            **{src: opt(src) for src, _dst in push.PROFILE_MAP},
        }

    # ------------------------------------------------------------------ push
    def _sgt_crm006_push_to_partner(self, force_note=False, overwrite_native=False, force_geo=False):
        """Sync Deal data to its Contact and parent Company (no avatar overwrite).

        The first successful Create Contact event and explicit update both pass
        overwrite_native=True.  Empty source values never clear existing data.
        Returns (changed, failed, company_name, company_changed).
        """
        self.ensure_one()
        partner = self.partner_id.sudo()
        if not partner:
            return [], [], '', []
        data = self._sgt_crm006_lead_data()
        wanted = push.build_wanted(data)
        if overwrite_native:
            # Phone/email come from the Deal's actual contact, NOT from a generic
            # company profile.  Update only on an explicit user button press.
            wanted.update(push.build_contact_channels(data))
        profile = push.build_profile(data)
        logo = push.logo_value(data.get('x_yp_logo_upload'), data.get('x_image'))

        vals = {}
        old_name = partner.name
        fixed_name = push.collapse_repeated_name(old_name)
        if fixed_name and fixed_name != old_name:
            vals['name'] = fixed_name

        company = None
        company_link_failed = False
        if not partner.is_company:
            if partner.parent_id:
                company = partner.parent_id.sudo()
            else:
                company = self._sgt_crm006_find_or_create_company(data, wanted, fill_existing=not overwrite_native)
                if company:
                    vals['parent_id'] = company.id
                elif push.clean(data.get('partner_name')):
                    # A Company name was supplied but no unique valid Company
                    # could be linked. Do not report phantom success.
                    company_link_failed = True
        else:
            company_link_failed = False

        # Snapshot before Odoo's res.partner.write resets GPS on Address changes.
        previous_partner_geo = (partner.partner_latitude or 0.0, partner.partner_longitude or 0.0)
        previous_company_geo = (company.partner_latitude or 0.0, company.partner_longitude or 0.0) if company else None

        current = {key: (partner[key].id if key in _RELATIONAL else partner[key]) for key in wanted}
        native_diff = (push.overwrite_nonempty(current, wanted) if overwrite_native
                       else push.fill_empty(current, wanted))
        vals.update(native_diff)
        # Individual avatar is user-managed. Company receives the Deal logo.
        vals.update(self._sgt_crm006_mirror(partner, profile, logo if partner.is_company else False))

        changed, failed = self._sgt_crm006_write_partner(partner, vals)
        if company_link_failed and 'parent_id' not in failed:
            failed.append('parent_id')
        # The Company link is a separate, essential relationship: confirm it
        # actually persisted before treating it as a successful update.
        if 'parent_id' in vals and partner.parent_id.id != vals['parent_id']:
            if 'parent_id' in changed:
                changed.remove('parent_id')
            if 'parent_id' not in failed:
                failed.append('parent_id')
            company = None  # avoid mirroring onto an unlinked target
        if 'name' in changed and self.contact_name == old_name:
            # the old addon also copied the doubled name into the Deal's Contact Name
            self.with_context(sgt_crm006_skip=True).contact_name = fixed_name

        try:
            with self.env.cr.savepoint():
                added = self._sgt_crm006_add_tags(partner, data['tag_names'])
            if added:
                changed.append('category_id')
        except Exception:
            if 'category_id' not in failed:
                failed.append('category_id')
            _logger.warning('CRM-006: cannot update tags for partner %s', partner.id, exc_info=True)

        company_name, company_changed = '', []
        if company:
            company_vals = self._sgt_crm006_mirror(company, profile, logo)
            if overwrite_native:
                # The Company owns commercial address, website and tax code.
                company_wanted = {key: value for key, value in wanted.items()
                                  if key in push.ADDRESS_FIELDS + ('website', 'vat')}
                company_current = {key: (company[key].id if key in _RELATIONAL else company[key])
                                   for key in company_wanted}
                company_vals.update(push.overwrite_nonempty(company_current, company_wanted))
            company_changed, company_failed = self._sgt_crm006_write_partner(company, company_vals)
            company_name = company.name
            failed += [key for key in company_failed if key not in failed]
        if overwrite_native:
            # Write Company first, Person last: native commercial-address logic
            # may reset a Person's GPS while the parent Company is being saved.
            # No custom columns; manual button explicitly accepts CRM as source.
            pair = push.source_geo_pair(data)
            targets = []
            if company:
                targets.append((company, previous_company_geo, company_changed, 'Company'))
            targets.append((partner, previous_partner_geo, changed,
                            'Company' if partner.is_company else 'Contact'))
            for target, previous, updated, role in targets:
                address_changed = any(k in push.ADDRESS_FIELDS for k in updated)
                if pair:
                    wrote, errors = self._sgt_crm006_copy_geo(
                        target, previous, pair, role, explicit=force_geo,
                        address_changed=address_changed)
                else:
                    wrote, errors = self._sgt_crm006_geo_fallback(
                        target, previous, address_changed, role, explicit=force_geo)
                updated.extend(key for key in wrote if key not in updated)
                failed.extend(key for key in errors if key not in failed)

        shown = [key for key in changed + company_changed if key != push.SYNC_FLAG]
        if shown or failed or force_note:
            self.message_post(
                body=Markup(html_escape(push.summary(changed, failed, company_name, company_changed))),
                message_type='comment', subtype_xmlid='mail.mt_note')
        return changed, failed, company_name, company_changed

    def _sgt_crm006_copy_geo(self, target, before, desired, role, explicit=False,
                              address_changed=False):
        '''Sync CRM-005 GPS after Address writes, with a readback check.

        On legacy Create Contact, preserve any pre-existing different Contact
        GPS; an explicit Update Contact button is the operator's choice to
        replace it with CRM-005's valid coordinates. No provenance column.
        '''
        if (not explicit and push.valid_geo_pair(*before)
                and not push.geo_pairs_equal(before, desired)):
            # An existing different pin might have been set manually. A native
            # address write can reset it to zero, so restore the old value and
            # explicitly warn that it must be reviewed for the new address.
            if not push.geo_pairs_equal(
                    (target.partner_latitude, target.partner_longitude), before):
                if not self._sgt_crm006_restore_geo(target, before, role):
                    return [], ['Geolocation', 'GeoProtected' + role]
            return [], ['GeoProtected' + role]
        if push.geo_pairs_equal(
                (target.partner_latitude, target.partner_longitude), desired):
            return [], []
        try:
            with self.env.cr.savepoint():
                target.write({'partner_latitude': desired[0],
                              'partner_longitude': desired[1]})
                if not push.geo_pairs_equal(
                        (target.partner_latitude, target.partner_longitude), desired):
                    raise ValueError('CRM-006 GPS readback differs from CRM-005')
            return ['partner_latitude', 'partner_longitude'], []
        except Exception:
            _logger.warning('CRM-006: GPS copy failed for %s %s', role, target.id,
                            exc_info=True)
            return [], ['Geolocation']

    def _sgt_crm006_restore_geo(self, target, previous, role):
        '''Best-effort restoration only when Address did not change.'''
        if not push.valid_geo_pair(*previous):
            return False
        try:
            with self.env.cr.savepoint():
                target.write({'partner_latitude': previous[0],
                              'partner_longitude': previous[1]})
                if not push.geo_pairs_equal(
                        (target.partner_latitude, target.partner_longitude), previous):
                    raise ValueError('Contact GPS restore failed')
            return True
        except Exception:
            _logger.warning('CRM-006: GPS restore failed for %s %s', role, target.id,
                            exc_info=True)
            return False

    def _sgt_crm006_geo_fallback(self, target, before, address_changed, role,
                                  explicit=False):
        '''Legacy Odoo geocoder only when CRM-005 has no current valid GPS.'''
        if push.valid_geo_pair(*before) and (not address_changed or not explicit):
            # Auto Create flow never replaces an existing pin if CRM-005 has no
            # valid source. Restore if native Address handling reset the value.
            if not push.geo_pairs_equal(
                    (target.partner_latitude, target.partner_longitude), before):
                if not self._sgt_crm006_restore_geo(target, before, role):
                    return [], ['Geolocation']
            return ([], ['GeoProtected' + role]) if address_changed else ([], [])
        # Do not claim old coordinates are correct for a changed address.
        if not (target.street and target.city and target.country_id):
            return [], ['Geolocation'] if address_changed else []
        geo_method = getattr(target, 'geo_localize', None)
        if not callable(geo_method):
            return [], ['Geolocation']
        try:
            with self.env.cr.savepoint():
                geo_method()
                if not push.valid_geo_pair(target.partner_latitude,
                                           target.partner_longitude):
                    raise ValueError('Odoo geocoder returned no GPS')
            return ['partner_latitude', 'partner_longitude'], []
        except Exception:
            _logger.warning('CRM-006: Odoo fallback GPS failed for %s %s',
                            role, target.id, exc_info=True)
            return [], ['Geolocation']

    def _sgt_crm006_mirror(self, target, profile, logo):
        """Mirror profile fields. Only callers targeting a Company may pass a logo."""
        current = {key: target[key] for key in push.mirror_keys(profile, logo)}
        return push.mirror_vals(current, profile, logo)

    def _sgt_crm006_write_partner(self, partner, vals):
        """Write all values; if Odoo refuses (e.g. VAT format) retry one by one so
        one bad value does not block the others.  Returns (changed, failed)."""
        if not vals:
            return [], []
        try:
            # Odoo's res.partner.write() can mutate vals in-place (notably
            # partner_latitude/longitude reset to zero after address changes).
            # Never report those side-effects as successfully geocoded fields.
            with self.env.cr.savepoint():
                partner.write(dict(vals))
            return self._sgt_crm006_confirm_fields(partner, vals)
        except Exception:
            _logger.info('CRM-006: bulk write refused for partner %s, retrying per field', partner.id)
        changed, failed = [], []
        for key, value in vals.items():
            try:
                with self.env.cr.savepoint():
                    partner.write({key: value})
                confirmed, unconfirmed = self._sgt_crm006_confirm_fields(partner, {key: value})
                changed += confirmed
                failed += unconfirmed
            except Exception:
                _logger.warning('CRM-006: field %s refused for partner %s', key, partner.id, exc_info=True)
                failed.append(key)
        return changed, failed

    def _sgt_crm006_confirm_fields(self, partner, requested):
        """Report persisted fields, not merely keys passed to write().

        Html can be sanitized and images recompressed by Odoo, so for those
        payloads verify presence rather than raw byte equality. Verify M2O
        links strictly, notably parent_id (Company).
        """
        confirmed, failed = [], []
        for key, value in requested.items():
            try:
                actual = partner[key]
                if key in _RELATIONAL + ('parent_id',):
                    persisted = actual.id == value
                elif key in push.HTML_TARGETS:
                    persisted = push.html_has_content(actual) if value else not push.html_has_content(actual)
                elif key == push.LOGO_FIELD:
                    persisted = bool(actual) if value else not bool(actual)
                elif key == push.SYNC_FLAG:
                    persisted = bool(actual) == bool(value)
                elif isinstance(value, str):
                    persisted = isinstance(actual, str) and actual.strip() == value.strip()
                else:
                    persisted = actual == value
                (confirmed if persisted else failed).append(key)
            except Exception:
                _logger.warning('CRM-006: cannot read back field %s on partner %s', key, partner.id, exc_info=True)
                failed.append(key)
        return confirmed, failed

    def _sgt_crm006_find_or_create_company(self, data, wanted, fill_existing=True):
        """Company for the Contact: same Tax ID, else same name, else a NEW one."""
        Partner = self.env['res.partner'].sudo()
        name = push.clean(data.get('partner_name'))
        if not name:
            return Partner.browse()
        company = Partner.browse()
        vat = wanted.get('vat')
        if vat:
            matches = Partner.with_context(active_test=False).search(
                [('is_company', '=', True), ('vat', '=', vat)], limit=2)
            if len(matches) > 1:
                _logger.warning('CRM-006: ambiguous Company VAT for Deal %s; manual review required', self.id)
                return Partner.browse()
            company = matches
        if not company:
            key = push.norm(name)
            exact = [candidate for candidate in Partner.with_context(active_test=False).search(
                [('is_company', '=', True), ('name', 'ilike', push.like_pattern(name))], limit=100)
                if push.norm(candidate.name) == key]
            if len(exact) > 1:
                _logger.warning('CRM-006: ambiguous Company name for Deal %s; manual review required', self.id)
                return Partner.browse()
            if exact:
                candidate = exact[0]
                # Same name with conflicting tax ID is NOT an identity match.
                if vat and candidate.vat and push.norm(candidate.vat) != push.norm(vat):
                    _logger.warning('CRM-006: Company name/VAT conflict for Deal %s', self.id)
                    return Partner.browse()
                company = candidate
        if company and not company.active:
            # Matching an archived record is NOT a license to link an invisible
            # Company or create its duplicate. Request manual review instead.
            _logger.warning('CRM-006: matching Company is archived for Deal %s', self.id)
            return Partner.browse()
        if company:
            # CRITICAL: manual update must REUSE the company, not enter the create
            # branch when fill_existing=False.  Previous Update_004 could produce
            # duplicates despite a successful VAT/name search.
            if fill_existing:
                company_wanted = {key: value for key, value in wanted.items()
                                  if key in push.ADDRESS_FIELDS + ('website', 'vat')}
                current = {key: (company[key].id if key in _RELATIONAL else company[key]) for key in company_wanted}
                self._sgt_crm006_write_partner(company, push.fill_empty(current, company_wanted))
        else:
            vals = push.company_vals(name, wanted)
            try:
                with self.env.cr.savepoint():
                    company = Partner.create(vals)
            except Exception:
                # Do not silently create an identity with no tax ID when VAT
                # validation fails; a later retry could create duplicates.
                _logger.warning('CRM-006: Company create failed for Deal %s; no unsafe retry', self.id, exc_info=True)
                return Partner.browse()
        return company

    def _sgt_crm006_add_tags(self, partner, names):
        """Add the Deal tags to the Contact (create missing Contact tags).  Never
        removes a tag.  Returns the list of tag names that were added."""
        Category = self.env['res.partner.category'].sudo()
        have = {push.norm(name) for name in partner.category_id.mapped('name')}
        added, ids = [], []
        for name in push.unique_names(names):
            if push.norm(name) in have:
                continue
            category = Category.browse()
            for candidate in Category.search([('name', 'ilike', push.like_pattern(name))], limit=20):
                if push.norm(candidate.name) == push.norm(name):
                    category = candidate
                    break
            if not category:
                category = Category.create({'name': name})
            ids.append(category.id)
            added.append(name)
        if ids:
            partner.write({'category_id': [(4, cid) for cid in ids]})
        return added
