# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request


class GeosisMobileAPI(http.Controller):
    def _partner_domain(self):
        commercial_partner = request.env.user.partner_id.commercial_partner_id
        return [('partner_id', 'child_of', commercial_partner.id)]

    def _is_portal_resident(self):
        return request.env.user.has_group('geosis_base.group_geosis_portal_resident')

    def _assigned_task_domain(self):
        Task = request.env['project.task']
        user_id = request.env.user.id
        has_user_ids = 'user_ids' in Task._fields
        has_user_id = 'user_id' in Task._fields
        if has_user_ids and has_user_id:
            return ['|', ('user_ids', 'in', [user_id]), ('user_id', '=', user_id)]
        if has_user_ids:
            return [('user_ids', 'in', [user_id])]
        if has_user_id:
            return [('user_id', '=', user_id)]
        return [('id', '=', 0)]

    def _assigned_budget_line_ids_for_project(self, project):
        budgets = request.env['geosis.budget'].sudo().search([
            ('project_id', '=', project.id),
            ('state', '!=', 'archived'),
        ])
        odoo_projects = budgets.mapped('odoo_project_id').filtered(lambda record: record.exists())
        if not odoo_projects:
            return []
        assigned_tasks = request.env['project.task'].sudo().search(
            [('project_id', 'in', odoo_projects.ids)] + self._assigned_task_domain()
        )
        if 'budget_line_id' not in assigned_tasks._fields:
            return []
        return assigned_tasks.mapped('budget_line_id').ids

    def _resident_has_project_access(self, project):
        if not self._is_portal_resident():
            return True
        return bool(self._assigned_budget_line_ids_for_project(project))

    def _accessible_project(self, project_id):
        Project = request.env['geosis.project'].sudo()
        if not project_id:
            return Project.browse()
        project = Project.search([('id', '=', int(project_id))] + self._partner_domain(), limit=1)
        if project and not self._resident_has_project_access(project):
            return Project.browse()
        return project

    def _budget_line_belongs_to_project(self, line_id, project):
        line = request.env['geosis.budget.line'].sudo().browse(int(line_id))
        if not line.exists() or line.budget_id.project_id.id != project.id:
            return False
        if self._is_portal_resident():
            return line.id in self._assigned_budget_line_ids_for_project(project)
        return True

    @http.route('/web/geosis/projects', type='json', auth='user', methods=['POST'])
    def get_projects(self):
        try:
            projects = request.env['geosis.project'].sudo().search(
                self._partner_domain() + [('state', 'in', ['planning', 'active'])],
                order='name asc',
            )
            if self._is_portal_resident():
                projects = projects.filtered(lambda project: self._resident_has_project_access(project))
            data = []

            for project in projects:
                budget = request.env['geosis.budget'].sudo().search([
                    ('project_id', '=', project.id),
                    ('state', '!=', 'archived'),
                ], limit=1, order='budget_date desc, id desc')

                tasks = []
                if budget:
                    budget_line_domain = [
                        ('budget_id', '=', budget.id),
                        ('date_start', '!=', False),
                        ('date_end', '!=', False),
                    ]
                    if self._is_portal_resident():
                        budget_line_domain.append(('id', 'in', self._assigned_budget_line_ids_for_project(project)))
                    budget_lines = request.env['geosis.budget.line'].sudo().search(
                        budget_line_domain,
                        order='sequence asc, id asc',
                    )

                    for line in budget_lines:
                        last_approved_task = request.env['geosis.bitacora.task'].sudo().search([
                            ('task_id', '=', line.id),
                            ('bitacora_id.project_id', '=', project.id),
                            ('bitacora_id.state', '=', 'approved'),
                        ], order='id desc', limit=1)

                        tasks.append({
                            'id': line.id,
                            'name': line.apu_name or 'Rubro sin nombre',
                            'progress': last_approved_task.progress if last_approved_task else 0.0,
                            'uom': line.uom_name or 'u',
                            'start': str(line.date_start) if line.date_start else '',
                            'end': str(line.date_end) if line.date_end else '',
                        })

                data.append({
                    'id': project.id,
                    'name': project.name,
                    'code': project.code or 'S/N',
                    'location': project.location or 'Sin ubicación',
                    'tasks': tasks,
                })

            return {'status': 'success', 'data': data}
        except Exception as exc:
            return {'status': 'error', 'message': str(exc)}

    @http.route('/web/geosis/submit_report', type='json', auth='user', methods=['POST'])
    def submit_report(self):
        try:
            params = request.get_json_data().get('params', {})
            data = params.get('report')
            if not data:
                return {'status': 'error', 'message': 'No se proporcionaron datos del reporte'}

            project = self._accessible_project(data.get('project_id'))
            if not project:
                return {'status': 'error', 'message': 'No tienes acceso a este proyecto'}

            bitacora_vals = {
                'project_id': project.id,
                'date': data.get('date') or fields.Date.context_today(request.env.user),
                'user_id': request.env.user.id,
                'weather': data.get('weather', 'sunny'),
                'content': data.get('content', ''),
                'personal_notes': data.get('personal_notes', ''),
                'equipment_notes': data.get('equipment_notes', ''),
                'contractor_queries': data.get('contractor_queries', ''),
                'latitude': float(data.get('latitude', 0.0) or 0.0),
                'longitude': float(data.get('longitude', 0.0) or 0.0),
                'state': 'draft',
            }
            if data.get('signature_contractor'):
                bitacora_vals['signature_contractor'] = data.get('signature_contractor')

            bitacora = request.env['geosis.bitacora'].sudo().create(bitacora_vals)

            for task in data.get('tasks', []):
                task_id = task.get('task_id')
                if not task_id or not self._budget_line_belongs_to_project(task_id, project):
                    continue
                request.env['geosis.bitacora.task'].sudo().create({
                    'bitacora_id': bitacora.id,
                    'task_id': int(task_id),
                    'progress': int(task.get('progress', 0) or 0),
                    'done': bool(task.get('done', False)),
                    'notes': task.get('notes', ''),
                })

            for photo in data.get('photos', []):
                if photo.get('base64_image'):
                    request.env['geosis.bitacora.photo'].sudo().create({
                        'bitacora_id': bitacora.id,
                        'image': photo.get('base64_image'),
                        'caption': photo.get('caption', ''),
                    })

            return {
                'status': 'success',
                'bitacora_id': bitacora.id,
                'message': 'Libro de Obra guardado correctamente en Odoo',
            }
        except Exception as exc:
            return {'status': 'error', 'message': str(exc)}

    @http.route('/geosis/mobile/submit_report', type='json', auth='user', methods=['POST'])
    def submit_report_legacy(self, **post):
        return self.submit_report()

    @http.route('/web/geosis/bitacoras', type='json', auth='user', methods=['POST'])
    def get_bitacoras(self):
        try:
            params = request.get_json_data().get('params', {})
            project_id = params.get('project_id')
            project_ids = request.env['geosis.project'].sudo().search(self._partner_domain()).ids

            domain = [('project_id', 'in', project_ids)]
            if project_id:
                project = self._accessible_project(project_id)
                if not project:
                    return {'status': 'error', 'message': 'No tienes acceso a este proyecto'}
                domain = [('project_id', '=', project.id)]
            if self._is_portal_resident():
                domain.append(('user_id', '=', request.env.user.id))

            bitacoras = request.env['geosis.bitacora'].sudo().search(domain, order='date desc, id desc')
            data = []
            for bitacora in bitacoras:
                data.append({
                    'id': bitacora.id,
                    'project_id': bitacora.project_id.id,
                    'project_name': bitacora.project_id.name,
                    'date': str(bitacora.date),
                    'weather': bitacora.weather or 'sunny',
                    'content': bitacora.content or '',
                    'personal_notes': bitacora.personal_notes or '',
                    'equipment_notes': bitacora.equipment_notes or '',
                    'contractor_queries': bitacora.contractor_queries or '',
                    'inspector_instructions': bitacora.inspector_instructions or '',
                    'state': bitacora.state or 'draft',
                    'signature_contractor': bitacora.signature_contractor or '',
                    'signature_inspector': bitacora.signature_inspector or '',
                    'tasks': [{
                        'task_name': task.task_id.apu_name or 'Rubro sin nombre',
                        'progress': task.progress,
                        'notes': task.notes or '',
                    } for task in bitacora.task_ids],
                    'photos': [{
                        'caption': photo.caption or '',
                        'image': photo.image or '',
                    } for photo in bitacora.photo_ids],
                })
            return {'status': 'success', 'data': data}
        except Exception as exc:
            return {'status': 'error', 'message': str(exc)}

    @http.route('/web/geosis/team', type='json', auth='user', methods=['POST'])
    def get_team(self):
        try:
            current_user = request.env.user
            is_resident = current_user.has_group('geosis_base.group_geosis_portal_resident')
            is_supervisor = current_user.has_group('geosis_base.group_geosis_portal_supervisor')
            is_admin = current_user.has_group('geosis_base.group_geosis_admin')
            
            # Chequeo seguro del rol perito
            has_perito_group = request.env.ref('geosis_base.group_geosis_perito', raise_if_not_found=False)
            is_perito = current_user.has_group('geosis_base.group_geosis_perito') if has_perito_group else (not (is_resident or is_supervisor) or is_admin)

            User = request.env['res.users'].sudo()
            
            # Usuarios de la misma compañía
            domain = [('company_ids', 'in', [current_user.company_id.id])]
            users = User.search(domain)
            
            filtered_users = []
            for u in users:
                u_is_admin = u.has_group('geosis_base.group_geosis_admin')
                u_is_supervisor = u.has_group('geosis_base.group_geosis_portal_supervisor')
                u_is_resident = u.has_group('geosis_base.group_geosis_portal_resident')
                u_is_perito = u.has_group('geosis_base.group_geosis_perito') if has_perito_group else (not (u_is_resident or u_is_supervisor) or u_is_admin)
                
                # Reglas de visibilidad
                if is_admin:
                    filtered_users.append(u)
                elif is_perito and u_is_perito:
                    filtered_users.append(u)
                elif is_supervisor and (u_is_resident or u_is_supervisor):
                    filtered_users.append(u)
                elif is_resident and (u_is_supervisor or u_is_resident):
                    filtered_users.append(u)

            data = []
            for u in filtered_users:
                if u.login == 'admin':
                    continue

                role_name = u.partner_id.function or "Dirección de Proyecto"
                if not u.partner_id.function:
                    if u.has_group('geosis_base.group_geosis_admin'):
                        role_name = "Administrador GEOSIS"
                    elif u.has_group('geosis_base.group_geosis_portal_appraiser'):
                        role_name = "Perito Valuador"
                    elif u.has_group('geosis_base.group_geosis_portal_resident'):
                        role_name = "Residente de Obra"
                    elif u.has_group('geosis_base.group_geosis_portal_supervisor'):
                        role_name = "Fiscalizador / Supervisor"

                data.append({
                    'id': u.id,
                    'name': u.name,
                    'role_name': role_name,
                    'email': u.login,
                    'phone': u.partner_id.phone or u.partner_id.mobile or '',
                    'image_128': u.image_128.decode('utf-8') if u.image_128 else False,
                })

            return {'status': 'success', 'data': data}
        except Exception as exc:
            return {'status': 'error', 'message': str(exc)}

    @http.route('/web/geosis/user_profile', type='json', auth='user', methods=['POST'])
    def get_user_profile(self):
        try:
            user = request.env.user
            is_resident = user.has_group('geosis_base.group_geosis_portal_resident')
            is_supervisor = user.has_group('geosis_base.group_geosis_portal_supervisor')
            is_perito_appraiser = user.has_group('geosis_base.group_geosis_portal_appraiser')
            is_admin = user.has_group('geosis_base.group_geosis_admin')
            
            is_direction = not (is_resident or is_supervisor or is_perito_appraiser)

            role_name = user.partner_id.function or "Dirección de Proyecto"
            if not user.partner_id.function:
                if is_admin:
                    role_name = "Administrador GEOSIS"
                elif is_perito_appraiser:
                    role_name = "Perito Valuador"
                elif is_resident:
                    role_name = "Residente de Obra"
                elif is_supervisor:
                    role_name = "Fiscalizador / Supervisor"

            return {
                'status': 'success',
                'data': {
                    'name': user.name,
                    'role_name': role_name,
                    'is_resident': is_resident,
                    'is_supervisor': is_supervisor,
                    'is_perito': is_perito_appraiser or is_direction or is_admin,
                    'is_admin': is_admin,
                    'is_direction': is_direction
                }
            }
        except Exception as exc:
            return {'status': 'error', 'message': str(exc)}
