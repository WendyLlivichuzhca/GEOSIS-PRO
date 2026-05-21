# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError

class GeosisBudget(models.Model):
    _inherit = 'geosis.budget'

    def action_calculate_polynomial(self):
        # Determinar si el usuario actual es del plan profesional o el suscriptor
        subscriber = self.env.user._get_subscriber_user()
        if not subscriber.has_premium_features:
            raise UserError(
                "La funcionalidad de Fórmula Polinómica solo está disponible en el Plan Constructor y Enterprise. "
                "Por favor, actualiza tu plan en Hotmart para habilitar esta opción."
            )
        return super().action_calculate_polynomial()
