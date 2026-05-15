# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GeosisInecIndex(models.Model):
    _name = 'geosis.inec.index'
    _description = 'Índice de Precios INEC'
    _order = 'code, name'

    code = fields.Char(string='Código', required=True, index=True)
    name = fields.Char(string='Nombre del Índice', required=True)
    active = fields.Boolean(default=True)
    value_ids = fields.One2many(
        'geosis.inec.index.value',
        'index_id',
        string='Valores Mensuales'
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código del índice debe ser único.'),
    ]


    @api.model
    def _get_next_inec_code(self):
        next_number = self.search_count([]) + 1
        code = f"INEC-{next_number:03d}"
        while self.search_count([('code', '=', code)]):
            next_number += 1
            code = f"INEC-{next_number:03d}"
        return code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self._get_next_inec_code()
        return super().create(vals_list)


class GeosisInecIndexValue(models.Model):
    _name = 'geosis.inec.index.value'
    _description = 'Valor Mensual de Índice INEC'
    _order = 'year desc, month desc'

    index_id = fields.Many2one(
        'geosis.inec.index',
        string='Índice',
        required=True,
        ondelete='cascade'
    )
    month = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string='Mes', required=True)
    year = fields.Integer(string='Año', required=True, default=lambda self: fields.Date.today().year)
    value = fields.Float(string='Valor del Índice', digits=(16, 4), required=True)

    _sql_constraints = [
        ('index_month_year_unique', 'unique(index_id, month, year)', 'Ya existe un valor para este índice en el mes y año seleccionado.'),
    ]
