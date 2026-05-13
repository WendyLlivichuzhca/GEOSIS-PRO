from odoo import api, fields, models

class GeosisBudget(models.Model):
    _inherit = 'geosis.budget'

    # Este campo es para tu sistema interno de Proyectos Geosis
    project_id = fields.Many2one(
        'geosis.project',
        string='Proyecto Geosis',
        ondelete='set null',
    )

    # Este campo es NUEVO y exclusivo para el Cronograma/Gantt de Odoo
    odoo_project_id = fields.Many2one(
        'project.project',
        string='Proyecto Odoo (Cronograma)',
        ondelete='set null',
    )

    def action_create_schedule_tasks(self):
        self.ensure_one()
        if not self.odoo_project_id:
            raise models.ValidationError("Primero debes asignar un Proyecto Odoo a este presupuesto para generar el cronograma.")
        
        task_obj = self.env['project.task']
        
        # Limpiar tareas anteriores de este proyecto para evitar duplicados
        existing_tasks = task_obj.search([
            ('project_id', '=', self.odoo_project_id.id),
        ])
        if existing_tasks:
            existing_tasks.unlink()
        
        tasks_created = 0
        
        for line in self.line_ids:
            # Solo creamos tareas para los rubros que tengan fechas definidas
            if line.date_start and line.date_end:
                task_values = {
                    'name': f"[{line.apu_code}] {line.apu_name}",
                    'project_id': self.odoo_project_id.id,
                    'date_deadline': line.date_end,
                    'description': f"Cantidad a ejecutar: {line.quantity} {line.uom_name}",
                }
                # Campos para el Timeline (project_timeline OCA)
                if 'planned_date_start' in task_obj._fields:
                    task_values['planned_date_start'] = line.date_start
                if 'planned_date_end' in task_obj._fields:
                    task_values['planned_date_end'] = line.date_end
                # Compatibilidad con Odoo Enterprise
                if 'planned_date_begin' in task_obj._fields:
                    task_values['planned_date_begin'] = line.date_start
                
                task_obj.create(task_values)
                tasks_created += 1
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cronograma Generado',
                'message': f'Se han creado {tasks_created} tareas en el proyecto: {self.odoo_project_id.name}',
                'type': 'success',
                'sticky': False,
            }
        }

