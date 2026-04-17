# -*- coding: utf-8 -*-
{
    'name': 'GEOSIS-PRO Recursos',
    'version': '17.0.1.0.0',
    'summary': 'Catalogo de recursos para APUs y presupuestos',
    'description': """
GEOSIS-PRO Recursos
===================

Administra recursos de mano de obra, equipos, materiales y transporte.
""",
    'author': 'GEOSIS-PRO',
    'license': 'LGPL-3',
    'category': 'Construction',
    'depends': ['base', 'uom', 'geosis_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/geosis_resource_views.xml',
    ],
    'installable': True,
    'application': False,
}
