{
    'name': 'XINYANG | UI-009 Login + Home',
    'version': '19.0.1.11.0',
    'category': 'Customizations',
    'summary': 'Branded Xinyang login with Home landing; English B2B product gallery.',
    'description': """
UI-009 + UI-010 + UI-011
===============
* Login page (/web/login): combined Saigon Trade x Xinyang logo top-left,
  Xinyang logo above the form, Saigon Trade company information at the bottom.
* "Home" app: landing page opened right after successful employee login, visible to every
  internal user. Animated English banner, optional highlight cards, Saigon Trade strip.
* Banners and facts remain editable via Home > Banners / Highlights (Settings group only).
* Products are managed in Home > Products by Home Manager roles assigned under Settings > Users > Home
  (Settings Administrators can always manage). Home Managers also get "+ Add product" and per-card "Edit" buttons.
* Update_013: Home concept layout + 12 product posters, enlarged poster viewer (Esc / arrows), Saigon Trade strip.
* Update_020: the Match Making page is ONE list for column 5 + column 6 (one combined total, filter All / column 5 / column 6),
  same period filter and cohort rule as the Management Dashboard weekly report.
* Update_019: Match Making page of the Dashboard lists every Deal of the period with its CRM information and its
  Evidence images (read with the viewer's own CRM rights, scaled on the server, large viewer with arrow keys).
* Update_018: Dashboard in Home (Dashboard Viewer right): one shared time filter, an overview of the 4 main KPIs
  (GB, Content, Data · prospects, Match Making) and one page per KPI. Data and Match Making are read with the user's own CRM
  rights; GB and Content come from social360 through a read-only service account set in Home > Settings.
* Update_017: content really spans ~94% of the screen under Odoo's Bootstrap, rounded buttons, professional motion
  (hero entrance, scroll reveal, hover feedback), Potential Map / Contacts reading fixed, Heat Map access list in Home > Settings.
* Update_016: wide layout (content uses about 94% of the screen), EN | VI switch on a coloured pill, and
  a Heat Map (XINYANG MAP) view inside Home, visible only to users with the "Heat Map Viewer" right.
* Update_015: sticky product picture with extra pictures + thumbnails, product navigation bar, Home > Settings
  (automatic picture change: off / 10 / 30 / custom seconds), compact Applications section.
* Update_014: EN / VI language switch on Home (English by default), product content shown when a product
  is opened (entered by hand on each product, translatable with the globe icon), hero layout fix.
""",
    'author': 'Saigon Trade',
    'website': 'https://saigontrade.vn',
    'license': 'LGPL-3',
    'depends': ['web', 'website'],
    'data': [
        'security/home_security.xml',
        'security/ir.model.access.csv',
        'views/login_templates.xml',
        'views/home_views.xml',
        'views/home_product_views.xml',
        'data/home_setting.xml',
        'views/home_setting_views.xml',
        'views/website_switch_views.xml',
        'data/home_data.xml',
        'data/home_products.xml',
        'data/website_switch.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sgt_xinyang_welcome/static/src/css/login.css',
        ],
        'web.assets_backend': [
            'sgt_xinyang_welcome/static/src/home/concept.css',
            'sgt_xinyang_welcome/static/src/home/i18n.js',
            'sgt_xinyang_welcome/static/src/home/home.js',
            'sgt_xinyang_welcome/static/src/home/home.xml',
        ],
    },
    'application': True,
    'installable': True,
}
