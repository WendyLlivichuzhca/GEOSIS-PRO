# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GeosisResource(models.Model):
    _name = 'geosis.resource'
    _description = 'Recurso GEOSIS'
    _order = 'category_id, code, name'

    code = fields.Char(string='Codigo', index=True)
    name = fields.Char(string='Descripcion', required=True)
    category_id = fields.Many2one(
        'geosis.resource.category',
        string='Categoria',
        required=True,
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
    location = fields.Char(string='Ubicación', index=True)
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('geosis_resource_code_location_unique', 'unique(code, location)', 'Ya existe un recurso con este codigo para esta ubicacion.'),
    ]

    @api.model
    def _get_next_resource_code(self, category_id=None, location=None):
        domain = [('location', '=', location or False)]
        prefix = 'RE'
        
        if category_id:
            category = self.env['geosis.resource.category'].browse(category_id)
            if category.exists():
                prefix = (category.code or category.name[:2] or 'RE').upper()
                domain.append(('category_id', '=', category_id))
        
        next_number = self.search_count(domain) + 1
        code = f"{prefix}-{next_number:04d}"
        while self.search_count([('location', '=', location or False), ('code', '=', code)]):
            next_number += 1
            code = f"{prefix}-{next_number:04d}"
        return code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self._get_next_resource_code(
                    category_id=vals.get('category_id'),
                    location=vals.get('location'),
                )
        return super().create(vals_list)

    def write(self, vals):
        res = super(GeosisResource, self).write(vals)
        if 'price' in vals:
            for record in self:
                # Buscar todas las líneas de APU asociadas a este recurso y actualizar su tarifa
                lines = self.env['geosis.apu.line'].sudo().search([('resource_id', '=', record.id)])
                if lines:
                    lines.write({'rate': vals['price']})
                    # Forzar el recálculo y guardado de los totales de los rubros
                    apus = lines.mapped('apu_id')
                    apus._compute_totals()
        return res



class GeosisInecIndex(models.Model):
    _inherit = 'geosis.inec.index'
    _description = 'Indice INEC GEOSIS'
    _order = 'code'

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result
