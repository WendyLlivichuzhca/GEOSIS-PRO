from odoo import api, fields, models

class GeosisProject(models.Model):
    _name = 'geosis.project'
    _description = 'Proyecto GEOSIS'
    _order = 'start_date desc, code desc, id desc'
    _rec_name = 'name'

    code = fields.Char(string='Codigo', required=True, index=True)
    name = fields.Char(string='Nombre del Proyecto', required=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        help="Socio de Odoo vinculado a este proyecto"
    )
    location = fields.Char(string='Ubicacion')
    start_date = fields.Date(
        string='Fecha Inicio',
        required=True,
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
    description = fields.Text(string='Descripcion')
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

    budget_ids = fields.One2many(
        'geosis.budget',
        'project_id',
        string='Presupuestos',
    )

    budget_count = fields.Integer(
        string='Nro. Presupuestos',
        compute='_compute_budget_metrics',
    )
    total_budget_amount = fields.Monetary(
        string='Monto Total Presupuestos',
        compute='_compute_budget_metrics',
        currency_field='currency_id',
    )

    @api.depends('budget_ids.total_amount')
    def _compute_budget_metrics(self):
        for project in self:
            project.budget_count = len(project.budget_ids)
            project.total_budget_amount = sum(project.budget_ids.mapped('total_amount'))

    @api.model
    def _get_next_project_code(self):
        last_project = self.search([], limit=1, order='code desc')
        if not last_project:
            return 'PROJ-001'
        try:
            last_code = last_project.code
            if '-' in last_code:
                prefix, num = last_code.rsplit('-', 1)
                return f"{prefix}-{int(num) + 1:03d}"
            return f"{last_code}-001"
        except Exception:
            return 'PROJ-001'
