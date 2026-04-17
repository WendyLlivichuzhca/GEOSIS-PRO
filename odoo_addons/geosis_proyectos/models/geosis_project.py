from odoo import api, fields, models


class GeosisProject(models.Model):
    _name = 'geosis.project'
    _description = 'Proyecto GEOSIS'
    _order = 'start_date desc, code desc, id desc'
    _rec_name = 'name'

    code = fields.Char(string='Codigo', required=True, index=True)
    name = fields.Char(string='Nombre del Proyecto', required=True)
    customer_name = fields.Char(string='Cliente')
    location = fields.Char(string='Ubicacion')
    start_date = fields.Date(
        string='Fecha Inicio',
        default=fields.Date.context_today,
    )
    end_date = fields.Date(string='Fecha Fin')
    state = fields.Selection(
        selection=[
            ('planning', 'Planificacion'),
            ('active', 'Activo'),
            ('completed', 'Terminado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        required=True,
        default='planning',
    )
    description = fields.Text(string='Observaciones')
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
    budget_ids = fields.One2many(
        'geosis.budget',
        'project_id',
        string='Presupuestos',
    )
    budget_count = fields.Integer(
        string='Cantidad de Presupuestos',
        compute='_compute_budget_metrics',
        store=True,
    )
    total_budget_amount = fields.Monetary(
        string='Total Presupuestado',
        compute='_compute_budget_metrics',
        store=True,
        currency_field='currency_id',
    )

    _sql_constraints = [
        (
            'geosis_project_code_company_uniq',
            'unique(code, company_id)',
            'Ya existe un proyecto con ese codigo para esta compania.',
        ),
    ]

    @api.depends('budget_ids.total_amount')
    def _compute_budget_metrics(self):
        for record in self:
            record.budget_count = len(record.budget_ids)
            record.total_budget_amount = sum(record.budget_ids.mapped('total_amount'))


class GeosisBudget(models.Model):
    _inherit = 'geosis.budget'

    project_id = fields.Many2one(
        'geosis.project',
        string='Proyecto',
        ondelete='set null',
        index=True,
    )
