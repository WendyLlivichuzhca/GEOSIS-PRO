# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    subscription_status = fields.Selection([
        ('active', 'Activa'),
        ('inactive', 'Inactiva')
    ], string='Estado de Suscripción', default='inactive', help="Indica si el usuario tiene su suscripción activa en Hotmart.")
    
    hotmart_subscription_id = fields.Char(string='ID de Suscripción Hotmart', help="El identificador de suscripción retornado por Hotmart.")
    hotmart_purchase_date = fields.Datetime(string='Fecha de Compra Hotmart')
