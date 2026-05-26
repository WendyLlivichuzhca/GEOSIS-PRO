# -*- coding: utf-8 -*-
{
    'name': 'GEOSIS Avalúos',
    'version': '1.0',
    'category': 'Services',
    'summary': 'Gestión técnica y cálculo científico de avalúos comerciales e inmobiliarios en Ecuador',
    'description': """
Módulo de avalúos y valuaciones inmobiliarias para GEOSIS-PRO.
Permite realizar inspecciones en campo integradas con la app móvil Flutter, 
calcular depreciación física mediante el método de Ross-Heidecke,
y emitir reportes formales de avalúos.
    """,
    'author': 'Antigravity / GEOSIS-PRO',
    'depends': ['geosis_base', 'geosis_apu', 'geosis_mobile'],
    'data': [
        'security/ir.model.access.csv',
        'views/geosis_avaluo_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
