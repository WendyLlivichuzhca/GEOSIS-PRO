# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError

class GeosisProject(models.Model):
    _inherit = 'geosis.project'

    @api.constrains('state', 'active')
    def _check_saas_project_limit(self):
        for project in self:
            # Validar si el proyecto está activo o en planificación (planning)
            if project.state in ('planning', 'active') and project.active:
                # Intentamos encontrar al suscriptor basado en el partner del proyecto
                subscriber = False
                if project.partner_id:
                    # Buscamos el usuario portal asociado al partner comercial del cliente del proyecto
                    subscriber = self.env['res.users'].sudo().with_context(active_test=True).search([
                        ('partner_id', '=', project.partner_id.commercial_partner_id.id)
                    ], limit=1)
                
                # Si no se encontró por partner_id, probamos por el usuario actual o el creador del registro
                if not subscriber:
                    user = self.env.user
                    if user.has_group('base.group_portal'):
                        subscriber = user._get_subscriber_user()
                    else:
                        creator = project.create_uid
                        if creator and creator.has_group('base.group_portal'):
                            subscriber = creator._get_subscriber_user()

                # Si es un suscriptor que pertenece al grupo Portal, aplicar límites
                if subscriber and subscriber.has_group('base.group_portal'):
                    max_allowed = subscriber.max_active_projects
                    
                    # Contar los proyectos del mismo suscriptor en estado planificación o activo
                    active_count = self.env['geosis.project'].sudo().search_count([
                        ('state', 'in', ('planning', 'active')),
                        ('active', '=', True),
                        ('partner_id', '=', subscriber.partner_id.commercial_partner_id.id),
                        ('id', '!=', project.id)
                    ])
                    
                    if (active_count + 1) > max_allowed:
                        raise ValidationError(
                            f"Límite de proyectos alcanzado. Tu plan actual permite un máximo de "
                            f"{max_allowed} proyecto(s) en planificación o activo(s) simultáneamente. "
                            f"Por favor, marca como Terminado o Cancelado un proyecto existente o actualiza tu plan."
                        )
