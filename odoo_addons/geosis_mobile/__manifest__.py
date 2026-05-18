{
    'name': 'GEOSIS Mobile Backend',
    'version': '1.0',
    'summary': 'Servicios y modelos para la App Móvil de Libro de Obra',
    'category': 'Project',
    'author': 'Antigravity / GEOSIS',
    'depends': ['base', 'geosis_proyectos'],
    'data': [
        'security/ir.model.access.csv',
        'views/geosis_bitacora_views.xml',
        'views/geosis_bitacora_report.xml',
    ],
    'installable': True,
    'application': True,
}
