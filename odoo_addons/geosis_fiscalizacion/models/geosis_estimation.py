# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class GeosisEstimation(models.Model):
    _name = 'geosis.estimation'
    _description = 'Planilla de Avance de Obra'
    _order = 'date desc, id desc'

    name = fields.Char(string='Numero de Planilla', required=True, copy=False, default='Nueva Planilla')
    budget_id = fields.Many2one(
        'geosis.budget', 
        string='Presupuesto/Contrato', 
        required=True,
        domain="[('state', '=', 'approved')]"
    )
    date = fields.Date(string='Fecha de Corte', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobada'),
        ('invoiced', 'Facturada'),
        ('cancel', 'Cancelada'),
    ], string='Estado', default='draft', required=True)
    
    line_ids = fields.One2many('geosis.estimation.line', 'estimation_id', string='Detalle de Planilla')
    
    total_amount = fields.Monetary(string='Total Planillado', compute='_compute_totals', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', related='budget_id.company_id', readonly=True, store=True)

    @api.depends('line_ids.subtotal')
    def _compute_totals(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('subtotal'))

    @api.onchange('budget_id')
    def _onchange_budget_id(self):
        if not self.budget_id:
            return
        
        # Cargar automáticamente todos los rubros del presupuesto
        lines = []
        for line in self.budget_id.line_ids:
            lines.append((0, 0, {
                'budget_line_id': line.id,
                'uom_id': line.apu_id.uom_name, # Podríamos mejorar esto a Many2one luego
                'unit_price': line.unit_price,
            }))
        self.line_ids = lines

    def action_approve(self):
        for record in self:
            if not record.line_ids:
                raise UserError("No puedes aprobar una planilla sin líneas.")
            record.state = 'approved'


class GeosisEstimationLine(models.Model):
    _name = 'geosis.estimation.line'
    _description = 'Linea de Planilla de Avance'

    estimation_id = fields.Many2one('geosis.estimation', string='Planilla', ondelete='cascade')
    budget_line_id = fields.Many2one('geosis.budget.line', string='Rubro Contractual', required=True)
    
    apu_name = fields.Char(related='budget_line_id.apu_name', string='Descripcion', readonly=True)
    uom_id = fields.Char(string='Unidad', readonly=True)
    
    qty_contract = fields.Float(related='budget_line_id.quantity', string='Cant. Contrato', readonly=True)
    qty_previous = fields.Float(string='Cant. Anterior', compute='_compute_quantities', store=False)
    qty_current = fields.Float(string='Cant. Actual', default=0.0)
    qty_total = fields.Float(string='Cant. Acumulada', compute='_compute_quantities', store=False)
    qty_pending = fields.Float(string='Saldo por Ejecutar', compute='_compute_quantities', store=False)
    
    unit_price = fields.Float(string='Precio Unitario', readonly=True)
    subtotal = fields.Float(string='Subtotal Actual', compute='_compute_subtotal', store=True)

    @api.depends('qty_current', 'budget_line_id', 'estimation_id.date', 'estimation_id.budget_id')
    def _compute_quantities(self):
        for line in self:
            # Buscar planillas anteriores aprobadas del mismo presupuesto
            previous_lines = self.env['geosis.estimation.line'].search([
                ('budget_line_id', '=', line.budget_line_id.id),
                ('estimation_id.budget_id', '=', line.estimation_id.budget_id.id),
                ('estimation_id.state', 'in', ['approved', 'invoiced']),
                ('estimation_id.date', '<', line.estimation_id.date),
                ('id', '!=', line.id)
            ])
            prev_qty = sum(previous_lines.mapped('qty_current'))
            
            line.qty_previous = prev_qty
            line.qty_total = prev_qty + line.qty_current
            line.qty_pending = line.qty_contract - line.qty_total

    @api.depends('qty_current', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty_current * line.unit_price
