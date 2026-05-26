# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GeosisAvaluo(models.Model):
    _name = 'geosis.avaluo'
    _description = 'Avalúo Inmobiliario y Catastral'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Código de Avalúo',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )
    title = fields.Char(string='Título / Objeto del Avalúo', required=True)
    owner_name = fields.Char(string='Propietario del Inmueble', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente / Solicitante', required=True)
    inspector_id = fields.Many2one('res.users', string='Perito Valuador', default=lambda self: self.env.user)
    date = fields.Date(string='Fecha del Avalúo', default=fields.Date.context_today, required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('inspected', 'Inspeccionado'),
        ('calculated', 'Calculado'),
        ('approved', 'Aprobado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', required=True, tracking=True)

    location = fields.Char(string='Dirección / Ubicación')
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))

    # --- DATOS DEL TERRENO ---
    land_area = fields.Float(string='Área de Terreno (m²)', digits=(12, 2))
    land_unit_value = fields.Float(string='Valor Unitario de Suelo ($/m²)', digits=(12, 2))
    land_topography_factor = fields.Float(string='Factor Topográfico', default=1.0, help='1.0 plano, < 1.0 inclinado')
    land_shape_factor = fields.Float(string='Factor Forma', default=1.0, help='1.0 regular, < 1.0 irregular')
    land_value = fields.Float(
        string='Valor Comercial de Terreno ($)',
        compute='_compute_land_value',
        store=True,
        digits=(12, 2)
    )

    # --- DATOS DE LA CONSTRUCCIÓN ---
    apu_id = fields.Many2one('geosis.apu', string='Rubro APU de Referencia', help='Vincular un rubro APU para obtener el costo de reposición a nuevo automáticamente')
    construction_area = fields.Float(string='Área de Construcción (m²)', digits=(12, 2))
    construction_replacement_cost = fields.Float(string='Costo de Reposición a Nuevo ($/m²)', digits=(12, 2))
    construction_age = fields.Integer(string='Antigüedad de la Edificación (Años)', default=0)
    construction_life_expectancy = fields.Integer(string='Vida Útil Estimada (Años)', default=50)
    construction_state_coef = fields.Selection([
        ('1.00', 'Perfecto / Nuevo (1.00)'),
        ('0.95', 'Bueno / Conservado (0.95)'),
        ('0.75', 'Regular / Reparaciones Sencillas (0.75)'),
        ('0.40', 'Malo / Reparaciones Estructurales (0.40)'),
        ('0.00', 'Ruinoso / Inhabitable (0.00)')
    ], string='Estado de Conservación', default='1.00', required=True)
    
    construction_depreciation_percent = fields.Float(
        string='Porcentaje de Depreciación (%)',
        compute='_compute_construction_value',
        store=True,
        digits=(5, 2)
    )
    construction_value = fields.Float(
        string='Valor Comercial de Construcción ($)',
        compute='_compute_construction_value',
        store=True,
        digits=(12, 2)
    )

    # --- VALOR TOTAL ---
    total_value = fields.Float(
        string='Avalúo Comercial Total ($)',
        compute='_compute_total_value',
        store=True,
        digits=(12, 2)
    )

    # --- DETALLES ---
    photo_ids = fields.One2many('geosis.avaluo.photo', 'avaluo_id', string='Fotografías de Inspección')
    comparable_ids = fields.One2many('geosis.avaluo.comparable', 'avaluo_id', string='Comparables de Mercado')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    @api.onchange('apu_id')
    def _onchange_apu_id(self):
        if self.apu_id:
            # Si hay un APU de referencia, usar su costo unitario final como CRN
            self.construction_replacement_cost = self.apu_id.total_cost or 0.0

    @api.depends('land_area', 'land_unit_value', 'land_topography_factor', 'land_shape_factor')
    def _compute_land_value(self):
        for rec in self:
            rec.land_value = (
                rec.land_area * 
                rec.land_unit_value * 
                rec.land_topography_factor * 
                rec.land_shape_factor
            )

    @api.depends(
        'construction_area', 'construction_replacement_cost', 
        'construction_age', 'construction_life_expectancy', 'construction_state_coef'
    )
    def _compute_construction_value(self):
        for rec in self:
            age = max(0, rec.construction_age)
            life = max(1, rec.construction_life_expectancy)
            c_factor = float(rec.construction_state_coef or 1.00)
            
            # Limitar relación edad/vida útil a máximo 1.0 (obsoleto total)
            age_ratio = min(1.0, float(age) / float(life))
            
            # Fórmula de Depreciación Física de Ross-Heidecke
            # Depreciacion% = 100 * (1 - C * (1 - e/t))
            deprec_factor = 1.0 - (c_factor * (1.0 - age_ratio))
            deprec_percent = deprec_factor * 100.0
            
            rec.construction_depreciation_percent = deprec_percent
            
            # Valor Comercial de la Construcción
            rec.construction_value = (
                rec.construction_area * 
                rec.construction_replacement_cost * 
                (1.0 - deprec_factor)
            )

    @api.depends('land_value', 'construction_value')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = rec.land_value + rec.construction_value

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('geosis.avaluo') or _('Nuevo')
        return super(GeosisAvaluo, self).create(vals_list)

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_inspected(self):
        self.write({'state': 'inspected'})

    def action_calculate(self):
        # Fuerza re-cálculos
        self._compute_land_value()
        self._compute_construction_value()
        self._compute_total_value()
        self.write({'state': 'calculated'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class GeosisAvaluoPhoto(models.Model):
    _name = 'geosis.avaluo.photo'
    _description = 'Fotografía de Inspección de Avalúo'

    avaluo_id = fields.Many2one('geosis.avaluo', string='Avalúo', ondelete='cascade', required=True)
    image = fields.Binary(string='Imagen', required=True)
    name = fields.Char(string='Nombre / Descripción', default='Fotografía de Campo')
    latitude = fields.Float(string='Latitud de Captura', digits=(10, 7))
    longitude = fields.Float(string='Longitud de Captura', digits=(10, 7))


class GeosisAvaluoComparable(models.Model):
    _name = 'geosis.avaluo.comparable'
    _description = 'Inmueble Comparable del Mercado'

    avaluo_id = fields.Many2one('geosis.avaluo', string='Avalúo', ondelete='cascade', required=True)
    name = fields.Char(string='Descripción / Comparable', required=True, placeholder='Ej: Departamento en Condominio X')
    area = fields.Float(string='Área Construida (m²)', required=True)
    price = fields.Float(string='Precio de Oferta ($)', required=True)
    price_m2 = fields.Float(string='Precio Unitario ($/m²)', compute='_compute_price_m2', store=True)
    distance_km = fields.Float(string='Distancia al Inmueble (Km)', digits=(5, 2))

    @api.depends('area', 'price')
    def _compute_price_m2(self):
        for rec in self:
            rec.price_m2 = rec.price / rec.area if rec.area > 0 else 0.0
