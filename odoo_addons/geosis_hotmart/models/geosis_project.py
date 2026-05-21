# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError

class GeosisProject(models.Model):
    _inherit = 'geosis.project'

    @api.constrains('state', 'active')
    def _check_saas_project_limit(self):
        for project in self:
            # Solo validar si el proyecto se activa (estado 'active' y active=True)
            if project.state == 'active' and project.active:
                creator = project.create_uid or self.env.user
                subscriber = creator._get_subscriber_user()
                
                # Solo aplicar límites a usuarios que pertenecen al grupo Portal
                if subscriber.has_group('base.group_portal'):
                    max_allowed = subscriber.max_active_projects
                    
                    # Encontrar todos los usuarios que pertenecen al mismo suscriptor comercial
                    commercial_partner_id = subscriber.partner_id.commercial_partner_id.id
                    subscriber_users = self.env['res.users'].sudo().with_context(active_test=False).search([
                        ('partner_id.commercial_partner_id', '=', commercial_partner_id)
                    ])
                    
                    # Contar otros proyectos activos creados por este equipo
                    active_count = self.env['geosis.project'].sudo().search_count([
                        ('state', '=', 'active'),
                        ('active', '=', True),
                        ('create_uid', 'in', subscriber_users.ids),
                        ('id', '!=', project.id)
                    ])
                    
                    if (active_count + 1) > max_allowed:
                        raise ValidationError(
                            f"Límite de proyectos alcanzado. Tu plan actual permite un máximo de "
                            f"{max_allowed} proyecto(s) activo(s). Por favor, actualiza tu plan para "
                            f"poder activar más proyectos."
                        )
