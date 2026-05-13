# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64
from datetime import datetime
import xml.etree.ElementTree as ET
from io import BytesIO

class GeosisBudgetExportMSProject(models.TransientModel):
    _name = 'geosis.budget.export.msproject'
    _description = 'Exportar Presupuesto a MS Project'

    budget_id = fields.Many2one('geosis.budget', string='Presupuesto', required=True)
    file_data = fields.Binary(string='Archivo XML', readonly=True)
    filename = fields.Char(string='Nombre de Archivo', readonly=True)

    def action_export(self):
        self.ensure_one()
        budget = self.budget_id
        
        # Crear estructura básica de MS Project XML
        project = ET.Element('Project', xmlns="http://schemas.microsoft.com/project")
        
        # Metadatos del Proyecto
        ET.SubElement(project, 'Name').text = budget.description or 'Presupuesto'
        ET.SubElement(project, 'Title').text = budget.description or 'Presupuesto'
        ET.SubElement(project, 'Company').text = self.env.company.name
        ET.SubElement(project, 'StartDate').text = datetime.now().strftime('%Y-%m-%dT08:00:00')
        
        # Contenedor de Tareas
        tasks = ET.SubElement(project, 'Tasks')
        
        # Tarea Raíz (El Proyecto completo)
        root_task = ET.SubElement(tasks, 'Task')
        ET.SubElement(root_task, 'UID').text = '0'
        ET.SubElement(root_task, 'ID').text = '0'
        ET.SubElement(root_task, 'Name').text = budget.description or 'Proyecto'
        ET.SubElement(root_task, 'Type').text = '1'
        ET.SubElement(root_task, 'CreateDate').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # Agregar cada rubro como una tarea
        uid_counter = 1
        for line in budget.line_ids:
            task = ET.SubElement(tasks, 'Task')
            ET.SubElement(task, 'UID').text = str(uid_counter)
            ET.SubElement(task, 'ID').text = str(uid_counter)
            ET.SubElement(task, 'Name').text = f"[{line.apu_code}] {line.apu_name}"
            ET.SubElement(task, 'OutlineLevel').text = '1'
            
            # Fechas si existen
            if line.date_start:
                ET.SubElement(task, 'Start').text = line.date_start.strftime('%Y-%m-%dT08:00:00')
            if line.date_end:
                ET.SubElement(task, 'Finish').text = line.date_end.strftime('%Y-%m-%dT17:00:00')
            
            # Duración aproximada (en formato MS Project: PT#H#M#S)
            if line.date_start and line.date_end:
                days = (line.date_end - line.date_start).days + 1
                ET.SubElement(task, 'Duration').text = f"PT{days*8}H0M0S"
                ET.SubElement(task, 'Manual').text = '0' # Auto programada
            else:
                ET.SubElement(task, 'Manual').text = '1' # Manual

            uid_counter += 1

        # Generar XML final
        output = BytesIO()
        tree = ET.ElementTree(project)
        tree.write(output, encoding='utf-8', xml_declaration=True)
        
        self.write({
            'file_data': base64.b64encode(output.getvalue()),
            'filename': f"Cronograma_{budget.code or 'export'}.xml"
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'geosis.budget.export.msproject',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
