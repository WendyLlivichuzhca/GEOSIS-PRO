# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv import expression
import base64

class GeosisCustomerPortal(CustomerPortal):

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
        critical_tasks = request.env['project.task'].sudo().search([
            ('project_id', 'in', all_odoo_projects.ids),
            ('is_critical', '=', True),
            ('stage_id.is_closed', '=', False)
        ], limit=5, order='date_deadline asc')

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

        values.update({
            'projects': projects,
            'page_name': 'project',
            'pager': pager,
            'search': search,
            'selected_state': state,
            'sort_by': sort_by,
            'sortings': sortings,
            'project_total_count': project_count,
            'project_total_amount': sum(projects.mapped('total_budget_amount')),
        })
        return request.render("geosis_website.portal_my_projects", values)

    @http.route(['/my/gantt'], type='http', auth="user", website=True)
    def portal_my_gantt(self, **kw):
        values = self.portal_my_projects(**kw).qcontext
        values.update({
            'page_name': 'gantt',
            'page_title': 'Cronogramas de Obra',
            'page_subtitle': 'Visualización de ruta crítica y Gantt',
        })
        return request.render("geosis_website.portal_my_projects", values)

    @http.route(['/my/projects/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_project_new(self, **kw):
        values = {
            'page_name': 'project',
            'form_data': {},
        }
        if request.httprequest.method == 'POST':
            try:
                Project = request.env['geosis.project'].sudo()
                vals = {
                    'name': kw.get('name'),
                    'code': kw.get('code') or Project._get_next_project_code(),
                    'location': kw.get('location'),
                    'state': kw.get('state', 'planning'),
                    'partner_id': request.env.user.partner_id.commercial_partner_id.id,
                    'description': kw.get('description'),
                }
                if kw.get('start_date'):
                    vals['start_date'] = kw.get('start_date')
                if kw.get('end_date'):
                    vals['end_date'] = kw.get('end_date')
                
                new_project = Project.create(vals)
                return request.redirect('/my/projects/%s?success=created' % new_project.id)
            except Exception as e:
                values['error_message'] = str(e)
                values['form_data'] = kw
                
        return request.render("geosis_website.portal_project_form", values)

    @http.route(['/my/projects/<int:project_id>'], type='http', auth="user", website=True)
    def portal_my_project_detail(self, project_id, **kw):
        project = request.env['geosis.project'].sudo().browse(project_id)
        # Comentado temporalmente para depurar
        # commercial_partner_id = request.env.user.partner_id.commercial_partner_id.id
        # if not project.exists() or project.partner_id.commercial_partner_id.id != commercial_partner_id:
        #     return request.redirect('/my/projects')

        editable_budget = project.budget_ids.filtered(lambda b: b.state == 'draft')[:1]
        project_tasks = editable_budget.odoo_project_id.task_ids.sorted(lambda t: (t.planned_date_start or t.create_date, t.id))
        
        # Calcular datos para Gantt
        tasks_with_gantt = []
        if project_tasks:
            all_dates = [t.planned_date_start for t in project_tasks if t.planned_date_start] + \
                        [t.planned_date_end for t in project_tasks if t.planned_date_end]
            if all_dates:
                min_date = min(all_dates)
                max_date = max(all_dates)
                total_days = (max_date - min_date).days or 1
                
                for t in project_tasks:
                    left = 0
                    width = 0
                    if t.planned_date_start and t.planned_date_end:
                        left = ((t.planned_date_start - min_date).days / total_days) * 100
                        width = (((t.planned_date_end - t.planned_date_start).days or 1) / total_days) * 100
                    
                    tasks_with_gantt.append({
                        'task': t,
                        'left': left,
                        'width': width
                    })

        values = {
            'project': project,
            'editable_budget': editable_budget,
            'project_tasks': project_tasks,
            'tasks_with_gantt': tasks_with_gantt,
            'available_apus': request.env['geosis.apu'].sudo().search([]),
            'page_name': 'project',
            'page_title': project.name,
            'success': kw.get('success'),
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
        return request.redirect('/my/projects/%s?success=metadata_updated' % project_id)

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
            
        values = {
            'budget': budget,
            'page_name': 'budget',
            'success': kw.get('success'),
            'available_apus': request.env['geosis.apu'].sudo().search([]),
        }
        return request.render("geosis_website.portal_my_budget_detail", values)

    @http.route(['/my/budget/<int:budget_id>/update-metadata'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_update_metadata(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists():
            try:
                budget.sudo().write({
                    'indirect_percent': float(kw.get('indirect_percent', budget.indirect_percent)),
                    'iva_percent': float(kw.get('iva_percent', budget.iva_percent)),
                    'offerer_id': int(kw.get('offerer_id')) if kw.get('offerer_id') else budget.offerer_id.id,
                })
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/budgets/%s?success=metadata_updated' % budget_id)

    @http.route(['/my/budget/<int:budget_id>/line/<int:line_id>/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_update(self, budget_id, line_id, **kw):
        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if line.exists() and line.budget_id.id == budget_id:
            try:
                line.sudo().write({
                    'quantity': float(kw.get('quantity', line.quantity)),
                    'unit_price': float(kw.get('unit_price', line.unit_price)),
                    'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else line.chapter_id.id,
                })
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/budgets/%s?success=line_updated' % budget_id)

    @http.route(['/my/budget/<int:budget_id>/line/add'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_add(self, budget_id, **kw):
        budget = request.env['geosis.budget'].sudo().browse(budget_id)
        if budget.exists() and kw.get('apu_id'):
            apu = request.env['geosis.apu'].sudo().browse(int(kw.get('apu_id')))
            request.env['geosis.budget.line'].sudo().create({
                'budget_id': budget.id,
                'apu_id': apu.id,
                'quantity': float(kw.get('quantity', 1.0)),
                'unit_price': float(kw.get('unit_price', apu.total_cost)),
                'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else False,
            })
        return request.redirect('/my/budgets/%s?success=line_added' % budget_id)

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
        task = request.env['project.task'].sudo().browse(task_id)
        if task.exists() and task.project_id.id == project_id:
            predecessor_id = int(kw.get('predecessor_id')) if kw.get('predecessor_id') else False
            if predecessor_id:
                task.write({'depend_on_ids': [(6, 0, [predecessor_id])]})
            else:
                task.write({'depend_on_ids': [(5, 0, 0)]})
            # Recalcular ruta crítica
            task.action_calculate_critical_path()
        return request.redirect('/my/projects/%s?tab=tasks' % project_id)

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
            budget.action_create_schedule_tasks()
            return request.redirect('/my/projects/%s?success=1' % budget.project_id.id)
        except Exception as e:
            return request.redirect('/my/budgets/%s?error=%s' % (budget_id, str(e)))

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
            
        pdf_content, content_type = request.env.ref(report_ref).sudo()._render_qweb_pdf([budget.id])
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
            
        pdf_content, content_type = request.env.ref('geosis_apu.action_report_geosis_apu').sudo()._render_qweb_pdf([apu.id])
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
        wizard = request.env['geosis.budget.export.msproject'].sudo().create({'budget_id': budget.id})
        xml_data = wizard._generate_msproject_xml()
        
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
                'note': kw.get('note', line.note),
            })
        return request.redirect('/my/rubro/%s?line_updated=1' % apu_id)

    @http.route(['/my/rubro/<int:apu_id>/generate-ia'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_generate_ia(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        apu.action_generate_with_ia()
        return request.redirect('/my/rubros/%s?ia_generated=1' % apu_id)

    @http.route(['/my/rubros'], type='http', auth="user", website=True)
    def portal_my_rubros(self, search=None, active='active', sort_by='name', **kw):
        Apu = request.env['geosis.apu'].sudo()
        domain = []
        if search:
            domain += [('|', '|', ('name', 'ilike', search), ('code', 'ilike', search), ('uom_name', 'ilike', search))]
        if active == 'active':
            domain += [('active', '=', True)]
        elif active == 'inactive':
            domain += [('active', '=', False)]

        sortings = {
            'name': {'label': 'Nombre A-Z', 'order': 'name asc'},
            'code': {'label': 'Código', 'order': 'code asc'},
            'cost': {'label': 'Costo mayor', 'order': 'total_cost desc'},
        }
        order = sortings.get(sort_by, sortings['name'])['order']
        rubros = Apu.search(domain, order=order)

        values = {
            'rubros': rubros,
            'page_name': 'rubro',
            'search': search,
            'selected_active': active,
            'sort_by': sort_by,
            'sortings': sortings,
            'rubro_total_count': Apu.search_count([]),
            'rubro_active_count': Apu.search_count([('active', '=', True)]),
            'rubro_inactive_count': Apu.search_count([('active', '=', False)]),
            'rubro_avg_total': sum(rubros.mapped('total_cost')) / len(rubros) if rubros else 0.0,
        }
        return request.render("geosis_website.portal_my_rubros", values)

    @http.route(['/my/rubro/<int:apu_id>'], type='http', auth="user", website=True)
    def portal_my_rubro_detail(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        resource_categories = {
            'M': {'label': 'Equipos', 'description': 'Herramientas y maquinaria pesada'},
            'N': {'label': 'Mano de Obra', 'description': 'Personal tecnico y obreros'},
            'O': {'label': 'Materiales', 'description': 'Suministros y materia prima'},
            'P': {'label': 'Transporte', 'description': 'Logistica y movilizacion'},
        }
        values = {
            'apu': apu,
            'page_name': 'rubro',
            'resource_categories': resource_categories,
            'success': kw.get('success'),
            'ia_generated': kw.get('ia_generated'),
        }
        return request.render("geosis_website.portal_my_rubro_detail", values)

    @http.route(['/my/rubro/<int:apu_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_rubro_edit(self, apu_id, **kw):
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        values = {
            'apu': apu,
            'page_name': 'rubro',
            'form_data': apu.read(['code', 'name', 'uom_name', 'indirect_percent', 'description', 'active'])[0],
        }
        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'code': kw.get('code'),
                    'name': kw.get('name'),
                    'uom_name': kw.get('uom_name'),
                    'indirect_percent': float(kw.get('indirect_percent', 0)),
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
                    'code': kw.get('code'),
                    'name': kw.get('name'),
                    'uom_name': kw.get('uom_name'),
                    'indirect_percent': float(kw.get('indirect_percent', 0)),
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

    @http.route(['/my/rubro/resource/add'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_resource_add(self, **kw):
        apu_id = int(kw.get('apu_id'))
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        
        resource_name = kw.get('resource_name')
        category = kw.get('category')
        
        # Buscar o crear el recurso
        Resource = request.env['geosis.resource'].sudo()
        resource = Resource.search([('name', '=', resource_name), ('category', '=', category)], limit=1)
        if not resource:
            resource = Resource.create({
                'name': resource_name,
                'category': category,
                'uom_name': kw.get('uom_name'),
                'price': float(kw.get('rate', 0)),
            })
            
        # Crear la linea del APU
        request.env['geosis.apu.line'].sudo().create({
            'apu_id': apu.id,
            'resource_id': resource.id,
            'quantity': float(kw.get('quantity', 1.0)),
            'rate': float(kw.get('rate', resource.price)),
            'performance': float(kw.get('performance', 1.0)),
        })
        
        return request.redirect('/my/rubro/%s?resource_line_added=1' % apu.id)

    @http.route(['/my/rubro/line/<int:line_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_line_delete(self, line_id, **kw):
        line = request.env['geosis.apu.line'].sudo().browse(line_id)
        apu_id = line.apu_id.id
        if line.exists():
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
                
            wizard = request.env['geosis.excel.import.wizard'].sudo().create(wizard_vals)
            
            try:
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
    def portal_my_resources(self, page=1, search=None, category='all', sort_by='name', **kw):
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
            url_args={'search': search, 'category': category, 'sort_by': sort_by},
            total=resource_count,
            page=page,
            step=20,
        )
        resources = Resource.search(domain, order=order, limit=20, offset=pager['offset'])

        values = {
            'resources': resources,
            'resource_total_count': resource_count,
            'resource_equipment_count': Resource.search_count([('active', '=', True), ('category', '=', 'M')]),
            'resource_labor_count':     Resource.search_count([('active', '=', True), ('category', '=', 'N')]),
            'resource_material_count':  Resource.search_count([('active', '=', True), ('category', '=', 'O')]),
            'pager': pager,
            'search': search or '',
            'selected_category': category,
            'sort_by': sort_by,
            'sortings': sortings,
            'page_name': 'resource',
            'success': kw.get('success'),
        }
        return request.render("geosis_website.portal_my_resources", values)

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
            return request.redirect('/my/projects/%s' % project_id)
            
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
