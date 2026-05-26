# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class HotmartWebhookController(http.Controller):

    @http.route('/api/hotmart/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def hotmart_webhook(self, **kw):
        expected_token = request.env['ir.config_parameter'].sudo().get_param('geosis.hotmart_token')
        received_token = request.httprequest.headers.get('X-Hotmart-HotTok')

        if not expected_token:
            _logger.error("Hotmart Webhook bloqueado: falta configurar 'geosis.hotmart_token'.")
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Webhook no configurado'}),
                status=503,
                headers=[('Content-Type', 'application/json')]
            )

        if received_token != expected_token:
            _logger.warning("Intento de webhook de Hotmart fallido: token de verificacion incorrecto.")
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Unauthorized: token incorrecto'}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        try:
            payload = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception as err:
            return request.make_response(
                json.dumps({'status': 'error', 'message': f'JSON invalido: {str(err)}'}),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )

        event = payload.get('event')
        data = payload.get('data', {})
        buyer = data.get('buyer', {})
        subscriber = data.get('subscriber', {})
        email = buyer.get('email') or subscriber.get('email')
        name = buyer.get('name') or subscriber.get('name')

        purchase = data.get('purchase', {})
        transaction = purchase.get('transaction')
        subscription = data.get('subscription', {})
        sub_id = subscription.get('subscriber', {}).get('code') or transaction

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
            user_model = request.env['res.users'].sudo().with_context(active_test=False)
            user = user_model.search([('login', '=', email)], limit=1)

            params = request.env['ir.config_parameter'].sudo()
            param_product_id = params.get_param('geosis.hotmart_product_id', '')
            offer_professional = params.get_param('geosis.hotmart_offer_professional', '')
            offer_pyme = params.get_param('geosis.hotmart_offer_pyme', '')
            offer_enterprise = params.get_param('geosis.hotmart_offer_enterprise', '')

            plan = 'professional'
            if product_id == param_product_id:
                if offer_code == offer_professional:
                    plan = 'professional'
                elif offer_code == offer_pyme:
                    plan = 'pyme'
                elif offer_code == offer_enterprise:
                    plan = 'enterprise'

            if event == 'PURCHASE_APPROVED':
                portal_group = request.env.ref('base.group_portal')
                customer_admin_group = request.env.ref('geosis_base.group_geosis_portal_customer_admin')
                group_ids = [portal_group.id, customer_admin_group.id]

                if user:
                    user.write({
                        'active': True,
                        'subscription_status': 'active',
                        'subscription_plan': plan,
                        'hotmart_subscription_id': sub_id,
                        'hotmart_purchase_date': fields.Datetime.now(),
                        'groups_id': [(6, 0, group_ids)],
                    })
                    if user.partner_id and not user.partner_id.active:
                        user.partner_id.write({'active': True})
                    _logger.info("Usuario existente activado correctamente por Hotmart: %s con plan %s", email, plan)
                else:
                    partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                    if not partner:
                        partner = request.env['res.partner'].sudo().create({
                            'name': name or email,
                            'email': email,
                        })

                    company_id = request.env.company.id
                    user = user_model.create({
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
                        'groups_id': [(6, 0, group_ids)],
                    })
                    _logger.info("Nuevo usuario portal creado para Hotmart: %s con plan %s", email, plan)

                    try:
                        user.action_reset_password()
                    except Exception as email_err:
                        log_vals['error_message'] = f"Usuario creado pero fallo envio de invitacion por correo: {str(email_err)}"
                        _logger.error("Error al enviar invitacion al usuario %s: %s", email, str(email_err))

            elif event in ('PURCHASE_REFUNDED', 'PURCHASE_CHARGEBACK', 'PURCHASE_EXPIRED', 'PURCHASE_CANCELED', 'SUBSCRIPTION_CANCELLATION'):
                if user:
                    user.write({
                        'active': False,
                        'subscription_status': 'inactive',
                    })
                    _logger.info("Usuario desactivado por Hotmart (evento: %s): %s", event, email)
                else:
                    log_vals['status'] = 'error'
                    log_vals['error_message'] = f"Se recibio evento de desactivacion {event} pero el usuario {email} no existe en Odoo."
                    _logger.warning("Intento de desactivar usuario inexistente %s por evento %s", email, event)
            else:
                _logger.info("Hotmart Webhook: evento '%s' recibido y guardado en logs sin accion directa.", event)

            request.env['geosis.hotmart.log'].sudo().create(log_vals)

            return request.make_response(
                json.dumps({'status': 'success', 'message': 'Webhook procesado correctamente'}),
                status=200,
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as err:
            log_vals.update({
                'status': 'error',
                'error_message': f"Error interno en el servidor Odoo: {str(err)}"
            })
            _logger.error("Error procesando webhook de Hotmart: %s", str(err))
            try:
                request.env['geosis.hotmart.log'].sudo().create(log_vals)
            except Exception as db_err:
                _logger.critical("No se pudo guardar el log de Hotmart en base de datos: %s", str(db_err))

            return request.make_response(
                json.dumps({'status': 'error', 'message': str(err)}),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )
