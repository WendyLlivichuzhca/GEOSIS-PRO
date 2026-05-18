from odoo import api, fields, models

class GeosisBitacora(models.Model):
    _name = 'geosis.bitacora'
    _description = 'Libro de Obra - Asiento Diario'
    _order = 'date desc, id desc'

    project_id = fields.Many2one('geosis.project', string='Proyecto', required=True, ondelete='cascade')
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user, required=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
    ], string='Estado', default='draft', required=True)

    weather = fields.Selection([
        ('sunny', 'Soleado'),
        ('cloudy', 'Nublado'),
        ('rainy', 'Lluvia'),
        ('storm', 'Tormenta'),
    ], string='Clima', default='sunny')

    content = fields.Text(string='Resumen del día')
    
    # Nuevos campos según normativa MIDUVI
    personal_notes = fields.Text(string='Personal en Obra')
    equipment_notes = fields.Text(string='Equipos/Maquinaria')
    contractor_queries = fields.Text(string='Consultas del Contratista')
    inspector_instructions = fields.Text(string='Instrucciones/Autorizaciones del Fiscalizador')
    
    signature_contractor = fields.Binary(string='Firma Contratista')
    signature_inspector = fields.Binary(string='Firma Fiscalizador')

    task_ids = fields.One2many('geosis.bitacora.task', 'bitacora_id', string='Tareas Realizadas')
    photo_ids = fields.One2many('geosis.bitacora.photo', 'bitacora_id', string='Evidencias Fotográficas')

    latitude = fields.Float(string='Latitud Reporte', digits=(10, 7))
    longitude = fields.Float(string='Longitud Reporte', digits=(10, 7))

    def action_approve(self):
        for record in self:
            record.write({'state': 'approved'})
            
            # 1. Buscar el presupuesto/contrato del proyecto
            budget = record.project_id.budget_ids.filtered(lambda b: b.state != 'archived')[:1]
            if not budget:
                continue
                
            # 2. Buscar o crear la planilla en borrador
            Estimation = self.env['geosis.estimation'].sudo()
            EstimationLine = self.env['geosis.estimation.line'].sudo()
            
            estimation = Estimation.search([
                ('budget_id', '=', budget.id),
                ('state', '=', 'draft')
            ], limit=1, order='date desc')
            
            if not estimation:
                estimation = Estimation.create({
                    'name': f"Planilla - {record.project_id.name}",
                    'budget_id': budget.id,
                    'date': record.date,
                    'state': 'draft',
                })
                # Crear las líneas vacías basadas en los rubros contractuales
                for bline in budget.line_ids:
                    EstimationLine.create({
                        'estimation_id': estimation.id,
                        'budget_line_id': bline.id,
                        'uom_id': bline.apu_id.uom_name or 'u',
                        'unit_price': bline.unit_price,
                        'qty_current': 0.0,
                    })
            
            # 3. Sumar cantidades ejecutadas basándose en el incremento de progreso diario
            for btask in record.task_ids:
                prev_btask = self.env['geosis.bitacora.task'].search([
                    ('task_id', '=', btask.task_id.id),
                    ('bitacora_id.project_id', '=', record.project_id.id),
                    ('bitacora_id.state', '=', 'approved'),
                    ('bitacora_id.date', '<', record.date)
                ], order='bitacora_id.date desc, id desc', limit=1)
                
                prev_progress = prev_btask.progress if prev_btask else 0
                progress_increment = max(btask.progress - prev_progress, 0)
                
                if progress_increment > 0:
                    daily_qty = (progress_increment / 100.0) * btask.task_id.quantity
                    
                    eline = EstimationLine.search([
                        ('estimation_id', '=', estimation.id),
                        ('budget_line_id', '=', btask.task_id.id)
                    ], limit=1)
                    
                    if eline:
                        eline.write({
                            'qty_current': eline.qty_current + daily_qty
                        })

class GeosisBitacoraTask(models.Model):
    _name = 'geosis.bitacora.task'
    _description = 'Tarea en Libro de Obra'

    bitacora_id = fields.Many2one('geosis.bitacora', string='Bitácora', ondelete='cascade')
    task_id = fields.Many2one('geosis.budget.line', string='Rubro APU', required=True)
    name = fields.Char(related='task_id.apu_name', readonly=True)
    progress = fields.Integer(string='Avance (%)', default=0)
    done = fields.Boolean(string='Completado', default=False)
    notes = fields.Char(string='Notas')

class GeosisBitacoraPhoto(models.Model):
    _name = 'geosis.bitacora.photo'
    _description = 'Foto de Evidencia'

    bitacora_id = fields.Many2one('geosis.bitacora', string='Bitácora', ondelete='cascade')
    image = fields.Binary(string='Foto', required=True)
    caption = fields.Char(string='Descripción')
    date_taken = fields.Datetime(string='Fecha/Hora Captura', default=fields.Datetime.now)
