{
    'name': 'GEOSIS-PRO Presupuestos',
    'summary': 'Presupuestos con rubros APU para GEOSIS-PRO',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'author': 'GEOSIS-PRO',
    'website': 'https://geosis-pro.local',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'geosis_base',
        'geosis_apu',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/geosis_budget_views.xml',
    ],
    'installable': True,
    'application': False,
}
