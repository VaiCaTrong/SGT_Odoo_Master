from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


HOME_ACTION = 'sgt_xinyang_welcome.action_sgt_home'


class SgtRootRedirect(Website):
    """Use the branded login as the entry point and the Xinyang client action after login.

    The Website editor still needs the original homepage inside its iframe. The
    existing Website switch remains available to administrators as in Update_010.
    """

    def _home_action_url(self):
        """Resolve the action at runtime: action IDs differ between databases."""
        action = request.env.ref(HOME_ACTION, raise_if_not_found=False)
        return f'/odoo/action-{action.id}' if action else '/odoo'

    @http.route()
    def index(self, **kw):
        # Do not intercept the website editor's iframe preview of "/".
        destination = (request.httprequest.headers.get('Sec-Fetch-Dest') or 'document').lower()
        if destination in ('iframe', 'frame', 'embed', 'object'):
            return super().index(**kw)
        if request.env['sgt.website.switch'].sudo().website_enabled():
            return super().index(**kw)

        user = request.env.user
        if user._is_public():
            return request.redirect('/web/login', code=302, local=True)
        if user._is_internal():
            return request.redirect(self._home_action_url(), code=302, local=True)
        return request.redirect('/my', code=302, local=True)

    @http.route()
    def web_login(self, *args, **kw):
        # Re-publish the inherited Odoo 19 Website login route on THIS controller
        # so that its calls to self._login_redirect use our Home destination.
        return super().web_login(*args, **kw)

    def _login_redirect(self, uid, redirect=None):
        """Land internal users on Home, while honoring links with explicit redirects.

        website.Website._login_redirect normally sends employees to /odoo. We
        redirect only fresh logins without an explicit destination. Portal users
        retain the standard /my routing.
        """
        if not redirect and request.params.get('login_success'):
            if request.env['res.users'].browse(uid)._is_internal():
                redirect = self._home_action_url()
        return super()._login_redirect(uid, redirect=redirect)
