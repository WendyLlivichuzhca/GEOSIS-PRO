# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GeosisEstimation(models.Model):
    _name = 'geosis.estimation'
    _description = 'Planilla de Avance de Obra'
    _order = 'estimation_date desc, code desc, id desc'
    _rec_name = 'display_name'

    code = fields.Char(string='Nro. Planilla', required=True, index=True)
    display_name = fields.Char(string='Nombre', compute='_compute_display_name', store=True)
    project_id = fields.Many2one(
        'geosis.project',
        string='Proyecto',
        required=True,
        ondelete='restrict',
        index=True,
    )
    budget_id = fields.Many2one(
        'geosis.budget',
        string='Presupuesto',
        domain="[('project_id', '=', project_id)]",
        ondelete='restrict',
    )
    estimation_date = fields.Date(
        string='Fecha de Planilla',
        required=True,
        default=fields.Date.context_today,
    )
    period_start = fields.Date(string='Inicio del Periodo')
    period_end = fields.Date(string='Fin del Periodo')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Presentada'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ], string='Estado', required=True, default='draft')
    notes = fields.Text(string='Observaciones')
    line_ids = fields.One2many(
        'geosis.estimation.line',
        'estimation_id',
        string='Detalle de Avance',
        copy=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    # Totales
    total_executed = fields.Monetary(
        string='Total Ejecutado (Planilla)',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_accumulated = fields.Monetary(
        string='Total Acumulado',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'Ya existe una planilla con ese número para esta compania.'),
    ]

    @api.depends('code', 'project_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.project_id.name or ''}"

    @api.depends('line_ids.subtotal_executed', 'line_ids.subtotal_accumulated')
    def _compute_totals(self):
        for rec in self:
            rec.total_executed = sum(rec.line_ids.mapped('subtotal_executed'))
            rec.total_accumulated = sum(rec.line_ids.mapped('subtotal_accumulated'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class GeosisEstimationLine(models.Model):
    _name = 'geosis.estimation.line'
    _description = 'Línea de Planilla de Avance'
    _order = 'sequence, id'

    estimation_id = fields.Many2one(
        'geosis.estimation',
        string='Planilla',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Orden', default=10)
    budget_line_id = fields.Many2one(
        'geosis.budget.line',
        string='Rubro del Presupuesto',
        domain="[('budget_id', '=', parent.budget_id)]",
        ondelete='restrict',
    )
    apu_code = fields.Char(string='Código', related='budget_line_id.apu_code', readonly=True)
    apu_name = fields.Char(string='Descripción', related='budget_line_id.apu_name', readonly=True)
    uom_name = fields.Char(string='Unidad', related='budget_line_id.uom_name', readonly=True)
    unit_price = fields.Monetary(
        string='P. Unitario',
        related='budget_line_id.unit_price',
        readonly=True,
        currency_field='currency_id',
    )
    quantity_budgeted = fields.Float(
        string='Cantidad Cont.',
        related='budget_line_id.quantity',
        readonly=True,
        digits=(16, 4),
    )
    quantity_executed = fields.Float(
        string='Cant. Esta Planilla',
        digits=(16, 4),
        default=0.0,
    )
    quantity_accumulated = fields.Float(
        string='Cant. Acumulada',
        compute='_compute_accumulated',
        store=True,
        digits=(16, 4),
    )
    subtotal_executed = fields.Monetary(
        string='Total Esta Planilla',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
    )
    subtotal_accumulated = fields.Monetary(
        string='Total Acumulado',
        compute='_compute_accumulated',
        store=True,
        currency_field='currency_id',
    )
    percent_executed = fields.Float(
        string='% Avance',
        compute='_compute_accumulated',
        store=True,
        digits=(5, 2),
    )
    note = fields.Char(string='Observación')
    company_id = fields.Many2one(
        'res.company',
        related='estimation_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='estimation_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('quantity_executed', 'unit_price')
    def _compute_subtotals(self):
        for line in self:
            line.subtotal_executed = line.quantity_executed * line.unit_price

    @api.depends('budget_line_id', 'quantity_executed', 'unit_price', 'quantity_budgeted')
    def _compute_accumulated(self):
        for line in self:
            if not line.budget_line_id:
                line.quantity_accumulated = line.quantity_executed
                line.subtotal_accumulated = line.subtotal_executed
                line.percent_executed = 0.0
                continue

            # Sumar todas las planillas APROBADAS anteriores del mismo rubro
            prev_lines = self.search([
                ('budget_line_id', '=', line.budget_line_id.id),
                ('estimation_id.state', '=', 'approved'),
                ('id', '!=', line.id),
            ])
            prev_qty = sum(prev_lines.mapped('quantity_executed'))
            accumulated = prev_qty + line.quantity_executed
            line.quantity_accumulated = accumulated
            line.subtotal_accumulated = accumulated * line.unit_price

            # Porcentaje de avance
            if line.quantity_budgeted > 0:
                line.percent_executed = (accumulated / line.quantity_budgeted) * 100.0
            else:
                line.percent_executed = 0.0
