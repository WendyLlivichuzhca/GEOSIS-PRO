import json
import base64
from odoo import http
from odoo.http import request

class GeosisMobileAPI(http.Controller):

    @http.route('/geosis/mobile/projects', type='json', auth='user', methods=['POST'])
    def get_projects(self):
        """ Retorna los proyectos activos o en planificación para el usuario """
        projects = request.env['geosis.project'].search([('state', 'in', ['draft', 'active'])])
        return {
            'status': 'success',
            'data': [{
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'location': p.location or '',
            } for p in projects]
        }

    @http.route('/geosis/mobile/submit_report', type='json', auth='user', methods=['POST'])
    def submit_report(self, **post):
        """ Recibe el reporte diario desde Flutter """
        try:
            data = post.get('report')
            if not data:
                return {'status': 'error', 'message': 'No data provided'}

            # Crear cabecera de bitácora
            bitacora = request.env['geosis.bitacora'].create({
                'project_id': data.get('project_id'),
                'weather': data.get('weather', 'sunny'),
                'content': data.get('content', ''),
                'latitude': data.get('latitude', 0.0),
                'longitude': data.get('longitude', 0.0),
            })

            # Crear tareas vinculadas
            for task in data.get('tasks', []):
                request.env['geosis.bitacora.task'].create({
                    'bitacora_id': bitacora.id,
                    'task_id': task.get('task_id'),
                    'progress': task.get('progress', 0),
                    'done': task.get('done', False),
                })

            # Procesar fotos (vienen en Base64 desde Flutter)
            for photo in data.get('photos', []):
                request.env['geosis.bitacora.photo'].create({
                    'bitacora_id': bitacora.id,
                    'image': photo.get('base64_image'),
                    'caption': photo.get('caption', ''),
                })

            return {
                'status': 'success',
                'bitacora_id': bitacora.id,
                'message': 'Reporte guardado correctamente'
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
