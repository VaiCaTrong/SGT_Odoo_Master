from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from lxml import html as lxml_html


class CrmLead(models.Model):
    """CRM-005 Update_010 + Update_016 + Update_020 + Update_023 + Update_032: the legacy profile fields on crm.lead (geo fields added separately in Update_047).

    Each field below exists because the 2026-10-11 Xinyang production Scan
    (191 crm.lead fields) has NO field able to hold that information. Every
    other piece of the Yellow Pages style profile re-uses existing fields:

        logo              -> x_image (char, written by the extension) or x_yp_logo_upload (uploaded by hand)
        hotline / Zalo    -> x_phone
        introduction      -> description (Notes tab)
        Yellow Pages link -> referred
        products          -> x_product_details
        business type     -> x_type_contact
        industries        -> x_fb_industry
        main market       -> x_country
        address           -> street / street2 / city
    """
    _inherit = 'crm.lead'

    x_yp_tax_code = fields.Char(
        string='Tax Code', copy=False,
        help='Company tax code. Added by CRM-005: crm.lead has no tax-code field '
             '(res.partner.vat exists only on the Contact, not on the Deal).',
    )
    x_yp_founded_year = fields.Integer(
        string='Founded Year', copy=False,
        help='Year the company was founded. Added by CRM-005: no crm.lead field '
             'holds it (x_createdate is the HubSpot deal creation date, not the '
             'company founding date).',
    )
    x_yp_employee_range = fields.Char(
        string='Employee Size', copy=False,
        help='Company size / number of employees as published. Added by CRM-005: '
             'crm.lead has no staff-size field.',
    )
    x_yp_gallery_html = fields.Html(
        string='Image Gallery', copy=False,
        help='Several company images (pasted or imported, inline base64 or '
             'image links) shown side by side. Added by CRM-005: every existing '
             'image field of crm.lead holds one image only, and the only Html '
             'field (description / Notes) holds the company introduction.',
    )
    x_yp_intro_en = fields.Html(
        string='Company Introduction (English)', copy=False,
        help='English version of the company introduction, pasted by the user. Added by '
             'CRM-005 Update_016: the Notes field (description) holds the Vietnamese '
             'introduction; x_notes / x_addnotes are plain text and carry legacy import data.',
    )
    x_yp_partners_html = fields.Html(
        string='Partners', copy=False,
        help='Logos of the partners / customers of the company (inline base64 or image links), '
             'shown as a grid in the Partners box. Added by CRM-005 Update_020: the Image Gallery '
             'field (x_yp_gallery_html) mixes every picture of the listing and cannot be split '
             'without JavaScript; no other crm.lead field holds several images.',
    )
    x_yp_logo_upload = fields.Binary(
        string='Company Logo (Upload)', copy=False, attachment=True,
        help='Company logo uploaded by hand from the computer. Added by CRM-005 Update_023: '
             'x_image is a Char (image link written by the Chrome extension) and cannot receive '
             'an uploaded file. When this field holds a picture it is shown instead of x_image; '
             'when empty the logo of x_image is shown as before. The extension never writes it.',
    )
    x_yp_evidence_html = fields.Html(
        string='Evidence', copy=False,
        help='Evidence pictures pasted by hand (Ctrl+V: screenshots, pictures copied from Zalo / Facebook...). '
             'Added by CRM-005 Update_032 (approved by the user 2026-10-31 08:50): no crm.lead field holds '
             'several pasted pictures (the gallery / partners fields are written by the Chrome extension and '
             'read-only).  The extension never writes it.  CRM-002 (when installed) counts a Deal without a '
             'picture here as missing data (bell) and frames the box in red in 5.Match Making / 6.Approved.',
    )

    @staticmethod
    def _crm005_remove_gallery_node(root, image):
        """Remove one picture tile from the parsed gallery (shared by single and bulk delete)."""
        parent = image.getparent()
        # Figures represent full image tiles (picture + caption). Remove the
        # tile only when it contains this one image, not unrelated pictures.
        figures = image.xpath('ancestor::figure')
        figure = figures[0] if figures else None
        if figure is not None and len(figure.xpath('.//img')) == 1:
            figure.getparent().remove(figure)
        else:
            parent.remove(image)
            # Remove empty image-only wrappers, but preserve text/captions.
            while parent is not None and parent is not root:
                if parent.tag not in ('p', 'div', 'span', 'a'):
                    break
                if (parent.text or '').strip() or len(parent) or (parent.tail or '').strip():
                    break
                ancestor = parent.getparent()
                if ancestor is None:
                    break
                ancestor.remove(parent)
                parent = ancestor

    # Update_066: pick several pictures and delete them in ONE write. Same safety checks as the
    # single delete (write access on the Deal, gallery count and a fingerprint per picture), and
    # nothing is written unless every check passes.  Update_067: Administrators only.
    GALLERY_BULK_DELETE_MAX = 500

    def action_crm005_delete_gallery_images(self, indexes, source_prefixes, expected_count):
        self.ensure_one()
        self.check_access('write')
        # Update_067: deleting several pictures at once is for Administrators (group "Settings") only.
        if not self.env.is_system():
            raise AccessError(_('Only an Administrator can delete several images at once.'))
        if not isinstance(indexes, (list, tuple)) or not isinstance(source_prefixes, (list, tuple)):
            raise ValidationError(_('Invalid image selection.'))
        if not indexes or len(indexes) != len(source_prefixes) or len(indexes) > self.GALLERY_BULK_DELETE_MAX:
            raise ValidationError(_('Invalid image selection.'))
        if any(not isinstance(i, int) or isinstance(i, bool) or i < 0 for i in indexes) or len(set(indexes)) != len(indexes):
            raise ValidationError(_('Invalid image index.'))
        if any(not isinstance(p, str) or len(p) > 128 for p in source_prefixes):
            raise ValidationError(_('Invalid image reference.'))
        if not isinstance(expected_count, int) or isinstance(expected_count, bool):
            raise ValidationError(_('Invalid image count.'))
        raw = self.x_yp_gallery_html or ''
        try:
            root = lxml_html.fragment_fromstring(raw, create_parent='div')
        except (ValueError, TypeError) as exc:
            raise UserError(_('The gallery HTML cannot be parsed.')) from exc
        images = root.xpath('.//img')
        if expected_count != len(images) or max(indexes) >= len(images):
            raise UserError(_('The gallery changed. Refresh this Deal before deleting.'))
        chosen = []
        for index, prefix in zip(indexes, source_prefixes):
            if (images[index].get('src') or '')[:128] != prefix:
                raise UserError(_('The gallery changed. Refresh this Deal before deleting.'))
            chosen.append(images[index])
        for image in chosen:
            self._crm005_remove_gallery_node(root, image)
        remaining = ''.join(lxml_html.tostring(child, encoding='unicode', method='html')
                            for child in root)
        self.write({'x_yp_gallery_html': remaining})
        return len(chosen)

    def action_crm005_delete_gallery_image(self, index, source_prefix, expected_count):
        """Remove one image, preserving the rest of the imported HTML gallery.

        The browser's Developer Mode only reveals the control; actual permission
        is enforced using Odoo's regular record ACLs/rules on the server.
        """
        self.ensure_one()
        self.check_access('write')
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise ValidationError(_('Invalid image index.'))
        if not isinstance(expected_count, int) or isinstance(expected_count, bool):
            raise ValidationError(_('Invalid image count.'))
        if not isinstance(source_prefix, str) or len(source_prefix) > 128:
            raise ValidationError(_('Invalid image reference.'))
        raw = self.x_yp_gallery_html or ''
        try:
            root = lxml_html.fragment_fromstring(raw, create_parent='div')
        except (ValueError, TypeError) as exc:
            raise UserError(_('The gallery HTML cannot be parsed.')) from exc
        images = root.xpath('.//img')
        if expected_count != len(images) or index >= len(images):
            raise UserError(_('The gallery changed. Refresh this Deal before deleting.'))
        image = images[index]
        if (image.get('src') or '')[:128] != source_prefix:
            raise UserError(_('The gallery changed. Refresh this Deal before deleting.'))
        self._crm005_remove_gallery_node(root, image)
        remaining = ''.join(lxml_html.tostring(child, encoding='unicode', method='html')
                            for child in root)
        self.write({'x_yp_gallery_html': remaining})
        return True

    # Update_060: the Kanban Documents shortcut is available only for a Deal
    # with an existing, ACTIVE folder visible to the current user. No new field,
    # schema change or server-side privilege escalation is introduced.
    @api.model
    def crm005_kanban_documents_available(self, lead_ids):
        if not isinstance(lead_ids, (list, tuple)) or len(lead_ids) > 100:
            raise ValidationError(_('Invalid Kanban Deal batch.'))
        try:
            ids = list(dict.fromkeys(int(i) for i in lead_ids))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError(_('Invalid Deal ID.')) from exc
        if any(i <= 0 for i in ids):
            raise ValidationError(_('Invalid Deal ID.'))
        if not ids:
            return []
        leads = self.browse(ids).exists()
        leads.check_access('read')
        if len(leads) != len(ids):
            raise ValidationError(_('Some Deals are no longer accessible.'))
        Folder = self.env['argo.document.folder']
        # sudo ONLY for lookup: presence of an inaccessible folder must not be
        # revealed. Return IDs only after the usual Documents ACL + folder levels.
        linked_domain = ([
            '|', ('lead_id', 'in', ids), ('crm_lead_ids', 'in', ids),
        ] if 'crm_lead_ids' in Folder._fields else [('lead_id', 'in', ids)])
        linked = Folder.sudo().with_context(active_test=False).search(linked_domain)
        available = set()
        for f in linked:
            if not f.active or f.trash_date:
                continue
            visible = Folder.browse(f.id)
            if not visible.has_access('read') or not visible._can_level('view'):
                continue
            if f.lead_id.id in ids:
                available.add(f.lead_id.id)
            if 'crm_lead_ids' in Folder._fields:
                available.update(x for x in f.crm_lead_ids.ids if x in ids)
        return sorted(available)

    def action_crm005_kanban_open_folder(self):
        self.ensure_one()
        self.check_access('read')
        info = self.env['argo.document.folder'].explorer_deal_folder_info(self.id)
        folder = info.get('folder') if info else None
        if not folder or not folder.get('id'):
            raise UserError(_('No accessible Documents folder is linked to this Deal.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'argo_documents.explorer',
            'name': _('CRM Information · Documents'),
            'context': {'active_id': folder['id']},
        }
