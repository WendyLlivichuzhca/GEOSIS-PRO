from odoo import api, fields, models

class GeosisBitacora(models.Model):
    _name = 'geosis.bitacora'
    _description = 'Libro de Obra - Asiento Diario'
    _order = 'date desc, id desc'

    project_id = fields.Many2one('geosis.project', string='Proyecto', required=True, ondelete='cascade')
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user, required=True)
    
    weather = fields.Selection([
        ('sunny', 'Soleado'),
        ('cloudy', 'Nublado'),
        ('rainy', 'Lluvia'),
        ('storm', 'Tormenta'),
    ], string='Clima', default='sunny')

    content = fields.Text(string='Resumen del día')
    
    task_ids = fields.One2many('geosis.bitacora.task', 'bitacora_id', string='Tareas Realizadas')
    photo_ids = fields.One2many('geosis.bitacora.photo', 'bitacora_id', string='Evidencias Fotográficas')

    latitude = fields.Float(string='Latitud Reporte', digits=(10, 7))
    longitude = fields.Float(string='Longitud Reporte', digits=(10, 7))

class GeosisBitacoraTask(models.Model):
    _name = 'geosis.bitacora.task'
    _description = 'Tarea en Libro de Obra'

    bitacora_id = fields.Many2one('geosis.bitacora', string='Bitácora', ondelete='cascade')
    task_id = fields.Many2one('project.task', string='Tarea Cronograma', required=True)
    name = fields.Char(related='task_id.name', readonly=True)
    progress = fields.Integer(string='Avance (%)', default=0)
    done = fields.Boolean(string='Completado', default=False)
    notes = fields.Char(string='Notas')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.task_id:
                # Actualizar el progreso en la tarea real de Odoo
                record.task_id.write({
                    'progress': record.progress,
                    'is_done': record.done
                })
        return records

class GeosisBitacoraPhoto(models.Model):
    _name = 'geosis.bitacora.photo'
    _description = 'Foto de Evidencia'

    bitacora_id = fields.Many2one('geosis.bitacora', string='Bitácora', ondelete='cascade')
    image = fields.Binary(string='Foto', required=True)
    caption = fields.Char(string='Descripción')
    date_taken = fields.Datetime(string='Fecha/Hora Captura', default=fields.Datetime.now)
