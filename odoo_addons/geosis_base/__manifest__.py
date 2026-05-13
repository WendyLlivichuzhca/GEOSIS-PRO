# -*- coding: utf-8 -*-
{
    'name': 'GEOSIS-PRO Base',
    'version': '17.0.1.0.0',
    'summary': 'Base funcional de GEOSIS-PRO para Odoo',
    'description': """
GEOSIS-PRO Base
================

Modulo base para arrancar GEOSIS-PRO en Odoo 17.
Incluye grupos de seguridad y el menu raiz del sistema.
""",
    'author': 'GEOSIS-PRO',
    'license': 'LGPL-3',
    'category': 'Construction',
    'depends': ['base'],
    'data': [
        'security/geosis_security.xml',
        'security/ir.model.access.csv',
        'views/geosis_menus.xml',
        'views/geosis_inec_views.xml',
    ],
    'installable': True,
    'application': True,
}
