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
    'depends': ['base', 'geosis_base', 'geosis_proyectos', 'geosis_presupuesto', 'geosis_website'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'views/res_users_views.xml',
        'views/hotmart_log_views.xml',
    ],
    'installable': True,
    'application': False,
}
