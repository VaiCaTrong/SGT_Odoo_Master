{
    'name': 'SGT CRM-007 | Contact Company Profile',
    'summary': 'Contact (res.partner) shows the Yellow Pages company profile of the CRM Deal (read-only; '
               'filled by the CRM-006 button "Cập nhật Contact")',
    'version': '19.0.1.2.0',
    'category': 'Contacts',
    'author': 'SGT',
    'license': 'LGPL-3',
    'depends': ['contacts'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sgt_contact_company_profile/static/src/css/contact_company_profile.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
