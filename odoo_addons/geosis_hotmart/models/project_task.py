# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError

class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.depends('planned_date_start', 'planned_date_end', 'depend_on_ids', 'project_id.task_ids')
    def _compute_is_critical(self):
        super()._compute_is_critical()
        for task in self:
            # Intentamos encontrar al suscriptor basado en el partner del proyecto
            subscriber = False
            if task.project_id and task.project_id.partner_id:
                subscriber = self.env['res.users'].sudo().with_context(active_test=True).search([
                    ('partner_id', '=', task.project_id.partner_id.commercial_partner_id.id)
                ], limit=1)
            
            # Si no se encontró por partner_id, probamos por el usuario actual o el creador del registro
            if not subscriber:
                user = self.env.user
                if user.has_group('base.group_portal'):
                    subscriber = user._get_subscriber_user()
                else:
                    creator = task.create_uid
                    if creator and creator.has_group('base.group_portal'):
                        subscriber = creator._get_subscriber_user()

            if subscriber and subscriber.has_group('base.group_portal') and not subscriber.has_premium_features:
                task.is_critical = False
                task.slack_time = 0

    def action_calculate_critical_path(self):
        # Determinar si el proyecto está asociado a un suscriptor portal
        subscriber = False
        if self.project_id and self.project_id.partner_id:
            subscriber = self.env['res.users'].sudo().with_context(active_test=True).search([
                ('partner_id', '=', self.project_id.partner_id.commercial_partner_id.id)
            ], limit=1)
        
        if not subscriber:
            user = self.env.user
            if user.has_group('base.group_portal'):
                subscriber = user._get_subscriber_user()
            else:
                subscriber = self.env.user

        if subscriber and subscriber.has_group('base.group_portal') and not subscriber.has_premium_features:
            raise UserError(
                "La funcionalidad de Ruta Crítica (CPM) solo está disponible en el Plan Constructor y Enterprise. "
                "Por favor, actualiza tu plan en Hotmart para habilitar esta opción."
            )
        return super().action_calculate_critical_path()
