# -*- coding: utf-8 -*-
from odoo import models, fields

class GeosisHotmartLog(models.Model):
    _name = 'geosis.hotmart.log'
    _description = 'Registro de Webhooks de Hotmart'
    _order = 'create_date desc'

    event = fields.Char(string='Evento', required=True)
    buyer_email = fields.Char(string='Email del Comprador')
    buyer_name = fields.Char(string='Nombre del Comprador')
    transaction = fields.Char(string='Transacción / ID de Suscripción')
    payload = fields.Text(string='JSON Recibido')
    status = fields.Selection([
        ('success', 'Éxito'),
        ('error', 'Error')
    ], string='Estado', default='success', required=True)
    error_message = fields.Text(string='Mensaje de Error')
