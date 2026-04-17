{
    'name': 'GEOSIS-PRO Proyectos',
    'summary': 'Proyectos vinculados a presupuestos para GEOSIS-PRO',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'author': 'GEOSIS-PRO',
    'website': 'https://geosis-pro.local',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'geosis_base',
        'geosis_presupuesto',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/geosis_project_views.xml',
    ],
    'installable': True,
    'application': False,
}
