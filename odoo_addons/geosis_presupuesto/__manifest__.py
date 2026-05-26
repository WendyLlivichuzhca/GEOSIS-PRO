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
        'security/geosis_budget_rules.xml',
        'views/geosis_budget_views.xml',
        'wizard/geosis_budget_export_msproject_views.xml',
        'reports/geosis_budget_reports.xml',
        'reports/geosis_budget_templates.xml',
    ],
    'installable': True,
    'application': False,
}
