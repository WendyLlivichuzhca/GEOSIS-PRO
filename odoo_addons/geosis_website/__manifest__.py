{
    'name': 'GEOSIS-PRO Website',
    'summary': 'Dashboard privado y flujo portal para clientes GEOSIS-PRO',
    'version': '17.0.1.0.0',
    'category': 'Website',
    'author': 'GEOSIS-PRO',
    'website': 'https://geosis-pro.local',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'portal',
        'geosis_recursos',
        'geosis_apu',
        'geosis_presupuesto',
        'geosis_proyectos',
        'geosis_import_excel',
    ],
    'data': [
        'views/geosis_portal_templates.xml',
        'views/geosis_report_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'geosis_website/static/src/scss/geosis_portal.scss',
        ],
    },
    'installable': True,
    'application': False,
}
