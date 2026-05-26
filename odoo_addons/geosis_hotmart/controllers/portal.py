# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from odoo.addons.geosis_website.controllers.portal import GeosisCustomerPortal


class GeosisCustomerPortalHotmart(GeosisCustomerPortal):

    def _count_active_residents_for_subscriber(self, subscriber):
        commercial_partner_id = subscriber.partner_id.commercial_partner_id.id
        resident_group = request.env.ref('geosis_base.group_geosis_portal_resident')
        return request.env['res.users'].sudo().search_count([
            ('partner_id.commercial_partner_id', '=', commercial_partner_id),
            ('active', '=', True),
            ('id', '!=', subscriber.id),
            ('groups_id', 'in', [resident_group.id]),
        ])

    @http.route(['/my/gantt'], type='http', auth="user", website=True)
    def portal_my_gantt(self, project_id=None, **kw):
        subscriber = request.env.user._get_subscriber_user()
        if subscriber.has_group('base.group_portal') and not subscriber.has_premium_features:
            error_message = (
                "La visualizacion de diagrama de Gantt es una caracteristica Premium de GEOSIS-PRO. "
                "Por favor, actualiza tu suscripcion al Plan Constructor o Enterprise para acceder."
            )
            return request.redirect(f'/my/projects?error_message={error_message}')
        return super().portal_my_gantt(project_id=project_id, **kw)

    @http.route(['/my/team/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_create(self, name=None, email=None, is_active=True, **kw):
        subscriber = request.env.user._get_subscriber_user()
        requested_role = kw.get('role')

        if subscriber.has_group('base.group_portal') and requested_role == 'resident':
            max_allowed = subscriber.max_residents
            resident_count = self._count_active_residents_for_subscriber(subscriber)

            if resident_count >= max_allowed:
                error_message = (
                    f"Has alcanzado el limite de residentes activos de tu plan ({max_allowed}). "
                    f"Por favor, actualiza tu suscripcion en Hotmart para agregar mas."
                )
                return request.redirect(f'/my/team?error_message={error_message}')

        return super().portal_my_team_create(name=name, email=email, is_active=is_active, **kw)

    @http.route(['/my/team/toggle-active/<int:user_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_toggle_active(self, user_id, **kw):
        user_to_toggle = request.env['res.users'].sudo().browse(user_id)
        if not user_to_toggle.exists():
            return request.redirect('/my/team?error_message=Colaborador no encontrado.')

        if not user_to_toggle.active and user_to_toggle.has_group('geosis_base.group_geosis_portal_resident'):
            subscriber = request.env.user._get_subscriber_user()
            if subscriber.has_group('base.group_portal'):
                max_allowed = subscriber.max_residents
                resident_count = self._count_active_residents_for_subscriber(subscriber)

                if resident_count >= max_allowed:
                    error_message = (
                        f"No se puede activar al residente. Tu plan actual permite un maximo de "
                        f"{max_allowed} residente(s) activo(s). Por favor, actualiza tu plan en Hotmart."
                    )
                    return request.redirect(f'/my/team?error_message={error_message}')

        return super().portal_my_team_toggle_active(user_id, **kw)
