# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class HotmartWebhookController(http.Controller):

    @http.route('/api/hotmart/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def hotmart_webhook(self, **kw):
        # 1. Verificar Token de seguridad (HotTok)
        expected_token = request.env['ir.config_parameter'].sudo().get_param('geosis.hotmart_token')
        received_token = request.httprequest.headers.get('X-Hotmart-HotTok')
        
        if expected_token:
            if received_token != expected_token:
                _logger.warning("Intento de webhook de Hotmart fallido: Token de verificación incorrecto.")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Unauthorized: Token incorrecto'}),
                    status=401,
                    headers=[('Content-Type', 'application/json')]
                )
        else:
            _logger.info("Hotmart Webhook: No se ha configurado 'geosis.hotmart_token' en Parámetros del Sistema. Se omite validación.")

        # 2. Leer y parsear el JSON
        try:
            raw_data = request.httprequest.data
            payload = json.loads(raw_data.decode('utf-8'))
        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'error', 'message': f'JSON inválido: {str(e)}'}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )

        event = payload.get('event')
        data = payload.get('data', {})
        buyer = data.get('buyer', {})
        email = buyer.get('email')
        name = buyer.get('name')
        
        purchase = data.get('purchase', {})
        transaction = purchase.get('transaction')
        
        subscription = data.get('subscription', {})
        sub_id = subscription.get('subscriber', {}).get('code') or transaction

        # Obtener datos de producto y oferta
        product_id = str(data.get('product', {}).get('id', ''))
        offer_code = purchase.get('offer', {}).get('code') or ''

        if not email:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Email del comprador no encontrado en el payload'}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )

        log_vals = {
            'event': event or 'UNKNOWN',
            'buyer_email': email,
            'buyer_name': name,
            'transaction': sub_id,
            'payload': json.dumps(payload, indent=2),
            'status': 'success',
        }

        try:
            # Buscar el usuario. Importante usar active_test=False para incluir usuarios inactivos
            user = request.env['res.users'].sudo().with_context(active_test=False).search([('login', '=', email)], limit=1)

            # Determinar el plan según el id de producto y código de oferta
            param_product_id = request.env['ir.config_parameter'].sudo().get_param('geosis.hotmart_product_id', '')
            offer_professional = request.env['ir.config_parameter'].sudo().get_param('geosis.hotmart_offer_professional', '')
            offer_pyme = request.env['ir.config_parameter'].sudo().get_param('geosis.hotmart_offer_pyme', '')
            offer_enterprise = request.env['ir.config_parameter'].sudo().get_param('geosis.hotmart_offer_enterprise', '')

            plan = 'professional'  # Fallback por defecto
            if product_id == param_product_id:
                if offer_code == offer_professional:
                    plan = 'professional'
                elif offer_code == offer_pyme:
                    plan = 'pyme'
                elif offer_code == offer_enterprise:
                    plan = 'enterprise'

            # --- CASO 1: COMPRA APROBADA (Activar o Crear Usuario Portal) ---
            if event == 'PURCHASE_APPROVED':
                if user:
                    user.write({
                        'active': True,
                        'subscription_status': 'active',
                        'subscription_plan': plan,
                        'hotmart_subscription_id': sub_id,
                        'hotmart_purchase_date': fields.Datetime.now()
                    })
                    # Asegurar que el partner relacionado esté activo
                    if user.partner_id and not user.partner_id.active:
                        user.partner_id.write({'active': True})
                    _logger.info(f"Usuario existente activado correctamente por Hotmart: {email} con plan {plan}")
                else:
                    # Crear nuevo partner y asignarlo a grupo Portal
                    partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                    if not partner:
                        partner = request.env['res.partner'].sudo().create({
                            'name': name or email,
                            'email': email,
                        })
                    
                    company_id = request.env.company.id
                    portal_group = request.env.ref('base.group_portal')
                    
                    user = request.env['res.users'].sudo().create({
                        'name': name or email,
                        'login': email,
                        'email': email,
                        'partner_id': partner.id,
                        'active': True,
                        'subscription_status': 'active',
                        'subscription_plan': plan,
                        'hotmart_subscription_id': sub_id,
                        'hotmart_purchase_date': fields.Datetime.now(),
                        'company_id': company_id,
                        'company_ids': [(6, 0, [company_id])],
                        'groups_id': [(6, 0, [portal_group.id])]
                    })
                    _logger.info(f"Nuevo usuario portal creado para Hotmart: {email} con plan {plan}")
                    
                    # Enviar correo de invitación / restablecimiento de contraseña
                    try:
                        user.action_reset_password()
                    except Exception as email_err:
                        log_vals['error_message'] = f"Usuario creado pero falló envío de invitación por correo: {str(email_err)}"
                        _logger.error(f"Error al enviar invitación al usuario {email}: {str(email_err)}")

            # --- CASO 2: COMPRA CANCELADA / EXPIRADA / REEMBOLSADA (Desactivar Usuario) ---
            elif event in ('PURCHASE_REFUNDED', 'PURCHASE_CHARGEBACK', 'PURCHASE_EXPIRED', 'PURCHASE_CANCELED', 'SUBSCRIPTION_CANCELLATION'):
                if user:
                    user.write({
                        'active': False,
                        'subscription_status': 'inactive',
                    })
                    _logger.info(f"Usuario desactivado por Hotmart (Evento: {event}): {email}")
                else:
                    log_vals['status'] = 'error'
                    log_vals['error_message'] = f"Se recibió evento de desactivación {event} pero el usuario {email} no existe en Odoo."
                    _logger.warning(f"Intento de desactivar usuario inexistente {email} por evento {event}")

            else:
                _logger.info(f"Hotmart Webhook: Evento '{event}' recibido y guardado en logs sin acción directa de activación/desactivación.")

            # Guardar el registro de log
            request.env['geosis.hotmart.log'].sudo().create(log_vals)

            return request.make_response(
                json.dumps({'status': 'success', 'message': 'Webhook procesado correctamente'}),
                status=200,
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            log_vals.update({
                'status': 'error',
                'error_message': f"Error interno en el servidor Odoo: {str(e)}"
            })
            _logger.error(f"Error procesando webhook de Hotmart: {str(e)}")
            try:
                request.env['geosis.hotmart.log'].sudo().create(log_vals)
            except Exception as db_err:
                _logger.critical(f"No se pudo guardar el log de Hotmart en base de datos: {str(db_err)}")
                
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )
