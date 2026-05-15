from odoo import http
from odoo.http import request
import json

class GeosisMobileAPI(http.Controller):

    @http.route('/web/geosis/projects', type='json', auth='none', methods=['POST'], csrf=False)
    def get_projects(self):
        try:
            projects = request.env['geosis.project'].sudo().search([])
            data = []
            for p in projects:
                # Intentamos obtener el proyecto de Odoo vinculado
                # En algunos casos el campo puede llamarse diferente, probamos con el ID directo
                tasks = []
                # Buscamos si existe una relación con project.task de forma genérica
                task_records = request.env['project.task'].sudo().search([('project_id', '!=', False)], limit=5)
                # O mejor, buscamos tareas que coincidan con el nombre del proyecto si no hay link directo
                if not task_records:
                     task_records = request.env['project.task'].sudo().search([('name', 'ilike', p.name)], limit=5)

                data.append({
                    'id': p.id,
                    'name': p.name,
                    'code': p.code or 'S/N',
                    'tasks': [{'id': t.id, 'name': t.name, 'progress': 0.0} for t in task_records]
                })
            return {'status': 'success', 'data': data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
