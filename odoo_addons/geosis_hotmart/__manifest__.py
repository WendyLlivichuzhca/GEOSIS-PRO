# -*- coding: utf-8 -*-
{
    'name': 'GEOSIS-PRO Hotmart Integration',
    'version': '17.0.1.0.0',
    'summary': 'Integración con Hotmart para gestión de suscripciones',
    'description': """
GEOSIS-PRO Hotmart Integration
==============================

Permite recibir webhooks de Hotmart para activar y desactivar usuarios de portal automáticamente.
""",
    'author': 'GEOSIS-PRO',
    'license': 'LGPL-3',
    'category': 'Extra Tools',
    'depends': ['base', 'geosis_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/hotmart_log_views.xml',
    ],
    'installable': True,
    'application': False,
}
