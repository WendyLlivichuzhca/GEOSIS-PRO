# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.geosis_website.controllers.portal import GeosisCustomerPortal

class GeosisCustomerPortalHotmart(GeosisCustomerPortal):

    @http.route(['/my/gantt'], type='http', auth="user", website=True)
    def portal_my_gantt(self, project_id=None, **kw):
        subscriber = request.env.user._get_subscriber_user()
        if subscriber.has_group('base.group_portal') and not subscriber.has_premium_features:
            error_message = (
                "La visualización de diagrama de Gantt es una característica Premium de GEOSIS-PRO. "
                "Por favor, actualiza tu suscripción al Plan Constructor o Enterprise para acceder."
            )
            return request.redirect(f'/my/projects?error_message={error_message}')
        return super().portal_my_gantt(project_id=project_id, **kw)

    @http.route(['/my/team/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_create(self, name=None, email=None, is_active=True, **kw):
        subscriber = request.env.user._get_subscriber_user()
        if subscriber.has_group('base.group_portal'):
            max_allowed = subscriber.max_residents
            commercial_partner_id = subscriber.partner_id.commercial_partner_id.id
            
            # Contar colaboradores del equipo (excluyendo al suscriptor principal)
            resident_count = request.env['res.users'].sudo().search_count([
                ('partner_id.commercial_partner_id', '=', commercial_partner_id),
                ('active', '=', True),
                ('id', '!=', subscriber.id)
            ])
            
            if resident_count >= max_allowed:
                error_message = (
                    f"Has alcanzado el límite de colaboradores activos de tu plan ({max_allowed}). "
                    f"Por favor, actualiza tu suscripción en Hotmart para agregar más."
                )
                return request.redirect(f'/my/team?error_message={error_message}')
                
        return super().portal_my_team_create(name=name, email=email, is_active=is_active, **kw)

    @http.route(['/my/team/toggle-active/<int:user_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_toggle_active(self, user_id, **kw):
        user_to_toggle = request.env['res.users'].sudo().browse(user_id)
        if not user_to_toggle.exists():
            return request.redirect('/my/team?error_message=Colaborador no encontrado.')

        # Si se va a activar
        if not user_to_toggle.active:
            subscriber = request.env.user._get_subscriber_user()
            if subscriber.has_group('base.group_portal'):
                max_allowed = subscriber.max_residents
                commercial_partner_id = subscriber.partner_id.commercial_partner_id.id
                
                resident_count = request.env['res.users'].sudo().search_count([
                    ('partner_id.commercial_partner_id', '=', commercial_partner_id),
                    ('active', '=', True),
                    ('id', '!=', subscriber.id)
                ])
                
                if resident_count >= max_allowed:
                    error_message = (
                        f"No se puede activar al colaborador. Tu plan actual permite un máximo de "
                        f"{max_allowed} colaborador(es) activo(s). Por favor, actualiza tu plan en Hotmart."
                    )
                    return request.redirect(f'/my/team?error_message={error_message}')

        return super().portal_my_team_toggle_active(user_id, **kw)
