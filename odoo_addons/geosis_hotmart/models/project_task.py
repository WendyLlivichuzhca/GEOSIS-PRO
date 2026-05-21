# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError

class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.depends('planned_date_start', 'planned_date_end', 'depend_on_ids', 'project_id.task_ids')
    def _compute_is_critical(self):
        super()._compute_is_critical()
        for task in self:
            creator = task.create_uid or self.env.user
            subscriber = creator._get_subscriber_user()
            if not subscriber.has_premium_features:
                task.is_critical = False
                task.slack_time = 0

    def action_calculate_critical_path(self):
        # Determinar si el usuario actual es del plan profesional (o el suscriptor correspondiente)
        subscriber = self.env.user._get_subscriber_user()
        if not subscriber.has_premium_features:
            raise UserError(
                "La funcionalidad de Ruta Crítica (CPM) solo está disponible en el Plan Constructor y Enterprise. "
                "Por favor, actualiza tu plan en Hotmart para habilitar esta opción."
            )
        return super().action_calculate_critical_path()
