"""Management KPIs inside Home (Update_018): GB, Content, Data · KH tiềm năng, Match Making.

One page (``/sgt_home/kpi``) with a shared time filter, an overview of the four KPIs and one detail page per KPI. Only users in
"Home > Dashboard Viewer" (Home Managers inherit it) and Settings Administrators can open it.

Data and Match Making are read with the USER'S OWN environment (record rules apply, nothing is written, no sudo).
GB and Content live on social360 and are read with the read-only service account set in Home > Settings; the account is read
by ``sgt.home.setting._kpi_sgt_config`` and never reaches the browser. Each KPI fails on its own: one that cannot be verified
shows its reason while the others still show.
"""
import logging
import os
from urllib.parse import urlsplit

from odoo import http
from odoo.http import request

from ..heatmap.adapter import OdooEnvGateway, OdooError
from ..kpi import evidence as ev_mod
from ..kpi import period as period_mod
from ..kpi import sgt as sgt_mod
from ..kpi import xinyang as xy_mod

_logger = logging.getLogger(__name__)
try:
    from psycopg2 import OperationalError as _DbRetry
except ImportError:  # pragma: no cover
    _DbRetry = ()

DASHBOARD_GROUP = 'sgt_xinyang_welcome.group_home_dashboard'
ADMIN_GROUP = 'base.group_system'
PAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kpi', 'kpi_page.html')
NO_STORE = ('Cache-Control', 'private, no-store')
KPIS = ('gb', 'content', 'data', 'mm', 'approved_mm', 'mm_all')
# Odoo 19 shows the Chatter tracking values only to Settings Administrators. The stage history is therefore read with an
# elevated, read-only gateway limited to exactly these calls, and only for Deals the user's own gateway already returned.
HISTORY_READS = {
    'mail.message': ('search_read',),
    'mail.tracking.value': ('search_read',),
    'ir.model.fields': ('search_read',),
    'crm.lead': ('read_group',),      # names of the funnels in use (no Deal, no count is shown)
}


def _module_version():
    try:
        return request.env['ir.module.module'].sudo().search([('name', '=', 'sgt_xinyang_welcome')], limit=1).latest_version or '0'
    except Exception:  # pragma: no cover - cache-busting label only
        return '0'


def _failed(kpi, reason, **extra):
    return {'kpi': kpi, 'available': False, 'reason': reason, **extra}


class SgtKpi(http.Controller):

    # ---- access ---------------------------------------------------------------------------------
    @staticmethod
    def _state():
        user = request.env.user
        if user._is_public():
            return 'public'
        if user._is_internal() and (user.has_group(DASHBOARD_GROUP) or user.has_group(ADMIN_GROUP)):
            return 'ok'
        return 'denied'

    @staticmethod
    def _json(payload, status=200):
        import json
        return request.make_response(json.dumps(payload, ensure_ascii=False, default=str), status=status,
                                     headers=[('Content-Type', 'application/json; charset=utf-8'), NO_STORE])

    def _guard(self):
        state = self._state()
        if state == 'public':
            return self._json({'detail': 'Phiên đăng nhập Odoo đã hết hạn. Hãy đăng nhập lại.'}, 401)
        if state == 'denied':
            return self._json({'detail': 'Tài khoản này chưa được cấp quyền Dashboard.'}, 403)
        return None

    # ---- the four readers (each one fails alone) ----------------------------------------------------
    @staticmethod
    def _sgt_client():
        cfg = request.env['sgt.home.setting']._kpi_sgt_config()
        client = sgt_mod.SgtClient(cfg.get('url'), cfg.get('db'), cfg.get('login'), cfg.get('secret'))
        return client if client.configured() else None

    def _one(self, kpi, per, force, page, page_size, detail=False, column='all'):
        try:
            if kpi in ('gb', 'content'):
                client = self._sgt_client()
                if client is None:
                    return _failed(kpi, 'Chưa kết nối social360. Quản trị viên nhập URL / database / tài khoản dịch vụ / API key '
                                        'tại Home > Settings (mục "KPI Dashboard · social360 connection").', not_connected=True,
                                   source='sgt', **per.as_dict())
                return (sgt_mod.fetch_gb if kpi == 'gb' else sgt_mod.fetch_content_kpi)(client, per, force)
            gateway = OdooEnvGateway(request.env)
            history = gateway.elevated(HISTORY_READS)
            session = gateway.session()
            if kpi == 'data':
                return xy_mod.prospects(gateway, history, session, per, page, page_size, force)
            host = (urlsplit(request.httprequest.host_url).hostname or None) if detail else None
            if kpi == 'mm_all':
                return xy_mod.mm_all_report(gateway, history, session, per, page, page_size, force, column=column,
                                            detail=detail, base_host=host)
            return xy_mod.stage_report(gateway, history, session, 'mm' if kpi == 'mm' else 'approved', per, page, page_size, force,
                                       detail=detail, base_host=host)
        except (sgt_mod.GbError, xy_mod.KpiError, OdooError) as exc:
            return _failed(kpi, str(exc), source='sgt' if kpi in ('gb', 'content') else 'xinyang', **per.as_dict())
        except _DbRetry:
            raise
        except Exception:  # noqa: BLE001 - a bug must show on its own card, not break the others
            _logger.exception('KPI %s: unexpected error', kpi)
            return _failed(kpi, 'Máy chủ không đọc được chỉ số này (lỗi nội bộ). Hãy báo quản trị viên kèm giờ xảy ra lỗi để xem nhật ký.',
                           **per.as_dict())

    # ---- page -----------------------------------------------------------------------------------
    @http.route('/sgt_home/kpi', type='http', auth='public', methods=['GET'], readonly=True)
    def page(self, **kw):
        state = self._state()
        if state == 'public':
            return request.redirect('/web/login?redirect=/sgt_home/kpi', code=302, local=True)
        if state == 'denied':
            return request.make_response(
                '<!doctype html><meta charset="utf-8"><body style="font:15px system-ui;padding:32px;color:#0c2340">'
                'Tài khoản này chưa được cấp quyền Dashboard. Hãy nhờ quản trị viên tích nhóm <b>Home &gt; Dashboard Viewer</b>.</body>',
                headers=[('Content-Type', 'text/html; charset=utf-8'), NO_STORE], status=403)
        with open(PAGE_FILE, encoding='utf-8') as handle:
            html = handle.read().replace('__VERSION__', _module_version())
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'), NO_STORE, ('X-Frame-Options', 'SAMEORIGIN')])

    # ---- data -----------------------------------------------------------------------------------
    @http.route('/sgt_home/kpi/data', type='http', auth='public', methods=['GET'], readonly=True)
    def data(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        try:
            per = period_mod.resolve(kw.get('period'), kw.get('date'))
            page = int(kw.get('page') or 1)
            page_size = int(kw.get('page_size') or 25)
        except period_mod.PeriodError as exc:
            return self._json({'detail': str(exc)}, 422)
        except (TypeError, ValueError):
            return self._json({'detail': 'Phân trang không hợp lệ.'}, 422)
        if not (1 <= page <= 100000 and 1 <= page_size <= 100):
            return self._json({'detail': 'Phân trang không hợp lệ.'}, 422)
        force = str(kw.get('force', '')).lower() in ('1', 'true', 'yes')
        kpi = (kw.get('kpi') or 'overview').strip().lower()
        if kpi == 'overview':
            # The overview needs only the numbers (first page of 5 rows is plenty); every KPI answers on its own.
            cards = {name: self._one(name, per, force, 1, 5) for name in KPIS if name != 'mm_all'}
            return self._json({'period': per.as_dict(), 'cards': cards})
        if kpi not in KPIS:
            return self._json({'detail': 'Chỉ số không hợp lệ.'}, 422)
        col = (kw.get('col') or 'all').strip().lower()
        if col not in ('all', 'mm', 'approved'):
            return self._json({'detail': 'Cột không hợp lệ.'}, 422)
        detail = str(kw.get('detail', '')).lower() in ('1', 'true', 'yes') and kpi in ('mm', 'approved_mm', 'mm_all')
        return self._json({'period': per.as_dict(), 'card': self._one(kpi, per, force, page, page_size, detail, col)})

    # ---- Evidence image of a Match Making Deal ---------------------------------------------------------
    @http.route('/sgt_home/kpi/evidence', type='http', auth='public', methods=['GET'], readonly=True)
    def evidence(self, **kw):
        """One scaled Evidence image of a Deal, read with the signed-in user's own rights (never a stored public link)."""
        denied = self._guard()
        if denied:
            return denied
        try:
            lead_id, index = int(kw.get('lead')), int(kw.get('i'))
        except (TypeError, ValueError):
            return self._json({'detail': 'Yêu cầu ảnh không hợp lệ.'}, 422)
        size = kw.get('size') or 'thumb'
        if size not in ev_mod.SIZES:
            return self._json({'detail': 'Kích thước ảnh không hợp lệ.'}, 422)
        try:
            gateway = OdooEnvGateway(request.env)
            original = ev_mod.load_original(gateway, gateway.session(), lead_id, index, urlsplit(request.httprequest.host_url).hostname)
            body, mime = ev_mod.render(original, size)
        except (ev_mod.EvidenceError, OdooError) as exc:
            return self._json({'detail': str(exc)}, 404)
        except _DbRetry:
            raise
        except Exception:  # noqa: BLE001
            _logger.exception('Evidence image %s/%s: unexpected error', lead_id, index)
            return self._json({'detail': 'Máy chủ không đọc được ảnh này.'}, 500)
        return request.make_response(body, headers=[
            ('Content-Type', mime), ('Content-Length', str(len(body))), ('Cache-Control', 'private, max-age=600'),
            ('X-Content-Type-Options', 'nosniff'), ('Content-Security-Policy', "default-src 'none'")])
