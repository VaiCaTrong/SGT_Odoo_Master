{
    'name': 'SGT CRM-006 | Push Deal data to Contact',
    'summary': 'After the existing "Create Contact" button (and with the button "Cập nhật Contact"), copy the Deal '
               'data (company, address, website, tags, tax id, salesperson, company profile, logo...) into the '
               'Contact and its Company',
    'version': '19.0.1.8.0',
    'category': 'Sales/CRM',
    'author': 'SGT',
    'license': 'LGPL-3',
    'depends': ['crm', 'crm_sync_contact_odoo2', 'sgt_contact_company_profile', 'sgt_crm_yellowpages_profile'],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
