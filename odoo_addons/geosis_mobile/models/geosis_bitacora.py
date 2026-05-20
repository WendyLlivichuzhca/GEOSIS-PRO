import base64
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
            ], limit=1, order='estimation_date desc, id desc')
            
            if not estimation:
                # Generar código automático simple
                last_est = Estimation.search([], order='id desc', limit=1)
                next_num = 1
                if last_est and last_est.code and last_est.code.startswith('EST-'):
                    try:
                        next_num = int(last_est.code.split('-')[1]) + 1
                    except: pass
                code = "EST-%04d" % next_num

                estimation = Estimation.create({
                    'code': code,
                    'project_id': record.project_id.id,
                    'budget_id': budget.id,
                    'estimation_date': record.date,
                    'state': 'draft',
                })
                # Crear las líneas vacías basadas en los rubros contractuales
                for bline in budget.line_ids:
                    EstimationLine.create({
                        'estimation_id': estimation.id,
                        'budget_line_id': bline.id,
                        'quantity_executed': 0.0,
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
                            'quantity_executed': eline.quantity_executed + daily_qty
                        })
            
            # 4. Enviar notificación automática por correo con el PDF MIDUVI adjunto
            try:
                pdf_data, dummy = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    'geosis_mobile.action_report_geosis_bitacora', [record.id]
                )
                
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': f"Libro_de_Obra_Dia_{record.date}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_data),
                    'res_model': 'geosis.bitacora',
                    'res_id': record.id,
                    'mimetype': 'application/pdf',
                })
                
                recipients = []
                if record.project_id.user_id and record.project_id.user_id.email:
                    recipients.append(record.project_id.user_id.email)
                if record.user_id and record.user_id.email:
                    recipients.append(record.user_id.email)
                if record.write_uid and record.write_uid.email:
                    recipients.append(record.write_uid.email)

                recipients = list(set(filter(None, recipients)))
                if not recipients:
                    admin_email = self.env.user.email or self.env.company.email
                    if admin_email:
                        recipients.append(admin_email)

                if recipients:
                    mail_values = {
                        'subject': f"📢 Libro de Obra Aprobado: {record.project_id.name} - Dia {record.date}",
                        'body_html': f"""
                            <div style="font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
                                <div style="background-color: #0d1b2a; padding: 20px; text-align: center; color: white;">
                                    <h2 style="margin: 0; font-size: 20px; font-weight: bold; letter-spacing: 1px;">GEOSIS-PRO</h2>
                                    <span style="font-size: 12px; color: #00b4d8;">Sistema Automatizado de Control de Obras</span>
                                </div>
                                <div style="padding: 25px; background-color: #ffffff; line-height: 1.6;">
                                    <p style="margin-top: 0; font-size: 15px;">Estimado Director de Proyecto,</p>
                                    <p style="font-size: 14px;">Le informamos que el reporte del <strong>Libro de Obra</strong> correspondiente al dia <strong>{record.date}</strong> ha sido <strong>revisado, firmado y aprobado legalmente</strong> por la Fiscalizacion.</p>
                                    
                                    <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0; border-radius: 4px;">
                                        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                                            <tr>
                                                <td style="padding: 5px 0; font-weight: bold; color: #555; width: 35%;">Proyecto:</td>
                                                <td style="padding: 5px 0; color: #333;">{record.project_id.name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 5px 0; font-weight: bold; color: #555;">Fecha:</td>
                                                <td style="padding: 5px 0; color: #333;">{record.date}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 5px 0; font-weight: bold; color: #555;">Clima Reportado:</td>
                                                <td style="padding: 5px 0; color: #333;">{record.weather.upper()}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 5px 0; font-weight: bold; color: #555;">Residente:</td>
                                                <td style="padding: 5px 0; color: #333;">{record.user_id.name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 5px 0; font-weight: bold; color: #555;">Aprobado por:</td>
                                                <td style="padding: 5px 0; color: #333;">{record.write_uid.name} (Fiscalizador)</td>
                                            </tr>
                                        </table>
                                    </div>
                                    
                                    <p style="font-size: 13px; color: #555;">Adjunto a este correo encontrara la <strong>Ficha Tecnica MIDUVI Oficial en formato PDF</strong> con el desglose de recursos, avance de rubros contractuales (sincronizados con planillas), registro fotografico de evidencias y las firmas electronicas correspondientes.</p>
                                    
                                    <div style="text-align: center; margin-top: 30px;">
                                        <a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/my/bitacora/{record.id}" 
                                           style="background-color: #007bff; color: white; padding: 12px 25px; text-decoration: none; font-size: 14px; font-weight: bold; border-radius: 5px; display: inline-block; box-shadow: 0 4px 6px rgba(0,123,255,0.15);">
                                            Ver Ficha en el Portal Web
                                        </a>
                                    </div>
                                </div>
                                <div style="background-color: #f1f3f5; padding: 15px; text-align: center; font-size: 11px; color: #777; border-top: 1px solid #e0e0e0;">
                                    Este es un correo automatico generado por GEOSIS-PRO ERP. Por favor, no responder directamente.
                                </div>
                            </div>
                        """,
                        'email_to': ','.join(recipients),
                        'attachment_ids': [(4, attachment.id)],
                    }
                    self.env['mail.mail'].sudo().create(mail_values).send()
                    print(f"DEBUG: Correo de aprobacion de Libro de Obra enviado a: {recipients}")
            except Exception as mail_err:
                print(f"DEBUG: Error al enviar correo de notificacion automatica: {mail_err}")

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
