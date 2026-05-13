import base64
import io
import os
import re
import zipfile
from xml.etree import ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import UserError


XLSX_NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pkg': 'http://schemas.openxmlformats.org/package/2006/relationships',
}


BUDGET_HEADER_ALIASES = {
    'item': ('item', 'item nro', 'it', 'nro', '#', 'n'),
    'code': ('codigo', 'code', 'cod', 'codigo rubro', 'codigo apu', 'apu'),
    'name': ('descripcion', 'detalle', 'concepto', 'nombre', 'rubro'),
    'uom_name': ('unidad', 'unidad de medida', 'u m', 'um', 'und'),
    'quantity': ('cantidad', 'cant', 'qty'),
    'unit_price': ('precio unitario', 'unitario', 'p u', 'pu', 'precio unit'),
    'total': ('total', 'subtotal', 'precio total', 'valor total'),
}


APU_HEADER_ALIASES = {
    'code': ('codigo', 'code', 'cod'),
    'name': ('descripcion', 'detalle', 'concepto', 'nombre', 'recurso'),
    'category': ('categoria', 'tipo'),
    'uom_name': ('unidad', 'unidad de medida', 'u m', 'um', 'und'),
    'quantity': ('cantidad', 'cant', 'qty'),
    'rate': ('tarifa', 'precio', 'rate', 'precio unitario'),
    'performance': ('rendimiento', 'performance', 'rend'),
    'cost': ('costo', 'cost'),
    'percentage': ('porcentaje', 'participacion'),
    'distance': ('distancia', 'distance'),
    'note': ('observacion', 'nota', 'note'),
}


METADATA_LABEL_ALIASES = {
    'budget_code': (
        'codigo presupuesto',
        'cod presupuesto',
        'nro presupuesto',
        'numero presupuesto',
    ),
    'budget_name': (
        'presupuesto',
        'descripcion presupuesto',
        'nombre presupuesto',
        'objeto',
    ),
    'project_code': (
        'codigo proyecto',
        'cod proyecto',
        'nro proyecto',
        'numero proyecto',
    ),
    'project_name': (
        'nombre proyecto',
        'proyecto',
        'nombre de proyecto',
        'obra',
    ),
    'partner_id': (
        'cliente',
        'contratante',
        'propietario',
        'beneficiario',
    ),
    'location': (
        'ubicacion',
        'localizacion',
        'lugar',
        'sitio',
        'direccion',
        'sector',
    ),
}


CATEGORY_LABELS = {
    'M': ('equipo', 'equipos', 'herramienta', 'herramientas', 'maquinaria', 'equipo y herramienta'),
    'N': ('mano de obra', 'labor'),
    'O': ('material', 'materiales'),
    'P': ('transporte', 'flete'),
}


CUSTOMER_HINTS = (
    'universidad',
    'municipio',
    'gobierno',
    'ministerio',
    'empresa',
    'hospital',
    'colegio',
    'escuela',
    'instituto',
    'prefectura',
    'constructora',
    'consorcio',
    'corporacion',
    'fundacion',
    'cooperativa',
    'banco',
)


LOCATION_HINTS = (
    'ubicacion',
    'localizacion',
    'direccion',
    'campus',
    'ciudad',
    'sector',
    'parroquia',
    'canton',
    'provincia',
    'avenida',
    'av ',
    'calle',
)


UOM_ALIASES = {
    'u': ('Unit(s)', 'Units'),
    'unit': ('Unit(s)', 'Units'),
    'und': ('Unit(s)', 'Units'),
    'hr': ('Hours',),
    'hora': ('Hours',),
    'hours': ('Hours',),
    'h': ('Hours',),
    'm': ('m', 'Meter'),
    'ml': ('m', 'Meter'),
    'm2': ('m²', 'Square Meter'),
    'm²': ('m²', 'Square Meter'),
    'm3': ('m³', 'Cubic Meter'),
    'm³': ('m³', 'Cubic Meter'),
    'kg': ('kg',),
    'glb': ('Unit(s)', 'Units'),
}


class GeosisExcelImportWizard(models.TransientModel):
    _name = 'geosis.excel.import.wizard'
    _description = 'Importador Excel GEOSIS'

    file_data = fields.Binary(string='Archivo Excel', required=True)
    file_name = fields.Char(string='Nombre del Archivo')
    budget_code = fields.Char(string='Codigo Presupuesto')
    budget_name = fields.Char(string='Descripcion Presupuesto')
    project_code = fields.Char(string='Codigo Proyecto')
    project_name = fields.Char(string='Nombre del Proyecto')
    partner_id = fields.Many2one('res.partner', string='Cliente')
    location = fields.Char(string='Ubicacion')
    budget_date = fields.Date(
        string='Fecha Presupuesto',
        default=fields.Date.context_today,
        required=True,
    )
    import_apu_sheets = fields.Boolean(
        string='Importar hojas APU',
        default=True,
        help='Si encuentra hojas cuyo nombre coincide con el codigo del rubro, crea o actualiza el detalle del APU y sus recursos.',
    )
    create_missing_apus = fields.Boolean(
        string='Crear APU faltantes',
        default=True,
        help='Si un rubro del presupuesto no existe, lo crea automaticamente.',
    )
    update_existing_apus = fields.Boolean(
        string='Actualizar APUs existentes',
        default=True,
        help='Si existe un APU con el mismo codigo y encuentra hoja detalle, reemplaza sus lineas con la informacion del Excel.',
    )
    replace_budget_lines = fields.Boolean(
        string='Reemplazar lineas del presupuesto',
        default=True,
        help='Si el presupuesto ya existe, elimina sus lineas antes de volver a importar.',
    )
    use_budget_sheet_prices = fields.Boolean(
        string='Respetar precios del presupuesto',
        default=True,
        help='Si la hoja Presupuesto trae precio unitario, se usa ese valor en las lineas.',
    )
    note = fields.Text(string='Observaciones')

    @api.onchange('file_data', 'file_name')
    def _onchange_file_data(self):
        for wizard in self:
            if not wizard.file_data:
                continue

            try:
                _, _, _, metadata = wizard._load_workbook_context()
            except Exception:
                continue

            for field_name in (
                'budget_code',
                'budget_name',
                'project_code',
                'project_name',
                'partner_id',
                'location',
            ):
                if not wizard[field_name] and metadata.get(field_name):
                    wizard[field_name] = metadata[field_name]

    def action_import_excel(self):
        self.ensure_one()

        if not self.file_data:
            raise UserError(_('Debes seleccionar un archivo .xlsx para importar.'))

        workbook, budget_sheet_name, budget_sheet_rows, metadata = self._load_workbook_context()
        budget_lines = self._extract_budget_lines(budget_sheet_rows)

        if not budget_lines:
            raise UserError(_('No pude encontrar lineas validas en la hoja principal del presupuesto.'))

        project = self._get_or_create_project(metadata)
        budget = self._get_or_create_budget(project, metadata)

        if self.replace_budget_lines and budget.line_ids:
            budget.line_ids.unlink()

        apu_sheet_map = self._build_apu_sheet_map(workbook, budget_sheet_name, budget_lines)
        apu_cache = {}
        missing_codes = []
        chapter_stack = {} # level -> chapter_id

        for index, line_data in enumerate(budget_lines, start=1):
            if line_data.get('is_chapter'):
                level = line_data.get('level', 1)
                parent_chapter = chapter_stack.get(level - 1)
                
                chapter = self.env['geosis.budget.chapter'].create({
                    'budget_id': budget.id,
                    'sequence': index * 10,
                    'code': line_data['item'],
                    'name': line_data['name'],
                    'parent_id': parent_chapter,
                })
                chapter_stack[level] = chapter.id
                # Limpiar niveles inferiores del stack
                for l in list(chapter_stack.keys()):
                    if l > level:
                        del chapter_stack[l]
                continue

            # Es un rubro
            apu = self._get_or_create_apu(workbook, line_data, apu_sheet_map, apu_cache)
            if not apu:
                missing_codes.append(line_data['code'])
                continue

            unit_price = line_data['unit_price']
            if not self.use_budget_sheet_prices or not unit_price:
                unit_price = apu.total_cost or unit_price

            # Determinar a qué capítulo pertenece este rubro
            # Buscamos el nivel más profundo activo en el stack
            current_chapter_id = False
            if chapter_stack:
                max_level = max(chapter_stack.keys())
                current_chapter_id = chapter_stack[max_level]

            self.env['geosis.budget.line'].create(
                {
                    'budget_id': budget.id,
                    'sequence': index * 10,
                    'chapter_id': current_chapter_id,
                    'apu_id': apu.id,
                    'quantity': line_data['quantity'],
                    'unit_price': unit_price,
                    'note': line_data.get('note') or False,
                }
            )

        if missing_codes:
            raise UserError(
                _('Faltan rubros APU y la opcion de crear faltantes esta desactivada: %s')
                % ', '.join(sorted(set(filter(None, missing_codes))))
            )

        budget._compute_totals()
        if project:
            project._compute_budget_metrics()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Presupuesto Importado'),
            'res_model': 'geosis.budget',
            'view_mode': 'form',
            'res_id': budget.id,
            'target': 'current',
        }

    def _load_workbook_context(self):
        workbook = GeosisSimpleXlsxReader(base64.b64decode(self.file_data))
        budget_sheet_name, budget_sheet_rows = self._find_budget_sheet(workbook)
        metadata = self._extract_budget_metadata(budget_sheet_rows, budget_sheet_name)
        return workbook, budget_sheet_name, budget_sheet_rows, metadata

    def _find_budget_sheet(self, workbook):
        for sheet_name in workbook.sheet_names:
            if 'presupuesto' in _normalize_text(sheet_name):
                return sheet_name, workbook.get_sheet(sheet_name)

        for sheet_name in workbook.sheet_names:
            rows = workbook.get_sheet(sheet_name)
            header_index, header_map = self._detect_header(rows, BUDGET_HEADER_ALIASES)
            if header_index is not None and 'name' in header_map:
                return sheet_name, rows

        raise UserError(_('No encontre una hoja tipo Presupuesto en el archivo Excel.'))

    def _extract_budget_lines(self, rows):
        header_index, header_map = self._detect_header(rows, BUDGET_HEADER_ALIASES)
        if header_index is None:
            return []

        parsed_lines = []
        blank_count = 0

        for raw_row in rows[header_index + 1 :]:
            item = _cell_as_string(_value_at(raw_row, header_map.get('item')))
            code = _cell_as_string(_value_at(raw_row, header_map.get('code')))
            name = _cell_as_string(_value_at(raw_row, header_map.get('name')))
            uom_name = _cell_as_string(_value_at(raw_row, header_map.get('uom_name')))
            quantity = _to_float(_value_at(raw_row, header_map.get('quantity')), default=0.0)
            unit_price = _to_float(_value_at(raw_row, header_map.get('unit_price')), default=0.0)
            total = _to_float(_value_at(raw_row, header_map.get('total')), default=0.0)

            if not code and not name and not quantity and not unit_price and not total:
                blank_count += 1
                if blank_count >= 5:
                    break
                continue

            blank_count = 0

            if not code and not name:
                continue

            # Detectar si es capítulo (Fila sin código o con formato de ítem jerárquico)
            is_chapter = False
            level = 1
            if not code and name:
                is_chapter = True
                if item:
                    level = len(item.split('.'))
            
            if is_chapter:
                parsed_lines.append({
                    'is_chapter': True,
                    'item': item or '',
                    'name': name,
                    'level': level,
                })
                continue

            code = code or self._make_code('APU', name)
            if not unit_price and quantity and total:
                unit_price = total / quantity

            parsed_lines.append(
                {
                    'item': item or '',
                    'code': code,
                    'name': name or code,
                    'uom_name': uom_name or 'Unit(s)',
                    'quantity': quantity or 1.0,
                    'unit_price': unit_price or 0.0,
                    'total': total or (quantity or 1.0) * (unit_price or 0.0),
                }
            )

        return parsed_lines

    def _build_apu_sheet_map(self, workbook, budget_sheet_name, budget_lines):
        if not self.import_apu_sheets:
            return {}

        available_names = [name for name in workbook.sheet_names if name != budget_sheet_name]
        normalized_sheet_names = {_normalize_text(name): name for name in available_names}

        mapping = {}
        for line_data in budget_lines:
            if line_data.get('is_chapter'):
                continue
            code = line_data['code']
            normalized_code = _normalize_text(code)
            matched_name = normalized_sheet_names.get(normalized_code)
            if matched_name:
                mapping[code] = matched_name
                continue

            for normalized_name, original_name in normalized_sheet_names.items():
                if (
                    normalized_name == normalized_code
                    or normalized_name.startswith(normalized_code)
                    or normalized_code.startswith(normalized_name)
                ):
                    mapping[code] = original_name
                    break

        return mapping

    def _extract_budget_metadata(self, rows, budget_sheet_name):
        header_index, _ = self._detect_header(rows, BUDGET_HEADER_ALIASES)
        scan_until = header_index if header_index is not None else min(len(rows), 30)
        scan_rows = rows[: max(scan_until, 12)]
        metadata = {field_name: False for field_name in METADATA_LABEL_ALIASES}
        title_candidates = []
        text_candidates = []

        for raw_row in scan_rows[:40]:
            non_empty_values = [_cell_as_string(value) for value in raw_row if _cell_as_string(value)]
            if not non_empty_values:
                continue

            joined_text = ' '.join(non_empty_values).strip()
            normalized_joined = _normalize_text(joined_text)
            text_candidates.append(joined_text)
            if (
                joined_text
                and len(joined_text) >= 12
                and (
                    'presupuesto' in normalized_joined
                    or 'proyecto' in normalized_joined
                    or len(non_empty_values) <= 3
                )
            ):
                title_candidates.append(joined_text)

            for column_index, cell_value in enumerate(raw_row):
                raw_text = _cell_as_string(cell_value)
                normalized = _normalize_text(raw_text)
                if not normalized:
                    continue

                for field_name, aliases in METADATA_LABEL_ALIASES.items():
                    if metadata[field_name]:
                        continue
                    if not self._matches_metadata_label(normalized, aliases):
                        continue

                    candidate_value = self._extract_metadata_value(raw_text, raw_row, column_index)
                    if candidate_value:
                        metadata[field_name] = candidate_value
                        break

        file_stem = os.path.splitext(self.file_name or budget_sheet_name or 'importacion')[0]
        metadata['location'] = metadata['location'] or self._derive_location(text_candidates)
        metadata['budget_name'] = (
            metadata['budget_name']
            or self._pick_best_title(title_candidates)
            or file_stem
        )
        metadata['project_name'] = (
            metadata['project_name']
            or self._derive_project_name(metadata['budget_name'])
            or self._derive_project_name(file_stem)
        )
        metadata['project_code'] = (
            metadata['project_code']
            or self._derive_project_code(metadata['project_name'] or metadata['budget_name'] or file_stem)
        )
        metadata['partner_id'] = (
            metadata['partner_id']
            or self._derive_customer_name(text_candidates, metadata['location'], metadata['project_name'])
        )
        metadata['budget_code'] = metadata['budget_code'] or self._make_code('PRES', metadata['budget_name'])

        return metadata

    def _matches_metadata_label(self, normalized, aliases):
        for alias in aliases:
            if normalized == alias:
                return True
            if normalized.startswith('%s ' % alias):
                return True
            if normalized.startswith('%s:' % alias):
                return True
        return False

    def _extract_metadata_value(self, raw_label, raw_row, column_index):
        if ':' in raw_label:
            inline_value = raw_label.split(':', 1)[1].strip()
            if inline_value and not self._looks_like_metadata_label(inline_value):
                return inline_value

        for offset in range(1, 4):
            candidate = _cell_as_string(_value_at(raw_row, column_index + offset))
            if candidate and not self._looks_like_metadata_label(candidate):
                return candidate

        return False

    def _looks_like_metadata_label(self, raw_value):
        normalized = _normalize_text(raw_value)
        if not normalized:
            return False

        for aliases in METADATA_LABEL_ALIASES.values():
            if any(normalized == alias for alias in aliases):
                return True
        return False

    def _pick_best_title(self, candidates):
        for candidate in candidates:
            normalized = _normalize_text(candidate)
            if 'presupuesto' in normalized:
                return candidate
        return candidates[0] if candidates else False

    def _derive_project_name(self, raw_value):
        text = _cell_as_string(raw_value)
        if not text:
            return False

        cleaned = re.sub(r'(?i)\bpresupuesto\b', ' ', text)
        cleaned = re.sub(
            r'(?i)\b(final|actualizado|actualizacion|actualizada|version|v\d+)\b',
            ' ',
            cleaned,
        )
        cleaned = re.sub(
            r'(?i)\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b',
            ' ',
            cleaned,
        )
        cleaned = re.sub(r'\b20\d{2}\b', ' ', cleaned)
        cleaned = re.sub(r'[_\-]+', ' ', cleaned)
        cleaned = ' '.join(cleaned.split()).strip(' -')

        return cleaned or text

    def _derive_project_code(self, raw_value):
        text = self._derive_project_name(raw_value) or _cell_as_string(raw_value)
        if not text:
            return False
        return self._make_code('PROY', text)

    def _derive_customer_name(self, candidates, location, project_name):
        searchable_candidates = list(candidates or [])
        if location:
            searchable_candidates.insert(0, location)

        for candidate in searchable_candidates:
            cleaned = self._clean_customer_candidate(candidate, project_name)
            normalized = _normalize_text(cleaned)
            if not cleaned or len(cleaned) < 6:
                continue
            if any(hint in normalized for hint in CUSTOMER_HINTS):
                return cleaned

        for candidate in searchable_candidates:
            cleaned = self._clean_customer_candidate(candidate, project_name)
            if cleaned and len(cleaned) >= 6:
                return cleaned

        return False

    def _resolve_partner(self, partner_name):
        if not partner_name:
            return False
        partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': partner_name})
        return partner.id

    def _clean_customer_candidate(self, raw_value, project_name):
        text = _cell_as_string(raw_value)
        if not text:
            return False

        normalized = _normalize_text(text)
        if not normalized or 'presupuesto' in normalized:
            return False

        if ':' in text:
            text = text.split(':', 1)[1].strip()

        if project_name and _normalize_text(project_name) == normalized:
            return False

        text = re.split(r'(?i)\b(ciudad de|sector|parroquia|canton|provincia|campus|direccion)\b', text, maxsplit=1)[0]
        text = text.split(',')[0].strip()
        text = re.sub(r'(?i)\b(ubicacion|localizacion|cliente|contratante|propietario|beneficiario)\b', ' ', text)
        text = ' '.join(text.split()).strip(' -')
        return text or False

    def _derive_location(self, candidates):
        for candidate in candidates or []:
            normalized = _normalize_text(candidate)
            if not normalized or 'presupuesto' in normalized:
                continue
            if any(hint in normalized for hint in LOCATION_HINTS):
                return candidate
        return False

    def _get_or_create_project(self, metadata):
        project_model = self.env['geosis.project']
        company = self.env.company

        project_code = (self.project_code or metadata.get('project_code') or '').strip()
        project_name = (
            self.project_name
            or metadata.get('project_name')
            or self._derive_project_name(self.budget_name or metadata.get('budget_name'))
            or False
        )
        project_name = (project_name or '').strip()
        if not project_code and not project_name:
            return False

        domain = [('company_id', '=', company.id)]
        if project_code:
            domain.append(('code', '=', project_code))
        else:
            domain.append(('name', '=', project_name))

        project = project_model.search(domain, limit=1)
        values = {
            'code': project_code or self._make_code('PROY', project_name),
            'name': project_name or project_code,
            'partner_id': self.partner_id.id if self.partner_id else self._resolve_partner(metadata.get('partner_id')),
            'location': self.location or metadata.get('location') or False,
            'start_date': self.budget_date,
            'state': 'planning',
            'company_id': company.id,
            'description': self.note or False,
        }

        if project:
            project.write(values)
        else:
            project = project_model.create(values)

        return project

    def _get_or_create_budget(self, project, metadata):
        budget_model = self.env['geosis.budget']
        company = self.env.company
        file_stem = os.path.splitext(self.file_name or 'importacion')[0]
        budget_code = (
            (self.budget_code or metadata.get('budget_code') or '').strip()
            or self._make_code('PRES', file_stem)
        )
        
        # Limpieza de seguridad para evitar errores de integridad en el borrado (si existiera)
        self.env.cr.execute("UPDATE geosis_budget SET project_id = NULL WHERE code = %s", [budget_code])

        budget_name = (
            (self.budget_name or metadata.get('budget_name') or '').strip()
            or file_stem
        )

        budget = budget_model.search(
            [('company_id', '=', company.id), ('code', '=', budget_code)],
            limit=1,
        )

        values = {
            'code': budget_code,
            'name': budget_name,
            'partner_id': self.partner_id.id if self.partner_id else self._resolve_partner(metadata.get('partner_id')),
            'location': self.location or metadata.get('location') or False,
            'budget_date': self.budget_date,
            'description': self.note or False,
            'project_id': project.id if project else False,
            'company_id': company.id,
            'state': 'draft',
        }

        if budget:
            budget.write(values)
        else:
            budget = budget_model.create(values)

        return budget

    def _get_or_create_apu(self, workbook, line_data, apu_sheet_map, apu_cache):
        company = self.env.company
        apu_model = self.env['geosis.apu']
        code = line_data['code']

        if code in apu_cache:
            return apu_cache[code]

        apu = apu_model.search(
            [('company_id', '=', company.id), ('code', '=', code)],
            limit=1,
        )

        sheet_name = apu_sheet_map.get(code)
        if sheet_name:
            apu = self._import_apu_from_sheet(apu, code, workbook, sheet_name, line_data)
        elif not apu and self.create_missing_apus:
            apu = apu_model.create(
                {
                    'code': code,
                    'name': line_data['name'],
                    'uom_name': line_data['uom_name'] or 'Unit(s)',
                    'company_id': company.id,
                    'indirect_percent': 0.0,
                    'description': _('Creado automaticamente desde importacion Excel.'),
                }
            )

        apu_cache[code] = apu
        return apu

    def _import_apu_from_sheet(self, apu, code, workbook, sheet_name, line_data):
        company = self.env.company
        apu_lines = self._extract_apu_lines(workbook.get_sheet(sheet_name))

        if not apu:
            apu = self.env['geosis.apu'].create(
                {
                    'code': code,
                    'name': line_data['name'],
                    'uom_name': line_data['uom_name'] or 'Unit(s)',
                    'company_id': company.id,
                    'indirect_percent': 0.0,
                    'description': _('Importado desde hoja %s') % sheet_name,
                }
            )
        elif self.update_existing_apus:
            apu.write(
                {
                    'name': line_data['name'] or apu.name,
                    'uom_name': line_data['uom_name'] or apu.uom_name,
                    'description': _('Actualizado desde hoja %s') % sheet_name,
                }
            )
            apu.line_ids.unlink()

        if not apu_lines:
            return apu

        for index, resource_data in enumerate(apu_lines, start=1):
            resource = self._get_or_create_resource(resource_data)
            self.env['geosis.apu.line'].create(
                {
                    'apu_id': apu.id,
                    'sequence': index * 10,
                    'resource_id': resource.id,
                    'category': resource_data['category'],
                    'uom_name': resource_data['uom_name'],
                    'quantity': resource_data['quantity'],
                    'rate': resource_data['rate'],
                    'performance': resource_data['performance'],
                    'percentage': resource_data['percentage'],
                    'distance': resource_data['distance'],
                    'note': resource_data['note'] or False,
                }
            )

        apu._compute_totals()
        return apu

    def _extract_apu_lines(self, rows):
        header_index, header_map = self._detect_header(rows, APU_HEADER_ALIASES)
        if header_index is None:
            return []

        parsed_lines = []
        current_category = False
        blank_count = 0

        # Escaneamos desde la fila 0 para capturar categorías que estén arriba de la cabecera
        for raw_row in rows:
            # Intentar detectar si esta fila es una categoría (ej: "EQUIPOS")
            # Probamos en las primeras columnas
            row_text_joined = ' '.join([_cell_as_string(c) for c in raw_row[:3] if c])
            possible_category = self._map_category(row_text_joined)
            
            if possible_category:
                # Si encontramos una categoría y no parece una fila de datos (sin cantidades/precios)
                # la marcamos como la categoría actual
                row_vals = [_to_float(c) for c in raw_row if _to_float(c) > 0]
                if not row_vals:
                    current_category = possible_category
                    continue

            # Si aún no tenemos cabecera detectada para las columnas, no podemos procesar datos
            if not header_map:
                continue

            code = _cell_as_string(_value_at(raw_row, header_map.get('code')))
            name = _cell_as_string(_value_at(raw_row, header_map.get('name')))
            raw_category = _cell_as_string(_value_at(raw_row, header_map.get('category')))
            uom_name = _cell_as_string(_value_at(raw_row, header_map.get('uom_name')))
            quantity = _to_float(_value_at(raw_row, header_map.get('quantity')), default=0.0)
            rate = _to_float(_value_at(raw_row, header_map.get('rate')), default=0.0)
            performance = _to_float(_value_at(raw_row, header_map.get('performance')), default=1.0)
            total_cost = _to_float(_value_at(raw_row, header_map.get('cost')), default=0.0)
            percentage = _to_float(_value_at(raw_row, header_map.get('percentage')), default=0.0)
            distance = _to_float(_value_at(raw_row, header_map.get('distance')), default=0.0)
            note = _cell_as_string(_value_at(raw_row, header_map.get('note')))

            if not code and not name and not quantity and not rate and not total_cost:
                blank_count += 1
                if blank_count >= 5:
                    break
                continue

            blank_count = 0

            possible_category = self._map_category(raw_category or name)
            if possible_category and not quantity and not rate and not total_cost and not code:
                current_category = possible_category
                continue

            if not name:
                continue

            category = self._map_category(raw_category) or current_category or self._infer_category_from_code(code) or 'O'
            code = code or self._make_resource_code(name, category)

            if not rate and quantity and total_cost:
                rate = total_cost / quantity
            elif not total_cost and quantity and rate:
                total_cost = (quantity * rate) / (performance or 1.0)

            parsed_lines.append(
                {
                    'code': code,
                    'name': name,
                    'category': category,
                    'uom_name': uom_name or 'Unit(s)',
                    'quantity': quantity or 1.0,
                    'rate': rate or total_cost or 0.0,
                    'performance': performance or 1.0,
                    'percentage': percentage or 0.0,
                    'distance': distance or 0.0,
                    'note': note or False,
                }
            )

        return parsed_lines

    def _get_or_create_resource(self, resource_data):
        resource = self.env['geosis.resource'].search([('code', '=', resource_data['code'])], limit=1)
        uom = self._resolve_uom(resource_data['uom_name'])
        values = {
            'code': resource_data['code'],
            'name': resource_data['name'],
            'category': resource_data['category'],
            'uom_id': uom.id,
            'price': resource_data['rate'],
            'description': resource_data.get('note') or False,
            'active': True,
        }

        if resource:
            resource.write(values)
        else:
            resource = self.env['geosis.resource'].create(values)

        return resource

    def _detect_header(self, rows, aliases):
        for row_index, row in enumerate(rows[:25]):
            header_map = {}
            for column_index, cell_value in enumerate(row):
                normalized = _normalize_text(cell_value)
                if not normalized:
                    continue
                for field_name, field_aliases in aliases.items():
                    if field_name in header_map:
                        continue
                    if any(alias in normalized for alias in field_aliases):
                        header_map[field_name] = column_index
                        break

            if 'name' in header_map and (
                'quantity' in header_map or 'unit_price' in header_map or 'rate' in header_map
            ):
                return row_index, header_map

        return None, {}

    def _resolve_uom(self, raw_uom_name):
        uom_model = self.env['uom.uom']
        name = _normalize_text(raw_uom_name)
        if not name:
            return self.env.ref('uom.product_uom_unit')

        candidates = list(UOM_ALIASES.get(name, ())) + [raw_uom_name]
        for candidate in candidates:
            if not candidate:
                continue
            uom = uom_model.search([('name', '=', candidate)], limit=1)
            if uom:
                return uom

        for candidate in candidates:
            if not candidate:
                continue
            uom = uom_model.search([('name', 'ilike', candidate)], limit=1)
            if uom:
                return uom

        return self.env.ref('uom.product_uom_unit')

    def _map_category(self, raw_value):
        normalized = _normalize_text(raw_value)
        if not normalized:
            return False

        for category_code, aliases in CATEGORY_LABELS.items():
            # Buscamos coincidencia exacta o que empiece con la palabra clave
            # para evitar confundirnos con "subtotal de..." o "rendimiento de..."
            for alias in aliases:
                if normalized == alias or normalized.startswith(alias + ' '):
                    return category_code
        return False

    def _infer_category_from_code(self, code):
        normalized = _normalize_text(code)
        if normalized.startswith('mo'):
            return 'N'
        if normalized.startswith('eq'):
            return 'M'
        if normalized.startswith('tr'):
            return 'P'
        if normalized.startswith('ma'):
            return 'O'
        return False

    def _make_code(self, prefix, seed):
        slug = re.sub(r'[^A-Z0-9]+', '-', (seed or '').upper()).strip('-')
        slug = slug[:30] or fields.Date.today().strftime('%Y%m%d')
        return '%s-%s' % (prefix, slug)

    def _make_resource_code(self, name, category):
        prefix_map = {'M': 'EQ', 'N': 'MO', 'O': 'MA', 'P': 'TR'}
        base_code = '%s-%s' % (
            prefix_map.get(category, 'RE'),
            re.sub(r'[^A-Z0-9]+', '', (name or '').upper())[:10] or 'AUTO',
        )

        resource_model = self.env['geosis.resource']
        code = base_code
        counter = 1
        while resource_model.search_count([('code', '=', code)]):
            counter += 1
            code = '%s-%02d' % (base_code[:20], counter)
        return code


class GeosisSimpleXlsxReader:
    def __init__(self, file_bytes):
        self._sheets = {}
        self._sheet_names = []
        self._load(file_bytes)

    @property
    def sheet_names(self):
        return list(self._sheet_names)

    def get_sheet(self, sheet_name):
        return self._sheets.get(sheet_name, [])

    def _load(self, file_bytes):
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            shared_strings = self._load_shared_strings(archive)
            relationships = self._load_relationships(archive)
            workbook_root = ET.fromstring(archive.read('xl/workbook.xml'))

            for sheet in workbook_root.findall('main:sheets/main:sheet', XLSX_NS):
                name = sheet.attrib.get('name')
                rel_id = sheet.attrib.get('{%s}id' % XLSX_NS['rel'])
                target = relationships.get(rel_id)
                if not name or not target:
                    continue

                sheet_path = self._resolve_sheet_path(target)
                rows = self._load_sheet_rows(archive, sheet_path, shared_strings)
                self._sheet_names.append(name)
                self._sheets[name] = rows

    def _load_shared_strings(self, archive):
        if 'xl/sharedStrings.xml' not in archive.namelist():
            return []

        root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
        values = []
        for string_item in root.findall('main:si', XLSX_NS):
            text_parts = []
            for text_node in string_item.findall('.//main:t', XLSX_NS):
                text_parts.append(text_node.text or '')
            values.append(''.join(text_parts))
        return values

    def _load_relationships(self, archive):
        root = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        relationships = {}
        for relation in root.findall('pkg:Relationship', XLSX_NS):
            relation_id = relation.attrib.get('Id')
            target = relation.attrib.get('Target')
            if relation_id and target:
                relationships[relation_id] = target
        return relationships

    def _resolve_sheet_path(self, target):
        clean_target = target.lstrip('/')
        if clean_target.startswith('xl/'):
            return clean_target
        return 'xl/%s' % clean_target

    def _load_sheet_rows(self, archive, sheet_path, shared_strings):
        root = ET.fromstring(archive.read(sheet_path))
        rows = []

        for row_node in root.findall('.//main:sheetData/main:row', XLSX_NS):
            row_values = {}
            max_index = -1

            for cell in row_node.findall('main:c', XLSX_NS):
                column_index = _column_to_index(cell.attrib.get('r', 'A1'))
                cell_type = cell.attrib.get('t')
                value = self._extract_cell_value(cell, cell_type, shared_strings)
                row_values[column_index] = value
                max_index = max(max_index, column_index)

            if max_index < 0:
                rows.append([])
                continue

            row = [False] * (max_index + 1)
            for column_index, value in row_values.items():
                row[column_index] = value
            rows.append(row)

        return rows

    def _extract_cell_value(self, cell, cell_type, shared_strings):
        if cell_type == 'inlineStr':
            inline = cell.find('main:is/main:t', XLSX_NS)
            return inline.text if inline is not None else False

        value_node = cell.find('main:v', XLSX_NS)
        raw_value = value_node.text if value_node is not None else False
        if raw_value is False:
            return False

        if cell_type == 's':
            try:
                return shared_strings[int(raw_value)]
            except (ValueError, IndexError):
                return raw_value

        if cell_type == 'b':
            return raw_value == '1'

        return raw_value


def _normalize_text(value):
    text = _cell_as_string(value).lower()
    text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    text = text.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return ' '.join(text.split())


def _cell_as_string(value):
    if value in (False, None):
        return ''
    return str(value).strip()


def _value_at(row, index):
    if index is None or index >= len(row):
        return False
    return row[index]


def _to_float(value, default=0.0):
    if value in (False, None, ''):
        return default

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace('$', '').replace('%', '').replace(' ', '')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace(',', '.')

    try:
        return float(text)
    except ValueError:
        return default


def _column_to_index(cell_ref):
    letters = ''.join(ch for ch in cell_ref if ch.isalpha()).upper()
    index = 0
    for letter in letters:
        index = (index * 26) + (ord(letter) - 64)
    return max(index - 1, 0)
