# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'
    budget_line_id = fields.Many2one(
        'geosis.budget.line',
        string='Linea de Presupuesto',
        ondelete='cascade',
        index=True,
        help='Vincula la tarea del cronograma con la linea del presupuesto que la origino.',
    )

    is_critical = fields.Boolean(
        string='Es Crítica',
        compute='_compute_is_critical',
        store=True,
        help="Indica si esta tarea está en la ruta crítica del proyecto."
    )
    
    slack_time = fields.Integer(
        string='Holgura (Días)',
        compute='_compute_is_critical',
        store=True,
        help="Días de retraso permitidos antes de afectar el final del proyecto."
    )

    @api.depends('planned_date_start', 'planned_date_end', 'depend_on_ids', 'project_id.task_ids')
    def _compute_is_critical(self):
        """
        Calcula la ruta crítica. Una tarea es crítica si su retraso 
        afecta la fecha final del proyecto (Holgura = 0).
        """
        for task in self:
            # 1. Por defecto no es crítica
            task.is_critical = False
            task.slack_time = 0
            
            if not task.project_id or not task.planned_date_end:
                continue

            # 2. Buscar si hay tareas que dependan de esta
            successors = self.search([
                ('project_id', '=', task.project_id.id),
                ('depend_on_ids', 'in', task.id)
            ])
            
            if not successors:
                # Si es la última tarea del proyecto, es crítica por definición
                task.is_critical = True
                task.slack_time = 0
            else:
                # 3. Calcular la holgura: diferencia entre el fin de esta 
                # y el inicio más temprano de la siguiente.
                min_successor_start = min(successors.mapped('planned_date_start'))
                if min_successor_start:
                    slack = (min_successor_start - task.planned_date_end).days - 1
                    task.slack_time = max(0, slack)
                    # Si la holgura es 0 o menos, es crítica
                    task.is_critical = (task.slack_time <= 0)

    def action_calculate_critical_path(self):
        """Disparar el recalculo de todo el proyecto"""
        self._compute_is_critical()
        return True
