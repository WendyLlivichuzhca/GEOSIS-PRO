{
    'name': 'GEOSIS-PRO Importacion Excel',
    'summary': 'Importa proyectos, presupuestos y APUs desde Excel',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'author': 'GEOSIS-PRO',
    'website': 'https://geosis-pro.local',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'uom',
        'geosis_base',
        'geosis_recursos',
        'geosis_apu',
        'geosis_presupuesto',
        'geosis_proyectos',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/geosis_import_excel_views.xml',
    ],
    'installable': True,
    'application': False,
}
