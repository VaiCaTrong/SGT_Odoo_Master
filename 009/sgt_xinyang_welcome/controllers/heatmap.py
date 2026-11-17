"""XINYANG MAP (Heat Map) inside Home.

Only users in "Home > Heat Map Viewer" (and Home Managers, who inherit it, and Settings Administrators) can open it.
The data builders (``heatmap/``) are the ones of the Management Dashboard; here they read Odoo with the USER'S OWN
environment: record rules and access rights apply, nothing is read with sudo, nothing is written.
"""
import logging
import os

from odoo import http
from odoo.http import request

from ..heatmap.adapter import OdooEnvGateway, OdooError
from ..heatmap.contact_map import ContactMapError, contact_map, contact_map_profile
from ..heatmap.deal_map import lead_logo as read_lead_logo, xinyang_map
from ..heatmap.potential import merge_contacts, xinyang_potential

_logger = logging.getLogger(__name__)
try:    # a database retry must keep reaching Odoo's own retry loop
    from psycopg2 import OperationalError as _DbRetry
except ImportError:  # pragma: no cover
    _DbRetry = ()

HEATMAP_GROUP = 'sgt_xinyang_welcome.group_home_heatmap'
ADMIN_GROUP = 'base.group_system'
PAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'heatmap', 'map_page.html')
NO_STORE = ('Cache-Control', 'private, no-store')


def _module_version():
    try:
        return request.env['ir.module.module'].sudo().search([('name', '=', 'sgt_xinyang_welcome')], limit=1).latest_version or '0'
    except Exception:  # pragma: no cover - only a cache-busting label
        return '0'


class SgtHeatMap(http.Controller):

    # ---- access ---------------------------------------------------------------------------------
    @staticmethod
    def _state():
        """'public' (not signed in) | 'denied' (signed in without the right) | 'ok'."""
        user = request.env.user
        if user._is_public():
            return 'public'
        if user._is_internal() and (user.has_group(HEATMAP_GROUP) or user.has_group(ADMIN_GROUP)):
            return 'ok'
        return 'denied'

    @staticmethod
    def _json(payload, status=200):
        return request.make_json_response(payload, headers=[NO_STORE], status=status)

    def _guard(self):
        """None when allowed, else the JSON answer (401 not signed in / 403 no right)."""
        state = self._state()
        if state == 'public':
            return self._json({'detail': 'Phiên đăng nhập Odoo đã hết hạn. Hãy đăng nhập lại.'}, 401)
        if state == 'denied':
            return self._json({'detail': 'Tài khoản này chưa được cấp quyền Heat Map.'}, 403)
        return None

    def _read(self, build):
        gateway = OdooEnvGateway(request.env)
        try:
            payload = build(gateway, gateway.session())
        except ContactMapError as exc:
            return self._json({'detail': str(exc)}, 422)
        except OdooError as exc:
            return self._json({'detail': str(exc)}, 403 if str(exc).startswith('Odoo từ chối') else 502)
        except _DbRetry:
            raise
        except Exception:  # noqa: BLE001 - a bug must show as a readable message in the map, not as an Odoo error page
            _logger.exception('Heat Map: unexpected error while reading %s', request.httprequest.path)
            return self._json({'detail': 'Máy chủ không đọc được dữ liệu bản đồ (lỗi nội bộ). Hãy báo quản trị viên kèm giờ xảy ra lỗi để xem nhật ký.'}, 500)
        if isinstance(payload, dict) and isinstance(payload.get('config'), dict):   # links to the Deal / Contact forms
            payload = {**payload, 'config': {**payload['config'], 'odoo_url': request.httprequest.host_url.rstrip('/')}}
        return self._json(payload)

    @staticmethod
    def _force(kw):
        return str(kw.get('force', '')).lower() in ('1', 'true', 'yes')

    # ---- page -----------------------------------------------------------------------------------
    @http.route('/sgt_home/map', type='http', auth='public', methods=['GET'], readonly=True)
    def page(self, **kw):
        state = self._state()
        if state == 'public':
            return request.redirect('/web/login?redirect=/sgt_home/map', code=302, local=True)
        if state == 'denied':
            return request.make_response(
                '<!doctype html><meta charset="utf-8"><body style="font:15px system-ui;padding:32px;color:#0c2340">'
                'Tài khoản này chưa được cấp quyền Heat Map. Hãy nhờ quản trị viên tích nhóm <b>Home &gt; Heat Map Viewer</b>.</body>',
                headers=[('Content-Type', 'text/html; charset=utf-8'), NO_STORE], status=403)
        with open(PAGE_FILE, encoding='utf-8') as handle:
            html = handle.read().replace('__VERSION__', _module_version())
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'), NO_STORE, ('X-Frame-Options', 'SAMEORIGIN')])

    # ---- data (same JSON the Dashboard map page reads) ------------------------------------------
    @http.route('/sgt_home/map/data', type='http', auth='public', methods=['GET'], readonly=True)
    def data(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        force = self._force(kw)

        def build(gateway, session):
            payload = xinyang_map(gateway, session, force=force)
            try:    # plus the Match Making / Approved Contacts; when they cannot be read the Deals still show
                return merge_contacts(payload, contact_map(gateway, session, force=force))
            except Exception as extra:  # noqa: BLE001
                return {**payload, 'status': {**payload.get('status', {}), 'contact_error': str(extra)[:200]}}
        return self._read(build)

    @http.route('/sgt_home/map/potential', type='http', auth='public', methods=['GET'], readonly=True)
    def potential(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        force = self._force(kw)
        return self._read(lambda gateway, session: xinyang_potential(gateway, session, force=force))

    @http.route('/sgt_home/map/lead-logo/<int:lead_id>', type='http', auth='public', methods=['GET'], readonly=True)
    def lead_logo(self, lead_id, **kw):
        denied = self._guard()
        if denied:
            return denied
        return self._read(lambda gateway, session: read_lead_logo(gateway, session, lead_id))

    @http.route('/sgt_home/map/profile/<int:contact_id>', type='http', auth='public', methods=['GET'], readonly=True)
    def profile(self, contact_id, **kw):
        denied = self._guard()
        if denied:
            return denied
        return self._read(lambda gateway, session: contact_map_profile(gateway, session, contact_id))
