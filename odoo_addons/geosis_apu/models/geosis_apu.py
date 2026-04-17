from odoo import api, fields, models


RESOURCE_CATEGORY_SELECTION = [
    ('M', 'Equipos y Herramienta'),
    ('N', 'Mano de Obra'),
    ('O', 'Materiales'),
    ('P', 'Transporte'),
]


class GeosisApu(models.Model):
    _name = 'geosis.apu'
    _description = 'Rubro APU'
    _order = 'code, id'
    _rec_name = 'name'

    code = fields.Char(string='Codigo', required=True, index=True)
    name = fields.Char(string='Descripcion', required=True)
    uom_name = fields.Char(string='Unidad de Medida', required=True, default='U')
    description = fields.Text(string='Observaciones')
    indirect_percent = fields.Float(string='Indirectos %', default=0.0)
    line_ids = fields.One2many(
        'geosis.apu.line',
        'apu_id',
        string='Recursos del APU',
        copy=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Moneda',
        store=True,
        readonly=True,
    )
    direct_cost = fields.Monetary(
        string='Costo Directo',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    indirect_value = fields.Monetary(
        string='Valor Indirectos',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_cost = fields.Monetary(
        string='Precio Unitario',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    _sql_constraints = [
        (
            'geosis_apu_code_company_uniq',
            'unique(code, company_id)',
            'Ya existe un rubro APU con ese codigo para esta compania.',
        ),
    ]

    @api.depends('line_ids.cost', 'indirect_percent')
    def _compute_totals(self):
        for record in self:
            direct_cost = sum(record.line_ids.mapped('cost'))
            indirect_value = direct_cost * (record.indirect_percent / 100.0)
            record.direct_cost = direct_cost
            record.indirect_value = indirect_value
            record.total_cost = direct_cost + indirect_value


class GeosisApuLine(models.Model):
    _name = 'geosis.apu.line'
    _description = 'Detalle de Recurso en APU'
    _order = 'sequence, id'

    apu_id = fields.Many2one(
        'geosis.apu',
        string='APU',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Orden', default=10)
    resource_id = fields.Many2one(
        'geosis.resource',
        string='Recurso',
        required=True,
        ondelete='restrict',
    )
    category = fields.Selection(
        RESOURCE_CATEGORY_SELECTION,
        string='Categoria',
    )
    uom_name = fields.Char(string='Unidad')
    quantity = fields.Float(string='Cantidad', default=1.0, digits=(16, 4))
    rate = fields.Monetary(
        string='Tarifa',
        currency_field='currency_id',
        default=0.0,
    )
    performance = fields.Float(string='Rendimiento', default=1.0, digits=(16, 4))
    percentage = fields.Float(string='Porcentaje', digits=(16, 4))
    distance = fields.Float(string='Distancia', digits=(16, 4))
    note = fields.Char(string='Observacion')
    company_id = fields.Many2one(
        'res.company',
        related='apu_id.company_id',
        string='Compania',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='apu_id.currency_id',
        string='Moneda',
        store=True,
        readonly=True,
    )
    cost = fields.Monetary(
        string='Costo',
        compute='_compute_cost',
        store=True,
        currency_field='currency_id',
    )

    @api.onchange('resource_id')
    def _onchange_resource_id(self):
        for line in self:
            resource = line.resource_id
            if not resource:
                continue

            field_names = resource._fields

            if 'price' in field_names:
                line.rate = resource.price or 0.0

            if 'category' in field_names:
                line.category = resource.category

            for candidate in ('uom_name', 'uom_id', 'uom', 'unit', 'unit_name'):
                if candidate not in field_names:
                    continue
                value = resource[candidate]
                if hasattr(value, 'display_name'):
                    line.uom_name = value.display_name
                else:
                    line.uom_name = value or False
                break

    @api.depends('quantity', 'rate', 'performance')
    def _compute_cost(self):
        for line in self:
            if not line.performance or line.performance <= 0:
                line.cost = line.quantity * line.rate
            else:
                line.cost = (line.quantity * line.rate) / line.performance
