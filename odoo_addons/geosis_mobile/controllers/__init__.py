from odoo import http
from odoo.http import request
import json

class GeosisMobileAPI(http.Controller):

    @http.route('/web/geosis/projects', type='json', auth='none', methods=['POST'], csrf=False)
    def get_projects(self):
        try:
            # 1. Buscamos tus proyectos de GEOSIS
            projects = request.env['geosis.project'].sudo().search([('state', 'in', ['planning', 'active'])])
            data = []
            
            for p in projects:
                # 2. Buscamos el presupuesto vinculado (tomamos el primero aprobado o borrador)
                budget = request.env['geosis.budget'].sudo().search([
                    ('project_id', '=', p.id),
                    ('state', '!=', 'archived')
                ], limit=1, order='budget_date desc')
                
                tasks = []
                if budget:
                    # 3. Filtramos los rubros: Solo los que tienen fechas programadas (Cronograma)
                    budget_lines = request.env['geosis.budget.line'].sudo().search([
                        ('budget_id', '=', budget.id),
                        ('date_start', '!=', False),
                        ('date_end', '!=', False)
                    ])
                    
                    for line in budget_lines:
                        tasks.append({
                            'id': line.id,
                            'name': line.apu_name or 'Rubro sin nombre',
                            'progress': 0.0,
                            'uom': line.uom_name or 'u',
                            'start': line.date_start,
                            'end': line.date_end,
                        })
                
                data.append({
                    'id': p.id,
                    'name': p.name,
                    'code': p.code or 'S/N',
                    'location': p.location or 'Sin ubicación',
                    'tasks': tasks
                })
                
            return {'status': 'success', 'data': data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/geosis/submit_report', type='json', auth='none', methods=['POST'], csrf=False)
    def submit_report(self):
        try:
            params = request.get_json_data().get('params', {})
            data = params.get('report')
            if not data:
                return {'status': 'error', 'message': 'No se proporcionaron datos del reporte'}

            # 1. Crear el Asiento de Bitácora
            bitacora_vals = {
                'project_id': int(data.get('project_id')),
                'date': data.get('date'),
                'weather': data.get('weather', 'sunny'),
                'content': data.get('content', ''),
                'personal_notes': data.get('personal_notes', ''),
                'equipment_notes': data.get('equipment_notes', ''),
                'contractor_queries': data.get('contractor_queries', ''),
                'latitude': float(data.get('latitude', 0.0)),
                'longitude': float(data.get('longitude', 0.0)),
                'state': 'draft'
            }

            # Procesar Firma del Contratista si viene en Base64
            if data.get('signature_contractor'):
                bitacora_vals['signature_contractor'] = data.get('signature_contractor')

            bitacora = request.env['geosis.bitacora'].sudo().create(bitacora_vals)

            # 2. Crear las Tareas/Rubros vinculados
            for task in data.get('tasks', []):
                request.env['geosis.bitacora.task'].sudo().create({
                    'bitacora_id': bitacora.id,
                    'task_id': int(task.get('task_id')),
                    'progress': int(task.get('progress', 0)),
                    'done': bool(task.get('done', False)),
                    'notes': task.get('notes', ''),
                })

            # 3. Procesar Fotos (en Base64)
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
                'message': 'Libro de Obra guardado correctamente en Odoo'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/web/geosis/bitacoras', type='json', auth='none', methods=['POST'], csrf=False)
    def get_bitacoras(self):
        try:
            params = request.get_json_data().get('params', {})
            project_id = params.get('project_id')
            
            domain = []
            if project_id:
                domain.append(('project_id', '=', int(project_id)))
                
            bitacoras = request.env['geosis.bitacora'].sudo().search(domain, order='date desc, id desc')
            data = []
            for b in bitacoras:
                tasks = []
                for t in b.task_ids:
                    tasks.append({
                        'task_name': t.task_id.apu_name or 'Rubro sin nombre',
                        'progress': t.progress,
                        'notes': t.notes or '',
                    })
                
                photos = []
                for p in b.photo_ids:
                    photos.append({
                        'caption': p.caption or '',
                        'image': p.image or '',
                    })
                    
                data.append({
                    'id': b.id,
                    'project_id': b.project_id.id,
                    'project_name': b.project_id.name,
                    'date': str(b.date),
                    'weather': b.weather or 'sunny',
                    'content': b.content or '',
                    'personal_notes': b.personal_notes or '',
                    'equipment_notes': b.equipment_notes or '',
                    'contractor_queries': b.contractor_queries or '',
                    'inspector_instructions': b.inspector_instructions or '',
                    'state': b.state or 'draft',
                    'signature_contractor': b.signature_contractor or '',
                    'signature_inspector': b.signature_inspector or '',
                    'tasks': tasks,
                    'photos': photos,
                })
            return {'status': 'success', 'data': data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
