# -*- coding: utf-8 -*-
from odoo import fields, models


class GeosisResource(models.Model):
    _name = 'geosis.resource'
    _description = 'Recurso GEOSIS'
    _order = 'category, code, name'

    code = fields.Char(string='Codigo', index=True)
    name = fields.Char(string='Descripcion', required=True)
    category = fields.Selection(
        selection=[
            ('M', 'Equipos'),
            ('N', 'Mano de Obra'),
            ('O', 'Materiales'),
            ('P', 'Transporte'),
        ],
        string='Categoria',
        required=True,
        default='O',
        index=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        required=True,
        ondelete='restrict',
    )
    price = fields.Float(string='Precio', digits=(16, 4), default=0.0)
    description = fields.Text(string='Observaciones')
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('geosis_resource_code_unique', 'unique(code)', 'El codigo del recurso debe ser unico.'),
    ]
