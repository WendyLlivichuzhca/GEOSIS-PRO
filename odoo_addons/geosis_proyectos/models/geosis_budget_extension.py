from odoo import fields, models
from odoo.exceptions import ValidationError


class GeosisBudget(models.Model):
    _inherit = 'geosis.budget'

    project_id = fields.Many2one(
        'geosis.project',
        string='Proyecto Geosis',
        ondelete='set null',
    )

    odoo_project_id = fields.Many2one(
        'project.project',
        string='Proyecto Odoo (Cronograma)',
        ondelete='set null',
    )

    def _prepare_schedule_task_values(self, line):
        self.ensure_one()
        task_obj = self.env['project.task']
        description = f"Cantidad a ejecutar: {line.quantity} {line.uom_name or ''}".strip()
        if getattr(line, 'note', False):
            description = f"{description}\nObservacion: {line.note}"

        task_values = {
            'name': f"[{line.apu_code}] {line.apu_name}",
            'project_id': self.odoo_project_id.id,
            'budget_line_id': line.id,
            'date_deadline': line.date_end,
            'description': description,
        }
        if 'planned_date_start' in task_obj._fields:
            task_values['planned_date_start'] = line.date_start
        if 'planned_date_end' in task_obj._fields:
            task_values['planned_date_end'] = line.date_end
        if 'planned_date_begin' in task_obj._fields:
            task_values['planned_date_begin'] = line.date_start
        return task_values

    def action_create_schedule_tasks(self):
        self.ensure_one()
        if not self.odoo_project_id:
            raise ValidationError(
                "Primero debes asignar un Proyecto Odoo a este presupuesto para generar el cronograma."
            )

        task_obj = self.env['project.task']
        current_line_ids = self.line_ids.ids
        linked_tasks = task_obj.search([
            ('project_id', '=', self.odoo_project_id.id),
            ('budget_line_id', 'in', current_line_ids),
        ])
        linked_tasks_by_line = {
            task.budget_line_id.id: task
            for task in linked_tasks
            if task.budget_line_id
        }

        tasks_created = 0
        tasks_updated = 0
        tasks_removed = 0

        for line in self.line_ids:
            if line.date_start and line.date_end:
                task_values = self._prepare_schedule_task_values(line)
                existing_task = linked_tasks_by_line.get(line.id)

                if existing_task:
                    existing_task.write(task_values)
                    tasks_updated += 1
                    continue

                legacy_task = task_obj.search([
                    ('project_id', '=', self.odoo_project_id.id),
                    ('budget_line_id', '=', False),
                    ('name', '=', task_values['name']),
                ], limit=1)
                if legacy_task:
                    legacy_task.write(task_values)
                    tasks_updated += 1
                else:
                    task_obj.create(task_values)
                    tasks_created += 1
            else:
                existing_task = linked_tasks_by_line.get(line.id)
                if existing_task:
                    existing_task.unlink()
                    tasks_removed += 1

        if current_line_ids:
            obsolete_tasks = task_obj.search([
                ('project_id', '=', self.odoo_project_id.id),
                ('budget_line_id', '!=', False),
                ('budget_line_id', 'not in', current_line_ids),
            ])
        else:
            obsolete_tasks = task_obj.search([
                ('project_id', '=', self.odoo_project_id.id),
                ('budget_line_id', '!=', False),
            ])
        if obsolete_tasks:
            tasks_removed += len(obsolete_tasks)
            obsolete_tasks.unlink()

        message_parts = []
        if tasks_created:
            message_parts.append(f'{tasks_created} creadas')
        if tasks_updated:
            message_parts.append(f'{tasks_updated} actualizadas')
        if tasks_removed:
            message_parts.append(f'{tasks_removed} eliminadas')
        if not message_parts:
            message_parts.append('sin cambios')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cronograma Generado',
                'message': f"Tareas del proyecto {self.odoo_project_id.name}: {', '.join(message_parts)}.",
                'type': 'success',
                'sticky': False,
            }
        }
