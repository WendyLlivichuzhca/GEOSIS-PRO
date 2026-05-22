# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError

class GeosisBudget(models.Model):
    _inherit = 'geosis.budget'

    def action_calculate_polynomial(self):
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
                "La funcionalidad de Fórmula Polinómica solo está disponible en el Plan Constructor y Enterprise. "
                "Por favor, actualiza tu plan en Hotmart para habilitar esta opción."
            )
        return super().action_calculate_polynomial()
