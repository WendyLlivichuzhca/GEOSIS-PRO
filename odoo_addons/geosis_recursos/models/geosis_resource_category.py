# -*- coding: utf-8 -*-
from odoo import models, fields

class GeosisResourceCategory(models.Model):
    _name = 'geosis.resource.category'
    _description = 'Categoría de Recurso'
    _order = 'sequence, name'

    name = fields.Char(string="Nombre de Categoría", required=True)
    code = fields.Char(string="Código / Inicial", required=True, help="Ej: M para Materiales, EQ para Equipos")
    sequence = fields.Integer(string="Secuencia", default=10)
    active = fields.Boolean(default=True)
