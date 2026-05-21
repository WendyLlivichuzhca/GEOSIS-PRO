# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    subscription_status = fields.Selection([
        ('active', 'Activa'),
        ('inactive', 'Inactiva')
    ], string='Estado de Suscripción', default='inactive', help="Indica si el usuario tiene su suscripción activa en Hotmart.")
    
    subscription_plan = fields.Selection([
        ('professional', 'Profesional'),
        ('pyme', 'Constructor (Pyme)'),
        ('enterprise', 'Enterprise')
    ], string='Plan de Suscripción', default='professional', help="El plan de suscripción actual del usuario en Hotmart.")

    hotmart_subscription_id = fields.Char(string='ID de Suscripción Hotmart', help="El identificador de suscripción retornado por Hotmart.")
    hotmart_purchase_date = fields.Datetime(string='Fecha de Compra Hotmart')

    def _get_subscriber_user(self):
        """
        Devuelve el usuario principal dueño de la suscripción.
        Si este usuario es un residente/colaborador, devuelve el usuario padre (comercial).
        """
        self.ensure_one()
        commercial_partner = self.partner_id.commercial_partner_id
        if not commercial_partner:
            return self
        
        # Buscar usuario activo correspondiente al partner comercial
        subscriber_user = self.env['res.users'].sudo().with_context(active_test=True).search([
            ('partner_id', '=', commercial_partner.id)
        ], limit=1)
        
        return subscriber_user or self

    @property
    def max_active_projects(self):
        if not self.has_group('base.group_portal'):
            return 999999
        plan = self.subscription_plan or 'professional'
        if plan == 'professional':
            return 2
        elif plan == 'pyme':
            return 10
        return 999999

    @property
    def max_residents(self):
        if not self.has_group('base.group_portal'):
            return 999999
        plan = self.subscription_plan or 'professional'
        if plan == 'professional':
            return 1
        elif plan == 'pyme':
            return 5
        return 999999

    @property
    def has_premium_features(self):
        if not self.has_group('base.group_portal'):
            return True
        plan = self.subscription_plan or 'professional'
        return plan in ('pyme', 'enterprise')
