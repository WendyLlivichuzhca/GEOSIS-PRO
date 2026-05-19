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
    cpc_code = fields.Char(string='Código CPC', help="Código del Clasificador Central de Productos para este rubro")
    indirect_percent = fields.Float(string='Indirectos %', default=0.0)
    line_ids = fields.One2many(
        'geosis.apu.line',
        'apu_id',
        string='Recursos del APU',
        copy=True,
    )
    active = fields.Boolean(default=True)
    location = fields.Char(string='Ubicación', index=True)
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
    vae_percent = fields.Float(
        string='VAE % Total',
        compute='_compute_totals',
        store=True,
        digits=(5, 2),
        help="Valor Agregado Ecuatoriano total del rubro"
    )

    _sql_constraints = [
        (
            'geosis_apu_code_company_location_uniq',
            'unique(code, company_id, location)',
            'Ya existe un rubro APU con ese codigo para esta ubicacion.',
        ),
    ]

    @api.model
    def _get_next_apu_code(self, company_id=None, location=None):
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))
        if location is not None:
            domain.append(('location', '=', location))

        next_number = self.search_count(domain) + 1
        code = f"APU-{next_number:04d}"
        while self.search_count(domain + [('code', '=', code)]):
            next_number += 1
            code = f"APU-{next_number:04d}"
        return code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self._get_next_apu_code(
                    company_id=vals.get('company_id') or self.env.company.id,
                    location=vals.get('location'),
                )
        return super().create(vals_list)


    @api.depends('line_ids.cost', 'indirect_percent')
    def _compute_totals(self):
        for record in self:
            direct_cost = sum(record.line_ids.mapped('cost'))
            indirect_value = direct_cost * (record.indirect_percent / 100.0)
            record.direct_cost = direct_cost
            record.indirect_value = indirect_value
            record.total_cost = direct_cost + indirect_value
            
            # Cálculo de VAE Ponderado
            if direct_cost > 0:
                vae_sum = sum(line.cost * line.vae_percent for line in record.line_ids)
                record.vae_percent = vae_sum / direct_cost
            else:
                record.vae_percent = 0.0

    def action_generate_with_ia(self):
        """
        Motor de sugerencias inteligentes para APUs.
        Analiza el nombre del rubro y sugiere recursos comunes.
        """
        self.ensure_one()
        
        # Limpiar sugerencias anteriores para evitar duplicados
        self.line_ids.unlink()
        
        name_lower = self.name.lower()
        suggestions = []

        # Reglas de sugerencia basadas en palabras clave con fallbacks de nombres (Simulación de IA)
        if 'excavacion' in name_lower or 'excavación' in name_lower:
            if 'mano' in name_lower or 'manual' in name_lower:
                suggestions = [
                    ('N', ['Peón', 'Peon', 'Jornalero', 'Obrero', 'Mano de Obra'], 1.0),
                    ('M', ['Herramienta menor', 'Herramientas menores', 'Herramienta', 'Herramientas'], 0.05),
                ]
            else:
                suggestions = [
                    ('M', ['Excavadora', 'Retroexcavadora', 'Cargadora', 'Tractor', 'Equipo pesado'], 0.02),
                    ('N', ['Operador de equipo', 'Operador de retroexcavadora', 'Operador', 'Chofer'], 1.0),
                    ('N', ['Peón', 'Peon', 'Jornalero', 'Obrero'], 1.0),
                    ('M', ['Herramienta menor', 'Herramientas menores', 'Herramienta', 'Herramientas'], 0.05),
                ]
        elif 'hormigon' in name_lower or 'hormigón' in name_lower:
            suggestions = [
                ('O', ['Cemento Portland', 'Cemento', 'Portland'], 7.5),
                ('O', ['Arena', 'Arena fina', 'Arena gruesa'], 0.5),
                ('O', ['Ripio', 'Grava', 'Piedra chispa', 'Piedra'], 0.8),
                ('O', ['Agua'], 0.2),
                ('N', ['Albañil', 'Maestro de obra'], 1.5),
                ('N', ['Peón', 'Peon', 'Jornalero'], 3.0),
                ('M', ['Mezcladora', 'Concretera', 'Mezclador'], 0.05),
                ('M', ['Herramienta menor', 'Herramientas menores', 'Herramienta'], 0.05),
            ]
        elif 'acero' in name_lower or 'hierro' in name_lower:
            suggestions = [
                ('O', ['Acero de refuerzo', 'Acero', 'Varilla'], 1.05),
                ('O', ['Alambre galvanizado', 'Alambre', 'Alambre recocido'], 0.05),
                ('N', ['Fierrero', 'Albañil'], 0.08),
                ('N', ['Ayudante', 'Peón', 'Peon', 'Jornalero'], 0.08),
                ('M', ['Herramienta menor', 'Herramientas menores', 'Herramienta'], 0.05),
            ]

        if not suggestions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'IA Geosis',
                    'message': 'No se encontraron sugerencias automáticas para este rubro. Intente con nombres como "Excavación" o "Hormigón".',
                    'type': 'warning',
                }
            }

        # Insertar los recursos encontrados (buscando en el catálogo)
        resource_obj = self.env['geosis.resource'].sudo()
        for cat, name_list, qty in suggestions:
            resource = resource_obj.browse()
            # Buscar el recurso más parecido en el catálogo usando fallbacks
            for name in name_list:
                resource = resource_obj.search([
                    ('category', '=', cat),
                    ('name', 'ilike', name)
                ], limit=1)
                if resource:
                    break
            
            if resource:
                self.env['geosis.apu.line'].create({
                    'apu_id': self.id,
                    'resource_id': resource.id,
                    'quantity': qty,
                    'performance': 1.0,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


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
    vae_percent = fields.Float(
        string='VAE %',
        digits=(5, 2),
        help="Heredado del recurso"
    )
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('resource_id'):
                resource = self.env['geosis.resource'].sudo().browse(vals['resource_id'])
                if resource.exists():
                    field_names = resource._fields
                    if 'price' in field_names and not vals.get('rate'):
                        vals['rate'] = resource.price or 0.0
                    if 'category' in field_names and not vals.get('category'):
                        vals['category'] = resource.category
                    if 'vae_percent' in field_names and not vals.get('vae_percent'):
                        vals['vae_percent'] = resource.vae_percent
                    if not vals.get('uom_name'):
                        for candidate in ('uom_name', 'uom_id', 'uom', 'unit', 'unit_name'):
                            if candidate in field_names:
                                value = resource[candidate]
                                if hasattr(value, 'display_name'):
                                    vals['uom_name'] = value.display_name
                                else:
                                    vals['uom_name'] = value or False
                                break
        return super().create(vals_list)

    def write(self, vals):
        if 'resource_id' in vals:
            resource = self.env['geosis.resource'].sudo().browse(vals['resource_id'])
            if resource.exists():
                field_names = resource._fields
                if 'price' in field_names and 'rate' not in vals:
                    vals['rate'] = resource.price or 0.0
                if 'category' in field_names and 'category' not in vals:
                    vals['category'] = resource.category
                if 'vae_percent' in field_names and 'vae_percent' not in vals:
                    vals['vae_percent'] = resource.vae_percent
                if 'uom_name' not in vals:
                    for candidate in ('uom_name', 'uom_id', 'uom', 'unit', 'unit_name'):
                        if candidate in field_names:
                            value = resource[candidate]
                            if hasattr(value, 'display_name'):
                                vals['uom_name'] = value.display_name
                            else:
                                vals['uom_name'] = value or False
                            break
        return super().write(vals)

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

            if 'vae_percent' in field_names:
                line.vae_percent = resource.vae_percent

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
            line.cost = line.quantity * line.rate * line.performance
