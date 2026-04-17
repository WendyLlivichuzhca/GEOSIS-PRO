from odoo import api, fields, models


class GeosisBudget(models.Model):
    _name = 'geosis.budget'
    _description = 'Presupuesto GEOSIS'
    _order = 'budget_date desc, code desc, id desc'
    _rec_name = 'name'

    code = fields.Char(string='Codigo', required=True, index=True)
    name = fields.Char(string='Descripcion', required=True)
    customer_name = fields.Char(string='Cliente')
    location = fields.Char(string='Ubicacion')
    budget_date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('approved', 'Aprobado'),
            ('archived', 'Archivado'),
        ],
        string='Estado',
        required=True,
        default='draft',
    )
    description = fields.Text(string='Observaciones')
    line_ids = fields.One2many(
        'geosis.budget.line',
        'budget_id',
        string='Rubros APU',
        copy=True,
    )
    chapter_ids = fields.One2many(
        'geosis.budget.chapter',
        'budget_id',
        string='Capitulos',
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
    subtotal_amount = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_amount = fields.Monetary(
        string='Total General',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    _sql_constraints = [
        (
            'geosis_budget_code_company_uniq',
            'unique(code, company_id)',
            'Ya existe un presupuesto con ese codigo para esta compania.',
        ),
    ]

    @api.depends('line_ids.subtotal')
    def _compute_totals(self):
        for record in self:
            subtotal = sum(record.line_ids.mapped('subtotal'))
            record.subtotal_amount = subtotal
            record.total_amount = subtotal


class GeosisBudgetChapter(models.Model):
    _name = 'geosis.budget.chapter'
    _description = 'Capitulo de Presupuesto GEOSIS'
    _order = 'sequence, id'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'

    budget_id = fields.Many2one(
        'geosis.budget',
        string='Presupuesto',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Orden', default=10)
    code = fields.Char(string='Codigo')
    name = fields.Char(string='Nombre', required=True)
    parent_id = fields.Many2one(
        'geosis.budget.chapter',
        string='Capitulo Padre',
        domain="[('budget_id', '=', budget_id)]",
        ondelete='cascade',
    )
    child_ids = fields.One2many(
        'geosis.budget.chapter',
        'parent_id',
        string='Subcapitulos',
    )
    parent_path = fields.Char(index=True)
    level = fields.Integer(
        string='Nivel',
        compute='_compute_level',
        store=True,
    )
    complete_name = fields.Char(
        string='Capitulo',
        compute='_compute_complete_name',
        store=True,
    )
    line_ids = fields.One2many(
        'geosis.budget.line',
        'chapter_id',
        string='Lineas',
    )
    total_amount = fields.Monetary(
        string='Total',
        compute='_compute_total_amount',
        currency_field='currency_id',
    )
    company_id = fields.Many2one(
        'res.company',
        related='budget_id.company_id',
        string='Compania',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='budget_id.currency_id',
        string='Moneda',
        store=True,
        readonly=True,
    )

    @api.depends('parent_id.level')
    def _compute_level(self):
        for record in self:
            record.level = (record.parent_id.level + 1) if record.parent_id else 1

    @api.depends('code', 'name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            parts = [part for part in (record.code, record.name) if part]
            label = ' - '.join(parts) if parts else record.name or ''
            if record.parent_id and record.parent_id.complete_name:
                record.complete_name = '%s / %s' % (record.parent_id.complete_name, label)
            else:
                record.complete_name = label

    @api.depends(
        'line_ids.subtotal',
        'child_ids.line_ids.subtotal',
        'child_ids.child_ids.line_ids.subtotal',
    )
    def _compute_total_amount(self):
        for record in self:
            descendants = self.search([('id', 'child_of', record.id)])
            record.total_amount = sum(descendants.mapped('line_ids.subtotal'))


class GeosisBudgetLine(models.Model):
    _name = 'geosis.budget.line'
    _description = 'Linea de Presupuesto GEOSIS'
    _order = 'sequence, id'

    budget_id = fields.Many2one(
        'geosis.budget',
        string='Presupuesto',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Orden', default=10)
    chapter_id = fields.Many2one(
        'geosis.budget.chapter',
        string='Capitulo',
        domain="[('budget_id', '=', budget_id)]",
        ondelete='set null',
    )
    apu_id = fields.Many2one(
        'geosis.apu',
        string='Rubro APU',
        required=True,
        ondelete='restrict',
    )
    apu_code = fields.Char(
        string='Codigo',
        related='apu_id.code',
        readonly=True,
    )
    apu_name = fields.Char(
        string='Descripcion',
        related='apu_id.name',
        readonly=True,
    )
    uom_name = fields.Char(
        string='Unidad',
        related='apu_id.uom_name',
        readonly=True,
    )
    quantity = fields.Float(string='Cantidad', default=1.0, digits=(16, 4))
    unit_price = fields.Monetary(
        string='Precio Unitario',
        currency_field='currency_id',
        default=0.0,
    )
    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
    )
    note = fields.Char(string='Observacion')
    company_id = fields.Many2one(
        'res.company',
        related='budget_id.company_id',
        string='Compania',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='budget_id.currency_id',
        string='Moneda',
        store=True,
        readonly=True,
    )

    @api.onchange('apu_id')
    def _onchange_apu_id(self):
        for line in self:
            apu = line.apu_id
            if not apu:
                continue
            line.unit_price = apu.total_cost or 0.0
            if not line.note and apu.description:
                line.note = apu.description

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
