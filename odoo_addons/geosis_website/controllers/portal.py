# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv import expression
import base64

class GeosisCustomerPortal(CustomerPortal):
    def _parse_portal_float(self, value, default=0.0):
        if value in (None, False, ''):
            return default
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(' ', '')
        if ',' in text and '.' not in text:
            text = text.replace(',', '.')
        elif ',' in text and '.' in text:
            text = text.replace(',', '')

        return float(text)

    def _build_tasks_with_gantt(self, project_tasks):
        tasks_with_gantt = []
        if not project_tasks:
            return tasks_with_gantt

        all_dates = [self._get_task_start(t) for t in project_tasks if self._get_task_start(t)] + \
                    [self._get_task_end(t) for t in project_tasks if self._get_task_end(t)]
        if not all_dates:
            return tasks_with_gantt

        min_date = min(all_dates)
        max_date = max(all_dates)
        total_days = max((max_date - min_date).days, 1)

        for task in project_tasks:
            start_dt = self._get_task_start(task)
            end_dt = self._get_task_end(task)
            left = 0
            width = 0
            if start_dt and end_dt:
                left = ((start_dt - min_date).days / total_days) * 100
                width = (max((end_dt - start_dt).days, 1) / total_days) * 100

            tasks_with_gantt.append({
                'task': task,
                'left': left,
                'width': width,
                'start_dt': start_dt,
                'end_dt': end_dt,
            })

        return tasks_with_gantt

    def _get_accessible_project(self, project_id):
        Project = request.env['geosis.project'].sudo()
        project = Project.browse(project_id)
        if not project.exists():
            return Project

        # Primero intentamos con el mismo dominio del catalogo.
        project_from_domain = Project.search(
            [('id', '=', project_id)] + self._partner_domain(),
            limit=1,
        )
        if project_from_domain:
            return project_from_domain

        # Fallback defensivo: algunos registros quedan vinculados al mismo
        # partner comercial pero no responden igual al child_of en todos los
        # entornos. Si coincide el partner comercial, permitimos abrirlo.
        user_commercial = request.env.user.partner_id.commercial_partner_id
        project_partner = project.partner_id.commercial_partner_id
        if project_partner and project_partner.id == user_commercial.id:
            return project

        return Project

    def _get_project_budget_context(self, project):
        budgets = project.budget_ids.sorted(
            key=lambda b: (
                b.state != 'draft',
                -(b.budget_date.toordinal() if b.budget_date else 0),
                -b.id,
            )
        )
        primary_budget = budgets[:1]
        odoo_projects = budgets.mapped('odoo_project_id').filtered(lambda p: p.exists())
        return budgets, primary_budget, odoo_projects

    def _get_task_start(self, task):
        return (
            getattr(task, 'planned_date_start', False)
            or getattr(task, 'date_assign', False)
            or getattr(task, 'create_date', False)
        )

    def _get_task_end(self, task):
        return (
            getattr(task, 'planned_date_end', False)
            or getattr(task, 'date_end', False)
            or getattr(task, 'date_deadline', False)
            or self._get_task_start(task)
        )

    def _get_open_task_domain(self):
        stage_fields = request.env['project.task.type']._fields
        if 'is_closed' in stage_fields:
            return [('stage_id.is_closed', '=', False)]
        if 'fold' in stage_fields:
            return [('stage_id.fold', '=', False)]
        return []

    def _prepare_home_portal_values(self, counters):
        values = super(GeosisCustomerPortal, self)._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        Project = request.env['geosis.project'].sudo()
        domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]
        
        if 'project_count' in counters:
            values['project_count'] = Project.search_count(domain)
        return values

    def _partner_domain(self):
        return [('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)]

    @http.route(['/geosis/dashboard'], type='http', auth="user", website=True)
    def geosis_private_dashboard(self, **kw):
        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        Apu = request.env['geosis.apu'].sudo()
        Resource = request.env['geosis.resource'].sudo()
        
        latest_projects = Project.search(partner_domain, limit=5, order='write_date desc')
        
        # Estadisticas de recursos
        res_stats = {}
        for cat in ['M', 'N', 'O', 'P']:
            resources = Resource.search([('category', '=', cat)])
            res_stats[cat] = {
                'count': len(resources),
                'avg': sum(resources.mapped('price')) / len(resources) if resources else 0.0
            }

        # Tareas críticas totales (de todos los proyectos del cliente)
        all_client_projects = Project.search(partner_domain)
        all_budgets = request.env['geosis.budget'].sudo().search([('project_id', 'in', all_client_projects.ids)])
        all_odoo_projects = all_budgets.mapped('odoo_project_id')
        critical_task_domain = [
            ('project_id', 'in', all_odoo_projects.ids),
            ('is_critical', '=', True),
        ] + self._get_open_task_domain()
        critical_tasks = request.env['project.task'].sudo().search(
            critical_task_domain,
            limit=5,
            order='date_deadline asc',
        )

        # Datos para gráfico de pastel (Distribución de Costos Global)
        cost_dist = {
            'M': sum(Resource.search([('category', '=', 'M')]).mapped('price')),
            'N': sum(Resource.search([('category', '=', 'N')]).mapped('price')),
            'O': sum(Resource.search([('category', '=', 'O')]).mapped('price')),
            'P': sum(Resource.search([('category', '=', 'P')]).mapped('price')),
        }

        values = {
            'project_count': Project.search_count(partner_domain),
            'active_project_count': Project.search_count([*partner_domain, ('state', '=', 'active')]),
            'apu_count': Apu.search_count([('active', '=', True)]),
            'resource_count': Resource.search_count([('active', '=', True)]),
            'latest_projects': latest_projects,
            'res_stats': res_stats,
            'critical_tasks': critical_tasks,
            'cost_dist': cost_dist,
            'page_name': 'home',
        }
        return request.render("geosis_website.geosis_private_dashboard_page", values)

    @http.route(['/my/profile'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_profile(self, **kw):
        partner = request.env.user.partner_id
        values = {
            'page_name': 'profile',
            'countries': request.env['res.country'].sudo().search([]),
        }
        
        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'name': kw.get('name'),
                    'email': kw.get('email'),
                    'phone': kw.get('phone'),
                    'mobile': kw.get('mobile'),
                    'street': kw.get('street'),
                    'city': kw.get('city'),
                    'zip': kw.get('zip'),
                }
                if kw.get('country_id'):
                    vals['country_id'] = int(kw.get('country_id'))
                partner.sudo().write(vals)
                values['profile_updated'] = True
            except Exception as e:
                values['error_message'] = str(e)
        
        # Leer datos siempre al final para tener lo último de la DB
        partner_data = partner.read(['name', 'email', 'phone', 'mobile', 'street', 'city', 'zip', 'country_id'])[0]
        # Normalizar country_id para la comparación en el select de la plantilla
        if partner_data.get('country_id'):
            partner_data['country_id'] = partner_data['country_id'][0]
        values['form_data'] = partner_data
        return request.render("geosis_website.portal_my_profile", values)

    @http.route(['/my/projects', '/my/projects/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_projects(self, page=1, search=None, state='all', sort_by='date', **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['geosis.project'].sudo()
        domain = self._partner_domain()

        if search:
            domain += [('|', '|', ('name', 'ilike', search), ('code', 'ilike', search), ('location', 'ilike', search))]
        if state and state != 'all':
            domain += [('state', '=', state)]

        sortings = {
            'date': {'label': 'Fecha Reciente', 'order': 'write_date desc'},
            'code': {'label': 'Código', 'order': 'code desc'},
            'name': {'label': 'Nombre', 'order': 'name asc'},
        }
        order = sortings.get(sort_by, sortings['date'])['order']

        project_count = Project.search_count(domain)
        pager = portal_pager(
            url="/my/projects",
            url_args={'search': search, 'state': state, 'sort_by': sort_by},
            total=project_count,
            page=page,
            step=10
        )
        projects = Project.search(domain, order=order, limit=10, offset=pager['offset'])
        all_projects = Project.search(domain)

        values.update({
            'projects': projects,
            'page_name': 'project',
            'pager': pager,
            'search': search,
            'selected_state': state,
            'sort_by': sort_by,
            'sortings': sortings,
            'project_total_count': project_count,
            'project_total_amount': sum(all_projects.mapped('total_budget_amount')),
            'project_active_count': Project.search_count(domain + [('active', '=', True)]),
            'project_planning_count': Project.search_count(domain + [('state', '=', 'planning')]),
            'error_reason': kw.get('error'),
        })
        return request.render("geosis_website.portal_my_projects", values)

    @http.route(['/my/bitacoras', '/my/bitacoras/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_bitacoras(self, page=1, search=None, sort_by='date', **kw):
        values = self._prepare_portal_layout_values()
        Bitacora = request.env['geosis.bitacora'].sudo()
        domain = self._partner_domain()
        
        project_ids = request.env['geosis.project'].sudo().search(domain).ids
        bitacora_domain = [('project_id', 'in', project_ids)]

        if search:
            bitacora_domain += [('|', '|', 
                ('project_id.name', 'ilike', search), 
                ('content', 'ilike', search),
                ('personal_notes', 'ilike', search)
            )]

        sortings = {
            'date': {'label': 'Fecha Reciente', 'order': 'date desc, id desc'},
            'project': {'label': 'Proyecto', 'order': 'project_id asc'},
        }
        order = sortings.get(sort_by, sortings['date'])['order']

        bitacora_count = Bitacora.search_count(bitacora_domain)
        pager = portal_pager(
            url="/my/bitacoras",
            url_args={'search': search, 'sort_by': sort_by},
            total=bitacora_count,
            page=page,
            step=10
        )
        bitacoras = Bitacora.search(bitacora_domain, order=order, limit=10, offset=pager['offset'])

        # Calcular métricas para el Dashboard superior
        all_bitacoras = Bitacora.search([('project_id', 'in', project_ids)])
        total_days = len(all_bitacoras)
        approved_count = len(all_bitacoras.filtered(lambda b: b.state == 'approved'))
        rainy_days = len(all_bitacoras.filtered(lambda b: b.weather in ('rainy', 'storm')))
        productive_days = len(all_bitacoras.filtered(lambda b: b.weather in ('sunny', 'cloudy')))

        values.update({
            'bitacoras': bitacoras,
            'page_name': 'bitacora',
            'pager': pager,
            'search': search,
            'sort_by': sort_by,
            'sortings': sortings,
            'page_title': 'Libro de Obra',
            'page_subtitle': 'Registro diario y control de incidencias en obra',
            'dashboard_metrics': {
                'total_days': total_days,
                'approved_count': approved_count,
                'rainy_days': rainy_days,
                'productive_days': productive_days,
            }
        })
        return request.render("geosis_website.portal_my_bitacoras", values)

    @http.route(['/my/bitacora/<int:bitacora_id>'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_bitacora_detail(self, bitacora_id, **kw):
        Bitacora = request.env['geosis.bitacora'].sudo()
        bitacora = Bitacora.browse(bitacora_id)
        if not bitacora.exists():
            return request.redirect('/my/bitacoras')

        domain = self._partner_domain()
        project_ids = request.env['geosis.project'].sudo().search(domain).ids
        if bitacora.project_id.id not in project_ids:
            return request.redirect('/my/bitacoras')

        # Procesar Guardado e Instrucciones del Fiscalizador
        if request.httprequest.method == 'POST':
            vals = {}
            if 'inspector_instructions' in kw:
                vals['inspector_instructions'] = kw.get('inspector_instructions')
            
            signature_data = kw.get('signature_inspector')
            if signature_data and signature_data.startswith('data:image/png;base64,'):
                base64_str = signature_data.split(',')[1]
                vals['signature_inspector'] = base64_str
                vals['state'] = 'approved'
            
            if vals:
                bitacora.write(vals)

        values = self._prepare_portal_layout_values()
        values.update({
            'bitacora': bitacora,
            'page_name': 'bitacora',
            'page_title': 'Detalle de Libro de Obra',
            'page_subtitle': f"{bitacora.project_id.name} - Fecha: {bitacora.date}",
        })
        return request.render("geosis_website.portal_my_bitacora_detail", values)

    @http.route(['/my/bitacora/print/<int:bitacora_id>'], type='http', auth="user", website=True)
    def portal_my_bitacora_print(self, bitacora_id, **kw):
        Bitacora = request.env['geosis.bitacora'].sudo()
        bitacora = Bitacora.browse(bitacora_id)
        if not bitacora.exists():
            return request.redirect('/my/bitacoras')

        domain = self._partner_domain()
        project_ids = request.env['geosis.project'].sudo().search(domain).ids
        if bitacora.project_id.id not in project_ids:
            return request.redirect('/my/bitacoras')

        # Generar el PDF oficial del libro de obra con el motor QWeb PDF
        pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'geosis_mobile.action_report_geosis_bitacora', [bitacora_id]
        )
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'attachment; filename="Libro_de_Obra_Dia_{bitacora.date}.pdf"')
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route(['/my/gantt'], type='http', auth="user", website=True)
    def portal_my_gantt(self, project_id=None, **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['geosis.project'].sudo()
        Task = request.env['project.task'].sudo()

        projects = Project.search(
            self._partner_domain(),
            order='write_date desc, id desc',
        )
        selected_project = Project.browse()

        if project_id:
            try:
                selected_project = self._get_accessible_project(int(project_id))
            except (TypeError, ValueError):
                selected_project = Project.browse()

        if not selected_project:
            for candidate in projects:
                budgets, _, odoo_projects = self._get_project_budget_context(candidate)
                if odoo_projects:
                    selected_project = candidate
                    break

        if not selected_project and projects:
            selected_project = projects[:1]

        budgets = request.env['geosis.budget'].sudo()
        odoo_projects = request.env['project.project'].sudo()
        selected_odoo_project = request.env['project.project'].sudo().browse()
        project_tasks = Task.browse()
        tasks_with_gantt = []

        if selected_project:
            budgets, _, odoo_projects = self._get_project_budget_context(selected_project)
            selected_odoo_project = budgets.mapped('odoo_project_id')[:1]
            if odoo_projects:
                project_tasks = Task.search(
                    [('project_id', 'in', odoo_projects.ids)],
                    order='priority desc, planned_date_start asc, date_deadline asc, id asc',
                )
                tasks_with_gantt = self._build_tasks_with_gantt(project_tasks)

        open_task_count = 0
        critical_task_count = 0
        task_durations = {}
        if project_tasks:
            open_task_count = Task.search_count(
                [('id', 'in', project_tasks.ids)] + self._get_open_task_domain()
            )
            if 'is_critical' in Task._fields:
                critical_task_count = Task.search_count(
                    [('id', 'in', project_tasks.ids), ('is_critical', '=', True)]
                )
            for task in project_tasks:
                start_dt = self._get_task_start(task)
                end_dt = self._get_task_end(task)
                if start_dt and end_dt:
                    sd = start_dt.date() if hasattr(start_dt, 'date') else start_dt
                    ed = end_dt.date() if hasattr(end_dt, 'date') else end_dt
                    task_durations[task.id] = max((ed - sd).days, 0) + 1
                else:
                    task_durations[task.id] = 0

        values.update({
            'page_name': 'gantt',
            'page_title': 'Cronograma (Gantt)',
            'page_subtitle': 'Tareas generadas desde las fechas del presupuesto',
            'projects': projects,
            'selected_project': selected_project,
            'selected_odoo_project': selected_odoo_project,
            'budgets': budgets,
            'odoo_projects': odoo_projects,
            'project_tasks': project_tasks,
            'tasks_with_gantt': tasks_with_gantt,
            'task_durations': task_durations,
            'gantt_task_count': len(project_tasks),
            'gantt_open_count': open_task_count,
            'gantt_critical_count': critical_task_count,
            'gantt_scheduled_count': len(tasks_with_gantt),
        })
        return request.render("geosis_website.portal_my_gantt", values)

    @http.route(['/my/projects/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_project_new(self, **kw):
        values = {
            'page_name': 'project',
            'form_mode': 'create',
            'form_action': '/my/projects/new',
            'form_data': {
                'state': 'planning',
                'start_date': fields.Date.context_today(request.env.user),
                'active': True,
            },
        }
        if request.httprequest.method == 'POST':
            try:
                Project = request.env['geosis.project'].sudo()
                vals = {
                    'name': kw.get('name'),
                    'code': kw.get('code') or Project._get_next_project_code(),
                    'location': kw.get('location'),
                    'latitude': float(kw.get('latitude') or 0.0),
                    'longitude': float(kw.get('longitude') or 0.0),
                    'state': kw.get('state', 'planning'),
                    'partner_id': request.env.user.partner_id.commercial_partner_id.id,
                    'description': kw.get('description'),
                    'active': bool(kw.get('active')),
                }
                if kw.get('start_date'):
                    vals['start_date'] = kw.get('start_date')
                if kw.get('end_date'):
                    vals['end_date'] = kw.get('end_date')
                
                new_project = Project.create(vals)
                return request.redirect('/my/project/%s?success=created' % new_project.id)
            except Exception as e:
                values['error_message'] = str(e)
                values['form_data'] = kw
                
        return request.render("geosis_website.portal_project_form", values)

    @http.route(['/my/project/<int:project_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_project_edit(self, project_id, **kw):
        project = self._get_accessible_project(project_id)
        if not project:
            return request.redirect('/my/projects?error=project_access')

        values = {
            'page_name': 'project',
            'page_title': 'Editar Proyecto',
            'form_mode': 'edit',
            'form_action': '/my/project/%s/edit' % project.id,
            'form_data': {
                'code': project.code or '',
                'name': project.name or '',
                'location': project.location or '',
                'latitude': project.latitude or '',
                'longitude': project.longitude or '',
                'state': project.state or 'planning',
                'start_date': project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                'end_date': project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
                'description': project.description or '',
                'active': project.active,
            },
            'project_record': project,
        }

        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'name': kw.get('name'),
                    'location': kw.get('location'),
                    'latitude': float(kw.get('latitude') or 0.0),
                    'longitude': float(kw.get('longitude') or 0.0),
                    'state': kw.get('state', project.state),
                    'description': kw.get('description'),
                    'active': bool(kw.get('active')),
                }
                vals['start_date'] = kw.get('start_date') or False
                vals['end_date'] = kw.get('end_date') or False
                project.sudo().write(vals)
                return request.redirect('/my/project/%s?success=metadata_updated' % project.id)
            except Exception as e:
                values['error_message'] = str(e)
                values['form_data'] = kw

        return request.render("geosis_website.portal_project_form", values)

    @http.route(['/my/project/<int:project_id>'], type='http', auth="user", website=True)
    def portal_my_project_detail(self, project_id, **kw):
        project = self._get_accessible_project(project_id)
        if not project:
            return request.redirect('/my/projects?error=project_access')

        budgets, editable_budget, odoo_projects = self._get_project_budget_context(project)
        project_tasks = request.env['project.task'].sudo().search(
            [('project_id', 'in', odoo_projects.ids)],
            order='planned_date_start asc, date_deadline asc, id asc',
        )

        # Calcular datos para Gantt
        tasks_with_gantt = []
        if project_tasks:
            all_dates = [self._get_task_start(t) for t in project_tasks if self._get_task_start(t)] + \
                        [self._get_task_end(t) for t in project_tasks if self._get_task_end(t)]
            if all_dates:
                min_date = min(all_dates)
                max_date = max(all_dates)
                total_days = max((max_date - min_date).days, 1)
                
                for t in project_tasks:
                    start_dt = self._get_task_start(t)
                    end_dt = self._get_task_end(t)
                    left = 0
                    width = 0
                    if start_dt and end_dt:
                        left = ((start_dt - min_date).days / total_days) * 100
                        width = (max((end_dt - start_dt).days, 1) / total_days) * 100
                    
                    tasks_with_gantt.append({
                        'task': t,
                        'left': left,
                        'width': width,
                        'start_dt': start_dt,
                        'end_dt': end_dt,
                    })

        # Filtro inteligente de rubros por ubicacion
        apu_domain = [('active', '=', True)]
        if project.location:
            apu_domain += [('location', '=', project.location)]
        else:
            apu_domain += [('location', 'in', [False, ''])]

        values = {
            'project': project,
            'editable_budget': editable_budget,
            'budgets': budgets,
            'project_tasks': project_tasks,
            'tasks_with_gantt': tasks_with_gantt,
            'available_apus': request.env['geosis.apu'].sudo().search(apu_domain, order='name asc'),
            'page_name': 'project',
            'page_title': project.name,
            'success': kw.get('success'),
            'project_created': kw.get('success') == 'created',
            'budget_line_added': kw.get('success') == 'line_added',
            'budget_line_updated': kw.get('success') == 'line_updated',
            'budget_line_deleted': kw.get('success') == 'line_deleted',
            'last_activity': project.write_date,
            'last_budget_date': budgets[:1].budget_date if budgets else False,
        }
        return request.render("geosis_website.portal_my_project_detail", values)

    @http.route(['/my/project/<int:project_id>/update-metadata'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_project_update_metadata(self, project_id, **kw):
        project = request.env['geosis.project'].sudo().browse(project_id)
        if project.exists():
            try:
                vals = {
                    'state': kw.get('state', project.state),
                }
                if kw.get('start_date'):
                    vals['start_date'] = kw.get('start_date')
                if kw.get('end_date'):
                    vals['end_date'] = kw.get('end_date')
                project.sudo().write(vals)
            except Exception:
                pass
        return request.redirect('/my/project/%s?success=metadata_updated' % project_id)

    @http.route(['/my/budgets', '/my/budgets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_budgets(self, page=1, search=None, state='all', sort_by='date', **kw):
        values = self._prepare_portal_layout_values()
        Budget = request.env['geosis.budget'].sudo()
        
        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        my_projects = Project.search(partner_domain)
        
        domain = [('project_id', 'in', my_projects.ids)]
        if search:
            domain += [('|', ('code', 'ilike', search), ('name', 'ilike', search))]
        if state and state != 'all':
            domain += [('state', '=', state)]

        sortings = {
            'date': {'label': 'Fecha Reciente', 'order': 'write_date desc'},
            'code': {'label': 'Código', 'order': 'code desc'},
            'name': {'label': 'Nombre', 'order': 'name asc'},
        }
        order = sortings.get(sort_by, sortings['date'])['order']

        budget_count = Budget.search_count(domain)
        pager = portal_pager(
            url="/my/budgets",
            url_args={'search': search, 'state': state, 'sort_by': sort_by},
            total=budget_count,
            page=page,
            step=10
        )
        budgets = Budget.search(domain, order=order, limit=10, offset=pager['offset'])

        # Métricas para el strip superior
        all_my_budgets = Budget.search([('project_id', 'in', my_projects.ids)])

        values.update({
            'budgets': budgets,
            'page_name': 'budget',
            'pager': pager,
            'search': search,
            'selected_state': state,
            'sort_by': sort_by,
            'sortings': sortings,
            'budget_total_count': budget_count,
            'budget_draft_count': len(all_my_budgets.filtered(lambda b: b.state == 'draft')),
            'budget_approved_count': len(all_my_budgets.filtered(lambda b: b.state == 'approved')),
            'budget_total_amount_sum': sum(all_my_budgets.mapped('total_amount')),
        })
        return request.render("geosis_website.portal_my_budgets", values)

    @http.route(['/my/budgets/<int:budget_id>'], type='http', auth="user", website=True)
    def portal_my_budget_detail(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')

        partner_domain = self._partner_domain()
        my_projects = request.env['geosis.project'].sudo().search(partner_domain, order='name asc')
        partner_tree_domain = [('id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)]
        available_partners = request.env['res.partner'].sudo().search(partner_tree_domain, order='name asc')
        available_offerers = request.env['res.partner'].sudo().search([('active', '=', True)], order='name asc')
        values = {
            'budget': budget,
            'page_name': 'budget',
            'success': kw.get('success'),
            'available_apus': request.env['geosis.apu'].sudo().search([]),
            'available_odoo_projects': request.env['project.project'].sudo().search([], order='name asc'),
            'available_projects': my_projects,
            'available_partners': available_partners,
            'available_offerers': available_offerers,
            'selected_tab': kw.get('tab') or 'items',
            'polynomial_calculated': kw.get('polynomial_calculated'),
        }
        return request.render("geosis_website.portal_my_budget_detail", values)

    @http.route(['/my/budget/<int:budget_id>/update-metadata'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_update_metadata(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists():
            try:
                vals = {
                    'name': kw.get('name', budget.name),
                    'location': kw.get('location', budget.location),
                    'state': kw.get('state', budget.state),
                    'active': bool(kw.get('active')),
                    'indirect_percent': self._parse_portal_float(kw.get('indirect_percent'), budget.indirect_percent),
                    'iva_percent': self._parse_portal_float(kw.get('iva_percent'), budget.iva_percent),
                    'partner_id': int(kw.get('partner_id')) if kw.get('partner_id') else budget.partner_id.id,
                    'offerer_id': int(kw.get('offerer_id')) if kw.get('offerer_id') else budget.offerer_id.id,
                    'project_id': int(kw.get('project_id')) if kw.get('project_id') else budget.project_id.id,
                    'odoo_project_id': int(kw.get('odoo_project_id')) if kw.get('odoo_project_id') else False,
                    'description': kw.get('description', budget.description),
                }
                if kw.get('budget_date'):
                    vals['budget_date'] = kw.get('budget_date')
                budget.sudo().write(vals)
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/budgets/%s?success=metadata_updated' % budget_id)

    @http.route(['/my/budget/<int:budget_id>/line/<int:line_id>/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_update(self, budget_id, line_id, **kw):
        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if line.exists() and line.budget_id.id == budget_id:
            try:
                vals = {
                    'quantity': self._parse_portal_float(kw.get('quantity'), line.quantity),
                    'unit_price': self._parse_portal_float(kw.get('unit_price'), line.unit_price),
                    'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else line.chapter_id.id,
                    'note': kw.get('note', line.note),
                }
                vals['date_start'] = kw.get('date_start') or False
                vals['date_end'] = kw.get('date_end') or False
                line.sudo().write(vals)
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/budgets/%s?success=line_updated' % budget_id)

    @http.route(['/my/budget/<int:budget_id>/line/<int:line_id>/update-ajax'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_update_ajax(self, budget_id, line_id, **kw):
        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if not line.exists() or line.budget_id.id != budget_id:
            return request.make_json_response({'ok': False, 'message': 'Linea no encontrada'}, status=404)

        try:
            vals = {
                'quantity': self._parse_portal_float(kw.get('quantity'), line.quantity),
                'unit_price': self._parse_portal_float(kw.get('unit_price'), line.unit_price),
                'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else line.chapter_id.id,
                'note': kw.get('note', line.note),
                'date_start': kw.get('date_start') or False,
                'date_end': kw.get('date_end') or False,
            }
            line.sudo().write(vals)
            line.invalidate_recordset()
        except (ValueError, TypeError):
            return request.make_json_response({'ok': False, 'message': 'Datos invalidos'}, status=400)

        return request.make_json_response({
            'ok': True,
            'line_id': line.id,
            'duration': line.duration or 0,
            'subtotal': line.subtotal or 0.0,
            'date_start': line.date_start and line.date_start.strftime('%Y-%m-%d') or '',
            'date_end': line.date_end and line.date_end.strftime('%Y-%m-%d') or '',
            'note': line.note or '',
            'chapter_id': line.chapter_id.id or False,
        })

    @http.route(['/my/budget/<int:budget_id>/line/add'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_add(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists() and kw.get('apu_id'):
            apu = request.env['geosis.apu'].sudo().browse(int(kw.get('apu_id')))
            request.env['geosis.budget.line'].sudo().create({
                'budget_id': budget.id,
                'apu_id': apu.id,
                'quantity': self._parse_portal_float(kw.get('quantity'), 1.0),
                'unit_price': self._parse_portal_float(kw.get('unit_price'), apu.total_cost),
                'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else False,
                'date_start': kw.get('date_start') or False,
                'date_end': kw.get('date_end') or False,
                'note': kw.get('note') or False,
            })
        return request.redirect('/my/budgets/%s?success=line_added' % budget_id)

    @http.route(['/my/budget/<int:budget_id>/line/<int:line_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_delete(self, budget_id, line_id, **kw):
        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if line.exists() and line.budget_id.id == budget_id:
            line.sudo().unlink()
        return request.redirect('/my/budgets/%s?success=line_deleted' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/create-odoo-project'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_create_odoo_project(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')
        project_vals = {
            'name': budget.project_id.name or budget.name or _('Cronograma de presupuesto'),
        }
        if 'partner_id' in request.env['project.project']._fields and budget.partner_id:
            project_vals['partner_id'] = budget.partner_id.id
        odoo_project = request.env['project.project'].sudo().create(project_vals)
        budget.sudo().write({'odoo_project_id': odoo_project.id})
        return request.redirect('/my/budgets/%s?success=odoo_project_created' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/chapter/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_chapter_create(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists() and kw.get('name'):
            request.env['geosis.budget.chapter'].sudo().create({
                'budget_id': budget.id,
                'name': kw.get('name'),
                'parent_id': int(kw.get('parent_id')) if kw.get('parent_id') else False
            })
        return request.redirect('/my/budgets/%s?tab=chapters' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/line/<int:line_id>/move'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_move_chapter(self, budget_id, line_id, **kw):
        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if line.exists() and line.budget_id.id == budget_id:
            line.write({'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else False})
        return request.redirect('/my/budgets/%s?line_moved=1' % budget_id)

    @http.route(['/my/projects/<int:project_id>/task/<int:task_id>/predecessor'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_project_task_update_predecessor(self, project_id, task_id, **kw):
        project = self._get_accessible_project(project_id)
        if not project:
            return request.redirect('/my/projects')

        task = request.env['project.task'].sudo().browse(task_id)
        _, _, odoo_projects = self._get_project_budget_context(project)
        if task.exists() and task.project_id.id in odoo_projects.ids:
            predecessor_id = int(kw.get('predecessor_id')) if kw.get('predecessor_id') else False
            if predecessor_id:
                task.write({'depend_on_ids': [(6, 0, [predecessor_id])]})
            else:
                task.write({'depend_on_ids': [(5, 0, 0)]})
            # Recalcular ruta crítica
            task.action_calculate_critical_path()
        return request.redirect('/my/project/%s?tab=tasks' % project_id)

    @http.route(['/my/budgets/<int:budget_id>/duplicate'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_duplicate(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists():
            new_budget = budget.copy({
                'name': _("%s (Copia)") % budget.name,
                'code': budget.code + "-COPY",
                'state': 'draft'
            })
            return request.redirect('/my/budgets/%s?success=duplicated' % new_budget.id)
        return request.redirect('/my/projects')

    @http.route(['/my/rubro/<int:apu_id>/duplicate'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_duplicate(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            new_apu = apu.copy({
                'name': _("%s (Copia)") % apu.name,
                'code': apu.code + "-C"
            })
            return request.redirect('/my/rubro/%s?success=duplicated' % new_apu.id)
        return request.redirect('/my/rubros')

    @http.route(['/my/budgets/<int:budget_id>/generate-schedule'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_generate_schedule(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')
        try:
            created_project = False
            if not budget.odoo_project_id:
                project_vals = {
                    'name': budget.project_id.name or budget.name or _('Cronograma de presupuesto'),
                }
                if 'partner_id' in request.env['project.project']._fields and budget.partner_id:
                    project_vals['partner_id'] = budget.partner_id.id
                odoo_project = request.env['project.project'].sudo().create(project_vals)
                budget.sudo().write({'odoo_project_id': odoo_project.id})
                created_project = True
            budget.action_create_schedule_tasks()
            success_key = 'schedule_generated_with_project' if created_project else 'schedule_generated'
            return request.redirect('/my/budgets/%s?success=%s&tab=items' % (budget.id, success_key))
        except Exception as e:
            return request.redirect('/my/budgets/%s?error=%s&tab=items' % (budget_id, str(e)))

    @http.route(['/my/budgets/<int:budget_id>/pdf'], type='http', auth="user", website=True)
    def portal_my_budget_report_pdf(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')
        
        # Usar el reporte de APUs por defecto o permitir elegir mediante kw
        report_type = kw.get('type', 'apus')
        report_ref = 'geosis_presupuesto.action_report_geosis_budget_apus'
        if report_type == 'summary':
            report_ref = 'geosis_presupuesto.action_report_geosis_budget_summary'
        elif report_type == 'resources':
            report_ref = 'geosis_presupuesto.action_report_geosis_budget_resources'
            
        pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report_ref,
            res_ids=[budget.id],
        )
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'attachment; filename="Presupuesto_%s.pdf"' % budget.code)
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route(['/my/rubros/<int:apu_id>/pdf'], type='http', auth="user", website=True)
    def portal_my_rubro_pdf(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if not apu.exists():
            return request.redirect('/my/rubros')
            
        pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'geosis_apu.action_report_geosis_apu',
            res_ids=[apu.id],
        )
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'attachment; filename="APU_%s.pdf"' % apu.code)
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route(['/my/budgets/<int:budget_id>/approve'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_approve(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists() and budget.state == 'draft':
            budget.sudo().write({'state': 'approved'})
        return request.redirect('/my/budgets/%s?success=approved' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/chapter/<int:chapter_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_chapter_delete(self, budget_id, chapter_id, **kw):
        chapter = request.env['geosis.budget.chapter'].sudo().browse(chapter_id)
        if chapter.exists() and chapter.budget_id.id == budget_id:
            chapter.sudo().unlink()
        return request.redirect('/my/budgets/%s?tab=chapters' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/calculate-polynomial'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_calculate_polynomial(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')
        try:
            budget.action_calculate_polynomial()
            return request.redirect('/my/budgets/%s?polynomial_calculated=1' % budget_id)
        except Exception as e:
            return request.redirect('/my/budgets/%s?error=%s' % (budget_id, str(e)))

    @http.route(['/my/budgets/<int:budget_id>/msproject'], type='http', auth="user", website=True)
    def portal_my_budget_msproject(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/budgets')
        wizard = request.env['geosis.budget.export.msproject'].sudo().create({'budget_id': budget.id})
        wizard.action_export()
        xml_data = base64.b64decode(wizard.file_data or b'')
        filename = "Proyecto_%s.xml" % budget.code
        return request.make_response(xml_data, [
            ('Content-Type', 'application/xml'),
            ('Content-Disposition', 'attachment; filename="%s";' % filename)
        ])

    @http.route(['/my/rubro/<int:apu_id>/line/<int:line_id>/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_line_update(self, apu_id, line_id, **kw):
        line = request.env['geosis.apu.line'].sudo().browse(line_id)
        if line.exists() and line.apu_id.id == apu_id:
            line.write({
                'quantity': float(kw.get('quantity', line.quantity)),
                'performance': float(kw.get('performance', line.performance)),
                'rate': float(kw.get('rate', line.rate)),
                'percentage': float(kw.get('percentage', line.percentage)),
                'distance': float(kw.get('distance', line.distance)),
                'note': kw.get('note', line.note),
            })
        return request.redirect('/my/rubro/%s?line_updated=1' % apu_id)

    @http.route(['/my/rubro/<int:apu_id>/generate-ia'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_generate_ia(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        apu.action_generate_with_ia()
        return request.redirect('/my/rubro/%s?ia_generated=1' % apu_id)

    @http.route(['/my/rubros', '/my/rubros/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rubros(self, page=1, search=None, active='active', sort_by='name', location='all', **kw):
        Apu = request.env['geosis.apu'].sudo()
        domain = []
        if search:
            domain += [('|', '|', ('name', 'ilike', search), ('code', 'ilike', search), ('uom_name', 'ilike', search))]
        if active == 'active':
            domain += [('active', '=', True)]
        elif active == 'inactive':
            domain += [('active', '=', False)]
            
        if location and location != 'all':
            domain += [('location', '=', location)]

        sortings = {
            'name': {'label': 'Nombre A-Z', 'order': 'name asc'},
            'code': {'label': 'Código', 'order': 'code asc'},
            'cost': {'label': 'Costo mayor', 'order': 'total_cost desc'},
        }
        order = sortings.get(sort_by, sortings['name'])['order']
        rubro_count = Apu.search_count(domain)
        pager = portal_pager(
            url="/my/rubros",
            url_args={'search': search, 'active': active, 'sort_by': sort_by, 'location': location},
            total=rubro_count,
            page=page,
            step=20,
        )
        rubros = Apu.search(domain, order=order, limit=20, offset=pager['offset'])

        # Obtener ubicaciones únicas disponibles
        available_locations = Apu.read_group([], ['location'], ['location'])
        locations = [l['location'] for l in available_locations if l['location']]

        values = {
            'rubros': rubros,
            'page_name': 'rubro',
            'search': search,
            'selected_active': active,
            'selected_location': location,
            'locations': sorted(locations),
            'sort_by': sort_by,
            'sortings': sortings,
            'pager': pager,
            'rubro_total_count': Apu.search_count([]),
            'rubro_active_count': Apu.search_count([('active', '=', True)]),
            'rubro_inactive_count': Apu.search_count([('active', '=', False)]),
            'rubro_avg_total': sum(rubros.mapped('total_cost')) / len(rubros) if rubros else 0.0,
            'rubro_created': kw.get('success') == 'rubro_created',
            'rubro_updated': kw.get('success') == 'rubro_updated',
            'rubro_deleted': kw.get('success') == 'rubro_deleted',
        }
        return request.render("geosis_website.portal_my_rubros", values)

    @http.route(['/my/rubro/<int:apu_id>'], type='http', auth="user", website=True)
    def portal_my_rubro_detail(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if not apu.exists():
            return request.redirect('/my/rubros')
        resource_categories = {
            'M': {'label': 'Equipos', 'description': 'Herramientas y maquinaria pesada'},
            'N': {'label': 'Mano de Obra', 'description': 'Personal tecnico y obreros'},
            'O': {'label': 'Materiales', 'description': 'Suministros y materia prima'},
            'P': {'label': 'Transporte', 'description': 'Logistica y movilizacion'},
        }
        resource_domain = [('active', '=', True)]
        if apu.location:
            resource_domain += [('location', 'in', [apu.location, False, ''])]
        resource_available = request.env['geosis.resource'].sudo().search(resource_domain, order='category, name asc')

        resource_grouped_lines = {code: [] for code in resource_categories}
        resource_subtotals = {code: 0.0 for code in resource_categories}
        for line in apu.line_ids.sorted(lambda l: (l.sequence, l.id)):
            category = line.category or line.resource_id.category or 'O'
            resource_grouped_lines.setdefault(category, []).append(line)
            resource_subtotals[category] = resource_subtotals.get(category, 0.0) + (line.cost or 0.0)

        values = {
            'apu': apu,
            'page_name': 'rubro',
            'resource_categories': resource_categories,
            'success': kw.get('success'),
            'ia_generated': kw.get('ia_generated'),
            'resource_available': resource_available,
            'resource_grouped_lines': resource_grouped_lines,
            'resource_subtotals': resource_subtotals,
            'resource_direct_total': sum(apu.line_ids.mapped('cost')),
            'resource_line_added': kw.get('resource_line_added'),
            'resource_line_deleted': kw.get('resource_line_deleted'),
            'line_updated': kw.get('line_updated'),
            'rubro_created': kw.get('rubro_created'),
            'rubro_updated': kw.get('rubro_updated'),
        }
        return request.render("geosis_website.portal_my_rubro_detail", values)

    @http.route(['/my/rubro/<int:apu_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_rubro_edit(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if not apu.exists():
            return request.redirect('/my/rubros')
        values = {
            'apu': apu,
            'page_name': 'rubro',
            'form_data': apu.read(['code', 'name', 'uom_name', 'indirect_percent', 'cpc_code', 'description', 'active'])[0],
        }
        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'code': kw.get('code') or apu.code,
                    'name': kw.get('name'),
                    'uom_name': kw.get('uom_name'),
                    'indirect_percent': float(kw.get('indirect_percent', 0)),
                    'cpc_code': kw.get('cpc_code'),
                    'description': kw.get('description'),
                    'active': bool(kw.get('active')),
                }
                apu.sudo().write(vals)
                return request.redirect('/my/rubro/%s?rubro_updated=1' % apu.id)
            except Exception as e:
                values['error_message'] = str(e)
                values['form_data'].update(kw)
        
        return request.render("geosis_website.portal_rubro_form", values)

    @http.route(['/my/rubros/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_rubro_new(self, **kw):
        values = {
            'apu': None,
            'page_name': 'rubro',
            'form_data': {'uom_name': 'U', 'active': True},
        }
        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'code': kw.get('code') or False,
                    'name': kw.get('name'),
                    'uom_name': kw.get('uom_name'),
                    'indirect_percent': float(kw.get('indirect_percent', 0)),
                    'cpc_code': kw.get('cpc_code'),
                    'description': kw.get('description'),
                    'active': bool(kw.get('active')),
                }
                new_apu = request.env['geosis.apu'].sudo().create(vals)
                return request.redirect('/my/rubro/%s?rubro_created=1' % new_apu.id)
            except Exception as e:
                values['error_message'] = str(e)
                values['form_data'] = kw
                
        return request.render("geosis_website.portal_rubro_form", values)

    @http.route(['/my/rubro/<int:apu_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_delete(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            apu.sudo().unlink()
        return request.redirect('/my/rubros?success=rubro_deleted')

    @http.route(['/my/rubro/resource/add', '/my/rubro/<int:apu_id>/add-resource'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_resource_add(self, apu_id=None, **kw):
        apu_id = apu_id or int(kw.get('apu_id'))
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if not apu.exists():
            return request.redirect('/my/rubros')
        
        category = kw.get('category')
        resource = False
        
        Resource = request.env['geosis.resource'].sudo()
        if kw.get('resource_id'):
            resource = Resource.browse(int(kw.get('resource_id')))

        resource_name = kw.get('resource_name') or (resource.name if resource else False)
        if not resource:
            resource = Resource.create({
                'name': resource_name,
                'category': category,
                'uom_id': request.env.ref('uom.product_uom_unit').id,
                'price': float(kw.get('rate', 0)),
            })
            
        request.env['geosis.apu.line'].sudo().create({
            'apu_id': apu.id,
            'resource_id': resource.id,
            'category': category,
            'uom_name': kw.get('uom_name') or (resource.uom_id.name if resource.uom_id else False),
            'quantity': float(kw.get('quantity', 1.0)),
            'rate': float(kw.get('rate', resource.price)),
            'performance': float(kw.get('performance', 1.0)),
            'percentage': float(kw.get('percentage', 0.0)),
            'distance': float(kw.get('distance', 0.0)),
            'note': kw.get('note'),
        })
        
        return request.redirect('/my/rubro/%s?resource_line_added=1' % apu.id)

    @http.route(['/my/rubro/line/<int:line_id>/delete', '/my/rubro/<int:apu_id>/line/<int:line_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_line_delete(self, line_id, apu_id=None, **kw):
        line = request.env['geosis.apu.line'].sudo().browse(line_id)
        if line.exists():
            apu_id = line.apu_id.id
            line.sudo().unlink()
        return request.redirect('/my/rubro/%s?resource_line_deleted=1' % apu_id)

    @http.route(['/my/rubro/<int:apu_id>/generate-ia'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_generate_ia(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            apu.sudo().action_generate_with_ia()
        return request.redirect('/my/rubro/%s?ia_generated=1' % apu.id)

    @http.route(['/my/rubro/<int:apu_id>/update-indirects'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_update_indirects(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            try:
                new_indirect = float(kw.get('indirect_percent', apu.indirect_percent))
                apu.sudo().write({'indirect_percent': new_indirect})
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/rubros/%s?success=indirects_updated' % apu_id)

    @http.route(['/my/import-excel'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_import_excel(self, **kw):
        values = {
            'page_name': 'import',
            'form_data': kw or {},
        }
        if 'geosis.excel.import.wizard' not in request.env:
            values['error_message'] = (
                'El modulo de importacion Excel no esta instalado o no se ha actualizado en Odoo. '
                'Instala/actualiza `geosis_import_excel` antes de usar esta pantalla.'
            )
            return request.render("geosis_website.portal_import_excel", values)

        if request.httprequest.method == 'POST' and kw.get('file_data'):
            file_data = kw.get('file_data').read()
            file_name = kw.get('file_data').filename
            
            # Crear el wizard de importación con todos los parámetros del formulario
            wizard_vals = {
                'file_data': base64.b64encode(file_data),
                'file_name': file_name,
                'budget_code': kw.get('budget_code'),
                'budget_name': kw.get('budget_name'),
                'project_code': kw.get('project_code'),
                'project_name': kw.get('project_name'),
                'location': kw.get('location'),
                'latitude': float(kw.get('latitude') or 0.0),
                'longitude': float(kw.get('longitude') or 0.0),
                'note': kw.get('note'),
                'import_apu_sheets': True if kw.get('import_apu_sheets') else False,
                'create_missing_apus': True if kw.get('create_missing_apus') else False,
                'update_existing_apus': True if kw.get('update_existing_apus') else False,
                'replace_budget_lines': True if kw.get('replace_budget_lines') else False,
                'use_budget_sheet_prices': True if kw.get('use_budget_sheet_prices') else False,
                'partner_id': request.env.user.partner_id.commercial_partner_id.id,
            }
            if kw.get('budget_date'):
                wizard_vals['budget_date'] = kw.get('budget_date')

            try:
                wizard = request.env['geosis.excel.import.wizard'].sudo().create(wizard_vals)
                res = wizard.action_import_excel()
                if res and res.get('res_id'):
                    return request.redirect('/my/budgets/%s?success=imported' % res['res_id'])
            except Exception as e:
                values['error_message'] = str(e)

        return request.render("geosis_website.portal_import_excel", values)

    # -------------------------------------------------------
    # CATÁLOGO DE RECURSOS
    # -------------------------------------------------------

    @http.route(['/my/resources', '/my/resources/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_resources(self, page=1, search=None, category='all', sort_by='name', location='all', **kw):
        Resource = request.env['geosis.resource'].sudo()

        domain = [('active', '=', True)]
        if search:
            domain += ['|', '|',
                ('name', 'ilike', search),
                ('code', 'ilike', search),
                ('description', 'ilike', search),
            ]
        if category and category != 'all':
            domain += [('category', '=', category)]
            
        if location and location != 'all':
            domain += [('location', '=', location)]

        sortings = {
            'name':     {'label': 'Nombre A-Z',      'order': 'name asc'},
            'name_desc':{'label': 'Nombre Z-A',      'order': 'name desc'},
            'price':    {'label': 'Precio mayor',    'order': 'price desc'},
            'price_asc':{'label': 'Precio menor',    'order': 'price asc'},
            'category': {'label': 'Categoría',       'order': 'category, name'},
        }
        order = sortings.get(sort_by, sortings['name'])['order']

        resource_count = Resource.search_count(domain)
        pager = portal_pager(
            url='/my/resources',
            url_args={'search': search, 'category': category, 'sort_by': sort_by, 'location': location},
            total=resource_count,
            page=page,
            step=20,
        )
        resources = Resource.search(domain, order=order, limit=20, offset=pager['offset'])

        # Obtener ubicaciones únicas disponibles
        available_locations = Resource.read_group([], ['location'], ['location'])
        locations = [l['location'] for l in available_locations if l['location']]

        values = {
            'resources': resources,
            'resource_total_count': resource_count,
            'resource_equipment_count': Resource.search_count([('active', '=', True), ('category', '=', 'M')]),
            'resource_labor_count':     Resource.search_count([('active', '=', True), ('category', '=', 'N')]),
            'resource_material_count':  Resource.search_count([('active', '=', True), ('category', '=', 'O')]),
            'pager': pager,
            'search': search or '',
            'selected_category': category,
            'selected_location': location,
            'locations': sorted(locations),
            'sort_by': sort_by,
            'sortings': sortings,
            'page_name': 'resource',
            'success': kw.get('success'),
        }
        return request.render("geosis_website.portal_my_resources", values)

    @http.route(['/my/resources/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_resource_new(self, **kw):
        Resource = request.env['geosis.resource'].sudo()
        Uom = request.env['uom.uom'].sudo()
        Inec = request.env['geosis.inec.index'].sudo()

        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'code': kw.get('code') or False,
                    'name': kw.get('name'),
                    'category': kw.get('category') or 'O',
                    'uom_id': int(kw.get('uom_id')) if kw.get('uom_id') else False,
                    'price': float(kw.get('price', 0) or 0),
                    'cpc_code': kw.get('cpc_code') or False,
                    'vae_percent': float(kw.get('vae_percent', 0) or 0),
                    'inec_index_id': int(kw.get('inec_index_id')) if kw.get('inec_index_id') else False,
                    'location': kw.get('location') or False,
                    'description': kw.get('description') or False,
                    'active': True if kw.get('active') else False,
                }
                resource = Resource.create(vals)
                return request.redirect('/my/resources/%s?success=created' % resource.id)
            except Exception as exc:
                values = {
                    'page_name': 'resource',
                    'resource': False,
                    'form_data': kw,
                    'selected_uom_id': str(kw.get('uom_id') or ''),
                    'selected_inec_index_id': str(kw.get('inec_index_id') or ''),
                    'uoms': Uom.search([], order='name asc'),
                    'inec_indices': Inec.search([('active', '=', True)], order='code asc'),
                    'error_message': str(exc),
                }
                return request.render("geosis_website.portal_resource_form", values)

        values = {
            'page_name': 'resource',
            'resource': False,
            'form_data': {'category': 'O', 'price': 0.0, 'vae_percent': 0.0, 'active': True},
            'selected_uom_id': '',
            'selected_inec_index_id': '',
            'uoms': Uom.search([], order='name asc'),
            'inec_indices': Inec.search([('active', '=', True)], order='code asc'),
            'error_message': False,
        }
        return request.render("geosis_website.portal_resource_form", values)

    @http.route(['/my/resources/<int:resource_id>'], type='http', auth="user", website=True)
    def portal_my_resource_detail(self, resource_id, **kw):
        resource = request.env['geosis.resource'].sudo().browse(resource_id)
        if not resource.exists():
            return request.redirect('/my/resources')

        values = {
            'page_name': 'resource',
            'resource': resource,
            'success': kw.get('success'),
        }
        return request.render("geosis_website.portal_my_resource_detail", values)

    @http.route(['/my/resources/<int:resource_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_resource_edit(self, resource_id, **kw):
        resource = request.env['geosis.resource'].sudo().browse(resource_id)
        if not resource.exists():
            return request.redirect('/my/resources')

        Uom = request.env['uom.uom'].sudo()
        Inec = request.env['geosis.inec.index'].sudo()

        if request.httprequest.method == 'POST':
            try:
                resource.write({
                    'code': kw.get('code') or resource.code,
                    'name': kw.get('name'),
                    'category': kw.get('category') or resource.category or 'O',
                    'uom_id': int(kw.get('uom_id')) if kw.get('uom_id') else False,
                    'price': float(kw.get('price', resource.price) or 0),
                    'cpc_code': kw.get('cpc_code') or False,
                    'vae_percent': float(kw.get('vae_percent', resource.vae_percent) or 0),
                    'inec_index_id': int(kw.get('inec_index_id')) if kw.get('inec_index_id') else False,
                    'location': kw.get('location') or False,
                    'description': kw.get('description') or False,
                    'active': True if kw.get('active') else False,
                })
                return request.redirect('/my/resources/%s?success=updated' % resource.id)
            except Exception as exc:
                values = {
                    'page_name': 'resource',
                    'resource': resource,
                    'form_data': kw,
                    'selected_uom_id': str(kw.get('uom_id') or ''),
                    'selected_inec_index_id': str(kw.get('inec_index_id') or ''),
                    'uoms': Uom.search([], order='name asc'),
                    'inec_indices': Inec.search([('active', '=', True)], order='code asc'),
                    'error_message': str(exc),
                }
                return request.render("geosis_website.portal_resource_form", values)

        values = {
            'page_name': 'resource',
            'resource': resource,
            'form_data': resource.read([
                'code', 'name', 'category', 'uom_id', 'price', 'cpc_code',
                'vae_percent', 'inec_index_id', 'location', 'description', 'active'
            ])[0],
            'selected_uom_id': str(resource.uom_id.id or ''),
            'selected_inec_index_id': str(resource.inec_index_id.id or ''),
            'uoms': Uom.search([], order='name asc'),
            'inec_indices': Inec.search([('active', '=', True)], order='code asc'),
            'error_message': False,
        }
        return request.render("geosis_website.portal_resource_form", values)

    @http.route(['/my/resources/<int:resource_id>/update-price'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_resource_update_price(self, resource_id, **kw):
        resource = request.env['geosis.resource'].sudo().browse(resource_id)
        if resource.exists():
            try:
                new_price = float(kw.get('price', resource.price))
                resource.sudo().write({'price': new_price})
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/resources?success=price_updated')

    # -------------------------------------------------------
    # PLANILLAS DE AVANCE (FISCALIZACIÓN)
    # -------------------------------------------------------

    @http.route(['/my/inec-indices', '/my/inec-indices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inec_indices(self, page=1, search=None, status='active', sort_by='code', **kw):
        Index = request.env['geosis.inec.index'].sudo()
        Value = request.env['geosis.inec.index.value'].sudo()

        domain = []
        if search:
            domain += ['|', ('code', 'ilike', search), ('name', 'ilike', search)]
        if status == 'active':
            domain += [('active', '=', True)]
        elif status == 'inactive':
            domain += [('active', '=', False)]

        sortings = {
            'code': {'label': 'Codigo', 'order': 'code asc, name asc'},
            'name': {'label': 'Nombre A-Z', 'order': 'name asc'},
            'name_desc': {'label': 'Nombre Z-A', 'order': 'name desc'},
        }
        order = sortings.get(sort_by, sortings['code'])['order']

        total = Index.search_count(domain)
        pager = portal_pager(
            url='/my/inec-indices',
            url_args={'search': search, 'status': status, 'sort_by': sort_by},
            total=total,
            page=page,
            step=20,
        )
        indices = Index.search(domain, order=order, limit=20, offset=pager['offset'])

        values = {
            'page_name': 'inec',
            'indices': indices,
            'pager': pager,
            'search': search or '',
            'selected_status': status,
            'sort_by': sort_by,
            'sortings': sortings,
            'index_total_count': total,
            'index_active_count': Index.search_count([('active', '=', True)]),
            'index_inactive_count': Index.search_count([('active', '=', False)]),
            'index_value_total_count': Value.search_count([]),
            'success': kw.get('success'),
        }
        return request.render("geosis_website.portal_my_inec_indices", values)

    @http.route(['/my/inec-indices/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_inec_index_new(self, **kw):
        if request.httprequest.method == 'POST':
            try:
                index_record = request.env['geosis.inec.index'].sudo().create({
                    'code': kw.get('code') or False,
                    'name': kw.get('name'),
                    'active': True if kw.get('active') else False,
                })
                return request.redirect('/my/inec-indices/%s?success=created' % index_record.id)
            except Exception as exc:
                values = {
                    'page_name': 'inec',
                    'index_record': False,
                    'form_data': kw,
                    'current_year': fields.Date.today().year,
                    'error_message': str(exc),
                }
                return request.render("geosis_website.portal_inec_form", values)

        values = {
            'page_name': 'inec',
            'index_record': False,
            'form_data': {'active': True},
            'current_year': fields.Date.today().year,
            'error_message': False,
        }
        return request.render("geosis_website.portal_inec_form", values)

    @http.route(['/my/inec-indices/<int:index_id>'], type='http', auth="user", website=True)
    def portal_my_inec_index_detail(self, index_id, **kw):
        index_record = request.env['geosis.inec.index'].sudo().browse(index_id)
        if not index_record.exists():
            return request.redirect('/my/inec-indices')

        month_labels = dict(request.env['geosis.inec.index.value']._fields['month'].selection)
        values = {
            'page_name': 'inec',
            'index_record': index_record,
            'month_labels': month_labels,
            'current_year': fields.Date.today().year,
            'success': kw.get('success'),
            'error_message': kw.get('error_message'),
        }
        return request.render("geosis_website.portal_my_inec_index_detail", values)

    @http.route(['/my/inec-indices/<int:index_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_inec_index_edit(self, index_id, **kw):
        index_record = request.env['geosis.inec.index'].sudo().browse(index_id)
        if not index_record.exists():
            return request.redirect('/my/inec-indices')

        if request.httprequest.method == 'POST':
            try:
                index_record.write({
                    'code': kw.get('code') or index_record.code,
                    'name': kw.get('name'),
                    'active': True if kw.get('active') else False,
                })
                return request.redirect('/my/inec-indices/%s?success=updated' % index_record.id)
            except Exception as exc:
                values = {
                    'page_name': 'inec',
                    'index_record': index_record,
                    'form_data': kw,
                    'current_year': fields.Date.today().year,
                    'error_message': str(exc),
                }
                return request.render("geosis_website.portal_inec_form", values)

        values = {
            'page_name': 'inec',
            'index_record': index_record,
            'form_data': index_record.read(['code', 'name', 'active'])[0],
            'current_year': fields.Date.today().year,
            'error_message': False,
        }
        return request.render("geosis_website.portal_inec_form", values)

    @http.route(['/my/inec-indices/<int:index_id>/values/add'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_inec_value_add(self, index_id, **kw):
        index_record = request.env['geosis.inec.index'].sudo().browse(index_id)
        if not index_record.exists():
            return request.redirect('/my/inec-indices')
        try:
            request.env['geosis.inec.index.value'].sudo().create({
                'index_id': index_record.id,
                'year': int(kw.get('year')),
                'month': kw.get('month'),
                'value': float(kw.get('value', 0) or 0),
            })
            return request.redirect('/my/inec-indices/%s?success=value_added' % index_record.id)
        except Exception:
            return request.redirect('/my/inec-indices/%s?error_message=No se pudo agregar el valor mensual.' % index_record.id)

    @http.route(['/my/inec-indices/<int:index_id>/values/<int:value_id>/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_inec_value_update(self, index_id, value_id, **kw):
        value_record = request.env['geosis.inec.index.value'].sudo().browse(value_id)
        if value_record.exists() and value_record.index_id.id == index_id:
            try:
                value_record.write({
                    'year': int(kw.get('year')),
                    'month': kw.get('month'),
                    'value': float(kw.get('value', value_record.value) or 0),
                })
                return request.redirect('/my/inec-indices/%s?success=value_updated' % index_id)
            except Exception:
                pass
        return request.redirect('/my/inec-indices/%s' % index_id)

    @http.route(['/my/inec-indices/<int:index_id>/values/<int:value_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_inec_value_delete(self, index_id, value_id, **kw):
        value_record = request.env['geosis.inec.index.value'].sudo().browse(value_id)
        if value_record.exists() and value_record.index_id.id == index_id:
            value_record.unlink()
            return request.redirect('/my/inec-indices/%s?success=value_deleted' % index_id)
        return request.redirect('/my/inec-indices/%s' % index_id)

    @http.route(['/my/estimations', '/my/estimations/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_estimations(self, page=1, search=None, state='all', **kw):
        values = self._prepare_portal_layout_values()
        Estimation = request.env['geosis.estimation'].sudo()
        
        # Filtramos por los proyectos que pertenecen al cliente actual
        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        my_projects = Project.search(partner_domain)
        
        domain = [('project_id', 'in', my_projects.ids)]
        if search:
            domain += [('|', ('code', 'ilike', search), ('notes', 'ilike', search))]
        if state and state != 'all':
            domain += [('state', '=', state)]

        estimation_count = Estimation.search_count(domain)
        pager = portal_pager(
            url="/my/estimations",
            url_args={'search': search, 'state': state},
            total=estimation_count,
            page=page,
            step=10
        )
        estimations = Estimation.search(domain, limit=10, offset=pager['offset'])

        values.update({
            'estimations': estimations,
            'page_name': 'estimation',
            'pager': pager,
            'search': search,
            'selected_state': state,
            'estimation_total_count': estimation_count,
            'estimation_total_amount': sum(estimations.mapped('total_executed')),
        })
        return request.render("geosis_website.portal_my_estimations", values)

    @http.route(['/my/estimations/<int:estimation_id>'], type='http', auth="user", website=True)
    def portal_my_estimation_detail(self, estimation_id, **kw):
        estimation = request.env['geosis.estimation'].sudo().browse(estimation_id)
        if not estimation.exists():
            return request.redirect('/my/estimations')
            
        values = {
            'estimation': estimation,
            'page_name': 'estimation',
            'success': kw.get('success'),
            'error': kw.get('error'),
        }
        return request.render("geosis_website.portal_my_estimation_detail", values)

    @http.route(['/my/estimations/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_estimation_create(self, **kw):
        project_id = int(kw.get('project_id'))
        budget_id = int(kw.get('budget_id'))
        
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if not budget.exists():
            return request.redirect('/my/project/%s' % project_id)
            
        # Generar código automático simple
        last_est = request.env['geosis.estimation'].sudo().search([], order='id desc', limit=1)
        next_num = 1
        if last_est and last_est.code.startswith('EST-'):
            try:
                next_num = int(last_est.code.split('-')[1]) + 1
            except: pass
        code = "EST-%04d" % next_num
        
        # Crear planilla
        estimation = request.env['geosis.estimation'].sudo().create({
            'code': code,
            'project_id': project_id,
            'budget_id': budget_id,
            'estimation_date': fields.Date.context_today(budget),
            'state': 'draft',
        })
        
        # Crear líneas basadas en el presupuesto
        for line in budget.line_ids:
            request.env['geosis.estimation.line'].sudo().create({
                'estimation_id': estimation.id,
                'budget_line_id': line.id,
                'quantity_executed': 0.0,
            })
            
        return request.redirect('/my/estimations/%s?success=created' % estimation.id)

    @http.route(['/my/estimations/<int:estimation_id>/line/<int:line_id>/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_estimation_line_update(self, estimation_id, line_id, **kw):
        line = request.env['geosis.estimation.line'].sudo().browse(line_id)
        if line.exists() and line.estimation_id.id == estimation_id:
            try:
                line.sudo().write({
                    'quantity_executed': float(kw.get('quantity_executed', 0.0)),
                    'note': kw.get('note', ''),
                })
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/estimations/%s?success=updated' % estimation_id)

    @http.route(['/my/estimations/<int:estimation_id>/action/<string:action>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_estimation_state_action(self, estimation_id, action, **kw):
        estimation = request.env['geosis.estimation'].sudo().browse(estimation_id)
        if estimation.exists():
            if action == 'submit':
                estimation.action_submit()
            elif action == 'approve':
                estimation.action_approve()
            elif action == 'reject':
                estimation.action_reject()
            elif action == 'reset':
                estimation.action_reset_draft()
        return request.redirect('/my/estimations/%s?success=action_%s' % (estimation_id, action))

    @http.route(['/my/map'], type='http', auth="user", website=True)
    def portal_my_map(self, **kw):
        projects = request.env['geosis.project'].sudo().search([
            ('latitude', '!=', 0.0),
            ('longitude', '!=', 0.0)
        ])
        
        values = {
            'projects': projects,
            'page_name': 'map',
            'page_title': 'Mapa de Bases de Datos',
            'page_subtitle': 'Explora precios y presupuestos por ubicacion geografica',
        }
        return request.render("geosis_website.portal_my_map", values)
