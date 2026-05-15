import json
import base64
from odoo import http
from odoo.http import request

class GeosisMobileAPI(http.Controller):

    @http.route('/web/geosis/projects', type='json', auth='none', methods=['POST'], csrf=False)
    def get_projects(self):
        """ Endpoint simplificado para evitar 404 """
        try:
            projects = request.env['geosis.project'].sudo().search([]) 
            data = []
            for p in projects:
                # Buscamos tareas reales
                project_real = p.project_id
                tasks = []
                if project_real:
                    tasks = request.env['project.task'].sudo().search([('project_id', '=', project_real.id)])
                
                data.append({
                    'id': p.id,
                    'name': p.name,
                    'code': p.code or 'S/N',
                    'tasks': [{'id': t.id, 'name': t.name, 'progress': 0.0} for t in tasks]
                })
            return {'status': 'success', 'data': data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        for p in projects:
            # Buscamos tareas asociadas al proyecto de Odoo estándar
            # Usamos sudo() por si hay problemas de permisos
            tasks = request.env['project.task'].sudo().search([('project_id', '=', p.project_id.id)])
            data.append({
                'id': p.id,
                'name': p.name,
                'code': p.code or 'S/N',
                'location': p.location or 'Sin ubicación',
                'tasks': [{
                    'id': t.id,
                    'name': t.name,
                    'progress': getattr(t, 'progress_real', 0.0), # Evitamos error si el campo no existe
                } for t in tasks]
            })
        return {
            'status': 'success',
            'data': data
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
