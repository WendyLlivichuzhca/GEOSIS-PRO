from odoo import api, fields, models


class GeosisBudget(models.Model):
    _name = 'geosis.budget'
    _description = 'Presupuesto GEOSIS'
    _order = 'budget_date desc, code desc, id desc'
    _rec_name = 'name'

    code = fields.Char(string='Codigo', required=True, index=True)
    name = fields.Char(string='Descripcion', required=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=False,
        help="Socio de Odoo vinculado a este presupuesto"
    )
    offerer_id = fields.Many2one(
        'res.partner',
        string='Oferente',
        help="Responsable de la oferta"
    )
    location = fields.Char(string='Ubicacion')
    budget_date = fields.Date(
        string='Fecha de Oferta',
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
    formula_line_ids = fields.One2many(
        'geosis.budget.formula.line',
        'budget_id',
        string='Lineas de Formula Polinomica',
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
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    indirect_percent = fields.Float(
        string='Indirectos %',
        default=0.0,
        digits=(5, 2),
        help='Porcentaje de costos indirectos sobre el costo directo total',
    )
    iva_percent = fields.Float(
        string='IVA %',
        default=0.0,
        digits=(5, 2),
        help='Porcentaje de IVA aplicado al subtotal de oferta',
    )
    # --- Desglose de totales ---
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
    subtotal_amount = fields.Monetary(
        string='Subtotal Oferta',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    iva_value = fields.Monetary(
        string='Valor IVA',
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
    vae_total = fields.Float(
        string='VAE % Oferta',
        compute='_compute_totals',
        store=True,
        digits=(5, 2),
    )
    vae_percent = fields.Float(
        string='VAE % Oferta',
        compute='_compute_totals',
        store=True,
        digits=(5, 2),
        help="Porcentaje de Valor Agregado Ecuatoriano de toda la oferta"
    )

    _sql_constraints = [
        (
            'geosis_budget_code_company_uniq',
            'unique(code, company_id)',
            'Ya existe un presupuesto con ese codigo para esta compania.',
        ),
    ]

    @api.model
    def _get_next_budget_code(self, company_id=None):
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))

        next_number = self.search_count(domain) + 1
        code = f"BUD-{next_number:04d}"
        while self.search_count(domain + [('code', '=', code)]):
            next_number += 1
            code = f"BUD-{next_number:04d}"
        return code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self._get_next_budget_code(
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    @api.depends('line_ids.subtotal', 'indirect_percent', 'iva_percent')
    def _compute_totals(self):
        for record in self:
            direct = sum(record.line_ids.mapped('subtotal'))
            indirect = direct * (record.indirect_percent / 100.0)
            subtotal = direct + indirect
            iva = subtotal * (record.iva_percent / 100.0)
            record.direct_cost = direct
            record.indirect_value = indirect
            record.subtotal_amount = subtotal
            record.iva_value = iva
            record.total_amount = subtotal + iva

            # Cálculo de VAE Ponderado de la Oferta
            if direct > 0:
                vae_sum = sum(line.subtotal * line.vae_percent for line in record.line_ids)
                record.vae_percent = vae_sum / direct
            else:
                record.vae_percent = 0.0

    def action_export_msproject(self):
        self.ensure_one()
        return {
            'name': 'Exportar a MS Project',
            'type': 'ir.actions.act_window',
            'res_model': 'geosis.budget.export.msproject',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_budget_id': self.id}
        }

    # ---------------------------------------------------------
    # POLYNOMIAL FORMULA LOGIC
    # ---------------------------------------------------------

    def action_calculate_polynomial(self):
        self.ensure_one()
        self.formula_line_ids.unlink()

        # 1. Agrupar costos por índice INEC
        index_data = {} # inec_index_id -> total_cost
        total_calculated_direct_cost = 0.0
        labor_index_id = False

        for line in self.line_ids:
            apu = line.apu_id
            if not apu: continue
            qty = line.quantity

            for detail in apu.line_ids:
                resource_cost = detail.cost * qty
                total_calculated_direct_cost += resource_cost
                
                index = detail.resource_id.inec_index_id
                index_id = index.id if index else 0
                
                # Detectar si es Mano de Obra para asignarle la 'a' luego
                if detail.category_id.code == 'N' and not labor_index_id:
                    labor_index_id = index_id

                index_data[index_id] = index_data.get(index_id, 0.0) + resource_cost

        if total_calculated_direct_cost <= 0:
            raise models.UserError("El presupuesto no tiene costos de recursos para calcular.")

        # 2. Crear las líneas de la fórmula
        # Primero la Mano de Obra (Símbolo 'a')
        labor_amount = index_data.pop(labor_index_id, 0.0)
        if labor_amount > 0 or labor_index_id:
            self._create_formula_line('a', labor_index_id, labor_amount, total_calculated_direct_cost, 0)

        # Luego el resto ordenado por peso
        sorted_indices = sorted(index_data.items(), key=lambda x: x[1], reverse=True)
        symbols = ['b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']
        
        for i, (idx_id, amount) in enumerate(sorted_indices):
            symbol = symbols[i] if i < len(symbols) else 'z'
            self._create_formula_line(symbol, idx_id, amount, total_calculated_direct_cost, (i + 1) * 10)

        return True

    def get_aggregated_resources(self):
        """Retorna un diccionario agrupado por categoria con los totales de cada recurso"""
        self.ensure_one()
        totals = {} # resource_id -> {'qty': x, 'cost': y, 'rec': z}
        
        for line in self.line_ids:
            apu = line.apu_id
            if not apu: continue
            
            for detail in apu.line_ids:
                rid = detail.resource_id.id
                qty = detail.quantity * line.quantity
                cost = detail.cost * line.quantity
                
                if rid not in totals:
                    totals[rid] = {
                        'qty': 0.0,
                        'cost': 0.0,
                        'resource': detail.resource_id,
                        'category_id': detail.category_id.id
                    }
                totals[rid]['qty'] += qty
                totals[rid]['cost'] += cost
        
        # Agrupar por categoria para el reporte
        categories = {}
        for cat in self.env['geosis.resource.category'].search([]):
            categories[cat.id] = {'name': cat.name.upper(), 'lines': []}
        
        for rid, data in totals.items():
            cat_id = data['category_id']
            if cat_id in categories:
                categories[cat_id]['lines'].append(data)
                
        return categories

    def _create_formula_line(self, symbol, idx_id, amount, total_base, sequence):
        index_rec = self.env['geosis.inec.index'].browse(idx_id) if idx_id else False
        name = index_rec.name if index_rec else ("Mano de Obra" if symbol == 'a' else "Otros Insumos")
        
        coefficient = amount / total_base
        
        self.env['geosis.budget.formula.line'].create({
            'budget_id': self.id,
            'sequence': sequence,
            'symbol': symbol,
            'name': name,
            'coefficient': round(coefficient, 3),
            'inec_index_id': idx_id if idx_id else False,
        })


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
            # Evitar error con NewId (IDs temporales en la interfaz)
            if not isinstance(record.id, int):
                record.total_amount = 0.0
                continue
            
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
    date_start = fields.Date(string='Fecha Inicio')
    date_end = fields.Date(string='Fecha Fin')
    duration = fields.Integer(string='Duración (Días)', compute='_compute_duration', store=True)
    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
    )
    vae_percent = fields.Float(
        string='VAE %',
        related='apu_id.vae_percent',
        readonly=True,
        store=True,
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

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for line in self:
            if line.date_start and line.date_end:
                delta = line.date_end - line.date_start
                line.duration = delta.days + 1
            else:
                line.duration = 0


class GeosisBudgetFormulaLine(models.Model):
    _name = 'geosis.budget.formula.line'
    _description = 'Línea de Fórmula Polinómica'
    _order = 'sequence, id'

    budget_id = fields.Many2one(
        'geosis.budget',
        string='Presupuesto',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Orden', default=10)
    symbol = fields.Char(string='Símbolo', help="Ej: a, b, c, d...")
    name = fields.Char(string='Descripción', required=True, help="Ej: Mano de Obra, Acero...")
    coefficient = fields.Float(string='Coeficiente', digits=(5, 3), required=True, default=0.0)
    inec_index_id = fields.Many2one(
        'geosis.inec.index',
        string='Índice INEC',
        help="Índice de precios para el reajuste"
    )
