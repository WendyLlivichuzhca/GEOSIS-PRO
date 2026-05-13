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
    cpc_code = fields.Char(string='Código CPC', help="Código del Clasificador Central de Productos")
    vae_percent = fields.Float(
        string='VAE %', 
        digits=(5, 2), 
        default=0.0,
        help="Porcentaje de Valor Agregado Ecuatoriano (0-100)"
    )
    inec_index_id = fields.Many2one(
        'geosis.inec.index',
        string='Indice INEC',
        help="Indice para la formula polinomica"
    )
    description = fields.Text(string='Observaciones')
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('geosis_resource_code_unique', 'unique(code)', 'El codigo del recurso debe ser unico.'),
    ]


class GeosisInecIndex(models.Model):
    _name = 'geosis.inec.index'
    _description = 'Indice INEC GEOSIS'
    _order = 'code'

    code = fields.Char(string='Codigo', required=True)
    name = fields.Char(string='Nombre del Indice', required=True)
    active = fields.Boolean(default=True)

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result
