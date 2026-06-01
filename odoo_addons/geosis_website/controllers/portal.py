# -*- coding: utf-8 -*-
from datetime import date, timedelta
from urllib.parse import quote

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

    def _build_gantt_years(self, tasks_with_gantt):
        if not tasks_with_gantt:
            return []

        all_dates = []
        for item in tasks_with_gantt:
            if item.get('start_dt'):
                all_dates.append(item['start_dt'])
            if item.get('end_dt'):
                all_dates.append(item['end_dt'])

        if not all_dates:
            return []

        min_date = min(all_dates)
        max_date = max(all_dates)
        min_base = min_date.date() if hasattr(min_date, 'date') else min_date
        max_base = max_date.date() if hasattr(max_date, 'date') else max_date
        total_days = max((max_base - min_base).days, 1)
        years = []

        for year in range(min_base.year, max_base.year + 1):
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            visible_start = max(min_base, year_start)
            visible_end = min(max_base, year_end)
            if visible_end < visible_start:
                continue

            start_offset = max((visible_start - min_base).days, 0)
            end_offset = max((visible_end - min_base).days, 0)
            left = (start_offset / total_days) * 100
            width = (max(end_offset - start_offset, 1) / total_days) * 100
            years.append({
                'year': year,
                'left': left,
                'width': width,
            })

        return years

    def _build_task_board_columns(self, project_tasks, project_stage_ids=None):
        columns = []
        grouped = {}
        empty_tasks = request.env['project.task'].sudo().browse()

        if not project_tasks:
            return [{
                'id': 0,
                'name': 'Sin Etapa',
                'fold': False,
                'tasks': empty_tasks,
            }]

        for task in project_tasks:
            stage = task.stage_id
            stage_key = stage.id or 0
            if stage_key not in grouped:
                grouped[stage_key] = {
                    'id': stage_key,
                    'name': stage.name or 'None',
                    'fold': bool(getattr(stage, 'fold', False)),
                    'tasks': empty_tasks,
                }
            grouped[stage_key]['tasks'] |= task

        if 0 not in grouped:
            grouped[0] = {
                'id': 0,
                'name': 'None',
                'fold': False,
                'tasks': empty_tasks,
            }

        def sort_key(item):
            stage_id, stage_data = item
            return (
                stage_id != 0,
                stage_data['fold'],
                stage_data['name'].lower(),
                stage_id,
            )

        for key, value in sorted(grouped.items(), key=sort_key):
            columns.append(value)
        return columns

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

    def _get_accessible_budget(self, budget_id):
        Budget = request.env['geosis.budget'].sudo()
        budget = Budget.browse(budget_id)
        if not budget.exists() or not budget.project_id:
            return Budget
        return budget if self._get_accessible_project(budget.project_id.id) else Budget

    def _get_accessible_estimation(self, estimation_id):
        Estimation = request.env['geosis.estimation'].sudo()
        estimation = Estimation.browse(estimation_id)
        if not estimation.exists() or not estimation.project_id:
            return Estimation
        return estimation if self._get_accessible_project(estimation.project_id.id) else Estimation

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

    def _compute_schedule_kpis(self, tasks, board_columns):
        Task = request.env['project.task'].sudo()
        today = fields.Date.context_today(request.env.user)
        total_task_count = len(tasks)
        open_task_ids = set()
        completed_task_ids = set()
        overdue_task_ids = set()
        stage_progress = []

        if total_task_count:
            open_tasks = Task.search([('id', 'in', tasks.ids)] + self._get_open_task_domain())
            open_task_ids = set(open_tasks.ids)
            completed_task_ids = set(tasks.ids) - open_task_ids
            if open_task_ids:
                overdue_tasks = Task.search(
                    [('id', 'in', list(open_task_ids)), '|', ('date_deadline', '<', today), ('planned_date_end', '<', today)]
                )
                overdue_task_ids = set(overdue_tasks.ids)

        open_task_count = len(open_task_ids)
        completed_task_count = len(completed_task_ids)
        overdue_task_count = len(overdue_task_ids)
        schedule_compliance_pct = ((total_task_count - overdue_task_count) / total_task_count * 100.0) if total_task_count else 0.0
        overdue_rate_pct = (overdue_task_count / open_task_count * 100.0) if open_task_count else 0.0
        delay_index_pct = (overdue_task_count / total_task_count * 100.0) if total_task_count else 0.0

        for column in board_columns or []:
            column_total = len(column['tasks'])
            column_open = len([task for task in column['tasks'] if task.id in open_task_ids])
            column_completed = len([task for task in column['tasks'] if task.id in completed_task_ids])
            if not column_total:
                continue
            stage_progress.append({
                'name': column['name'],
                'total': column_total,
                'open': column_open,
                'completed': column_completed,
                'share_pct': (column_total / total_task_count * 100.0) if total_task_count else 0.0,
                'completion_pct': (column_completed / column_total * 100.0) if column_total else 0.0,
                'completion_pct_clamped': min(max((column_completed / column_total * 100.0) if column_total else 0.0, 0.0), 100.0),
                'is_folded': bool(column.get('fold')),
            })

        return {
            'total_task_count': total_task_count,
            'open_task_count': open_task_count,
            'completed_task_count': completed_task_count,
            'overdue_task_count': overdue_task_count,
            'schedule_compliance_pct': schedule_compliance_pct,
            'overdue_rate_pct': overdue_rate_pct,
            'delay_index_pct': delay_index_pct,
            'stage_progress': stage_progress,
        }

    def _prepare_portal_layout_values(self):
        values = super(GeosisCustomerPortal, self)._prepare_portal_layout_values()
        values.update({
            'is_geosis_team_admin': self._is_team_admin(),
            'is_geosis_portal_resident': self._is_portal_resident(),
            'is_geosis_portal_supervisor': self._is_portal_supervisor(),
            'is_geosis_portal_appraiser': self._is_portal_appraiser(),
        })
        return values

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

    def _is_team_admin(self):
        user = request.env.user
        partner = user.partner_id
        commercial_partner = partner.commercial_partner_id
        return bool(
            user.has_group('geosis_base.group_geosis_admin')
            or (partner and commercial_partner and partner.id == commercial_partner.id)
        )

    def _is_portal_resident(self):
        return request.env.user.has_group('geosis_base.group_geosis_portal_resident')

    def _is_portal_supervisor(self):
        return request.env.user.has_group('geosis_base.group_geosis_portal_supervisor')

    def _is_portal_appraiser(self):
        return request.env.user.has_group('geosis_base.group_geosis_portal_appraiser')

    def _is_portal_worker(self):
        return (
            self._is_portal_resident()
            or self._is_portal_supervisor()
            or self._is_portal_appraiser()
        )

    def _can_manage_admin_portal(self):
        return self._is_team_admin() and not self._is_portal_worker()

    def _can_access_avaluos(self):
        return self._can_manage_admin_portal() or self._is_portal_appraiser()

    def _get_avaluo_domain_for_current_user(self):
        if self._can_manage_admin_portal():
            return self._partner_domain()
        if self._is_portal_appraiser():
            return [('inspector_id', '=', request.env.user.id)] + self._partner_domain()
        return [('id', '=', 0)]

    def _deny_portal_access(self):
        return request.redirect('/geosis/dashboard?error=access_denied')

    def _deny_json_access(self):
        return {'success': False, 'error': 'No tienes permisos para realizar esta accion'}

    def _task_assigned_to_current_user(self, task):
        user = request.env.user
        if 'user_ids' in task._fields:
            return user in task.user_ids
        if 'user_id' in task._fields:
            return task.user_id.id == user.id
        return False

    def _assigned_task_domain(self):
        Task = request.env['project.task']
        user_id = request.env.user.id
        has_user_ids = 'user_ids' in Task._fields
        has_user_id = 'user_id' in Task._fields
        if has_user_ids and has_user_id:
            return ['|', ('user_ids', 'in', [user_id]), ('user_id', '=', user_id)]
        if has_user_ids:
            return [('user_ids', 'in', [user_id])]
        if has_user_id:
            return [('user_id', '=', user_id)]
        return [('id', '=', 0)]

    def _filter_tasks_for_current_role(self, tasks):
        if self._is_portal_resident():
            return tasks.filtered(lambda task: self._task_assigned_to_current_user(task))
        return tasks

    def _project_has_assigned_task(self, project):
        if not self._is_portal_resident():
            return True
        _, _, odoo_projects = self._get_project_budget_context(project)
        if not odoo_projects:
            return False
        return bool(request.env['project.task'].sudo().search_count(
            [('project_id', 'in', odoo_projects.ids)] + self._assigned_task_domain()
        ))

    def _can_update_task_state(self, task):
        return (
            self._can_manage_admin_portal()
            or self._is_portal_supervisor()
            or (self._is_portal_resident() and self._task_assigned_to_current_user(task))
        )

    def _can_review_task(self):
        return self._can_manage_admin_portal() or self._is_portal_supervisor()

    def _get_team_company_partner(self):
        return request.env.user.partner_id.commercial_partner_id

    def _get_team_user_domain(self):
        company_partner = self._get_team_company_partner()
        geosis_groups = [
            request.env.ref('geosis_base.group_geosis_admin', raise_if_not_found=False),
            request.env.ref('geosis_base.group_geosis_user', raise_if_not_found=False),
            request.env.ref('geosis_base.group_geosis_readonly', raise_if_not_found=False),
            request.env.ref('geosis_base.group_geosis_portal_resident', raise_if_not_found=False),
            request.env.ref('geosis_base.group_geosis_portal_supervisor', raise_if_not_found=False),
            request.env.ref('geosis_base.group_geosis_portal_appraiser', raise_if_not_found=False),
        ]
        geosis_group_ids = [group.id for group in geosis_groups if group]
        domain = [
            ('partner_id.commercial_partner_id', '=', company_partner.id),
            ('id', '!=', request.env.user.id),
        ]
        if geosis_group_ids:
            domain.append(('groups_id', 'in', geosis_group_ids))
        return domain

    def _get_team_users(self):
        User = request.env['res.users'].sudo().with_context(active_test=False)
        users = User.search(self._get_team_user_domain(), order='active desc, name asc, id asc')
        for user in users:
            self._ensure_team_user_is_portal_only(user)
        return users

    def _get_team_role_choices(self):
        return [
            ('resident', 'Residente de Obra'),
            ('supervisor', 'Fiscalizador / Supervisor'),
            ('perito', 'Perito Valuador'),
        ]

    def _get_user_team_role(self, user):
        if user.has_group('geosis_base.group_geosis_admin'):
            return 'Administrador'
        if user.has_group('geosis_base.group_geosis_portal_resident'):
            return 'Residente de Obra'
        if user.has_group('geosis_base.group_geosis_portal_supervisor'):
            return 'Fiscalizador / Supervisor'
        if user.has_group('geosis_base.group_geosis_portal_appraiser'):
            return 'Perito Valuador'
        if user.has_group('geosis_base.group_geosis_user'):
            return 'Residente de Obra'
        if user.has_group('geosis_base.group_geosis_readonly'):
            return 'Fiscalizador / Supervisor'
        return 'Sin rol GEOSIS'

    def _get_portal_team_group(self, role):
        if role == 'resident':
            xmlid = 'geosis_base.group_geosis_portal_resident'
        elif role == 'supervisor':
            xmlid = 'geosis_base.group_geosis_portal_supervisor'
        elif role == 'perito':
            xmlid = 'geosis_base.group_geosis_portal_appraiser'
        else:
            return request.env['res.groups']
        return request.env.ref(xmlid, raise_if_not_found=False)

    def _get_portal_team_group_ids(self, role):
        groups = [
            request.env.ref('base.group_portal', raise_if_not_found=False),
        ]
        g = self._get_portal_team_group(role)
        if g:
            groups.append(g)
        return [group.id for group in groups if group]

    def _ensure_team_user_is_portal_only(self, user):
        """Convert collaborators created by Mi Equipo before this fix to portal-only users."""
        if not user or user.id == request.env.user.id:
            return
        if user.has_group('geosis_base.group_geosis_admin'):
            return

        role = False
        if user.has_group('geosis_base.group_geosis_portal_resident'):
            role = 'resident'
        elif user.has_group('geosis_base.group_geosis_portal_supervisor'):
            role = 'supervisor'
        elif user.has_group('geosis_base.group_geosis_portal_appraiser'):
            role = 'perito'
        elif user.has_group('geosis_base.group_geosis_user'):
            role = 'resident'
        elif user.has_group('geosis_base.group_geosis_readonly'):
            role = 'supervisor'

        if not role:
            return

        remove_xmlids = [
            'base.group_user',
            'project.group_project_user',
            'geosis_base.group_geosis_user',
            'geosis_base.group_geosis_readonly',
        ]
        commands = []
        for xmlid in remove_xmlids:
            group = request.env.ref(xmlid, raise_if_not_found=False)
            if group:
                commands.append((3, group.id))
        for group_id in self._get_portal_team_group_ids(role):
            commands.append((4, group_id))
        if commands:
            user.sudo().write({'groups_id': commands})
            user.invalidate_recordset(['groups_id'])

    def _prepare_team_member_values(self, user):
        partner = user.partner_id
        return {
            'user': user,
            'role_label': self._get_user_team_role(user),
            'phone': partner.phone or partner.mobile or '',
            'email': user.login or partner.email or '',
            'status_label': 'Activo' if user.active else 'Inactivo',
        }

    def _legacy_geosis_private_dashboard_unused(self, **kw):
        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        Apu = request.env['geosis.apu'].sudo()
        Resource = request.env['geosis.resource'].sudo()
        
        latest_projects = Project.search(partner_domain, limit=5, order='write_date desc')
        
        # Estadisticas de recursos
        res_stats = {}
        for cat in ['M', 'N', 'O', 'P']:
            resources = Resource.search([('category_id.code', '=', cat)])
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
        cat_subtotals = {
            'M': sum(Resource.search([('category_id.code', '=', 'M')]).mapped('price')),
            'N': sum(Resource.search([('category_id.code', '=', 'N')]).mapped('price')),
            'O': sum(Resource.search([('category_id.code', '=', 'O')]).mapped('price')),
            'P': sum(Resource.search([('category_id.code', '=', 'P')]).mapped('price')),
        }

        values = {
            'project_count': Project.search_count(partner_domain),
            'active_project_count': Project.search_count([*partner_domain, ('state', '=', 'active')]),
            'apu_count': Apu.search_count([('active', '=', True)]),
            'resource_count': Resource.search_count([('active', '=', True)]),
            'latest_projects': latest_projects,
            'res_stats': res_stats,
            'critical_tasks': critical_tasks,
            'cost_dist': cat_subtotals,
            'page_name': 'home',
        }
        return request.render("geosis_website.geosis_private_dashboard_page", values)

    @http.route(['/geosis/dashboard'], type='http', auth="user", website=True)
    def geosis_private_dashboard(self, **kw):
        is_resident_dashboard = self._is_portal_resident()
        is_supervisor_dashboard = self._is_portal_supervisor()
        is_appraiser_dashboard = self._is_portal_appraiser()
        is_direction_dashboard = not (
            is_resident_dashboard or is_supervisor_dashboard or is_appraiser_dashboard
        )

        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        Apu = request.env['geosis.apu'].sudo()
        Resource = request.env['geosis.resource'].sudo()
        Estimation = request.env['geosis.estimation'].sudo()
        Bitacora = request.env['geosis.bitacora'].sudo()
        Task = request.env['project.task'].sudo()
        Avaluo = request.env['geosis.avaluo'].sudo()

        today = fields.Date.context_today(request.env.user)
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        all_client_projects = Project.search(partner_domain)
        if is_resident_dashboard:
            all_client_projects = all_client_projects.filtered(lambda project: self._project_has_assigned_task(project))
        latest_projects = all_client_projects[:5]
        all_budgets = request.env['geosis.budget'].sudo().search([('project_id', 'in', all_client_projects.ids)])
        all_odoo_projects = all_budgets.mapped('odoo_project_id').filtered(lambda project: project.exists())

        res_stats = {}
        for cat in ['M', 'N', 'O', 'P']:
            resources = Resource.search([('category_id.code', '=', cat), ('active', '=', True)])
            res_stats[cat] = {
                'count': len(resources),
                'avg': sum(resources.mapped('price')) / len(resources) if resources else 0.0,
            }

        budget_total_amount = sum(all_client_projects.mapped('total_budget_amount'))
        latest_approved_estimations = Estimation.browse()
        for budget in all_budgets:
            approved_estimation = Estimation.search([
                ('budget_id', '=', budget.id),
                ('state', '=', 'approved'),
            ], limit=1, order='estimation_date desc, id desc')
            if approved_estimation:
                latest_approved_estimations |= approved_estimation

        executed_total = sum(latest_approved_estimations.mapped('total_accumulated'))
        pending_total = max(budget_total_amount - executed_total, 0.0)
        physical_progress_pct = (executed_total / budget_total_amount * 100.0) if budget_total_amount else 0.0

        delayed_project_count = len(all_client_projects.filtered(
            lambda project: project.state not in ('completed', 'cancelled') and project.end_date and project.end_date < today
        ))
        completed_project_count = len(all_client_projects.filtered(lambda project: project.state == 'completed'))

        base_task_domain = [('project_id', 'in', all_odoo_projects.ids)]
        if is_resident_dashboard:
            base_task_domain += self._assigned_task_domain()

        open_task_domain = base_task_domain + self._get_open_task_domain()
        critical_task_domain = open_task_domain + [('is_critical', '=', True)]
        critical_tasks = Task.search(
            critical_task_domain,
            limit=5,
            order='date_deadline asc, planned_date_end asc, id asc',
        )
        overdue_task_count = Task.search_count(
            open_task_domain + ['|', ('date_deadline', '<', today), ('planned_date_end', '<', today)]
        )

        month_bitacoras = Bitacora.search([
            ('project_id', 'in', all_client_projects.ids),
            ('date', '>=', month_start),
            ('date', '<=', month_end),
        ])
        if is_resident_dashboard:
            month_bitacoras = month_bitacoras.filtered(lambda bitacora: bitacora.user_id.id == request.env.user.id)
        approved_bitacora_count = len(month_bitacoras.filtered(lambda bitacora: bitacora.state == 'approved'))
        month_bitacora_count = len(month_bitacoras)
        bitacora_approval_rate = (approved_bitacora_count / month_bitacora_count * 100.0) if month_bitacora_count else 0.0

        estimation_domain = [('project_id', 'in', all_client_projects.ids)]
        planilla_state_counts = {
            'draft': Estimation.search_count(estimation_domain + [('state', '=', 'draft')]),
            'submitted': Estimation.search_count(estimation_domain + [('state', '=', 'submitted')]),
            'approved': Estimation.search_count(estimation_domain + [('state', '=', 'approved')]),
            'rejected': Estimation.search_count(estimation_domain + [('state', '=', 'rejected')]),
        }

        cat_subtotals = {
            'M': sum(Resource.search([('category_id.code', '=', 'M'), ('active', '=', True)]).mapped('price')),
            'N': sum(Resource.search([('category_id.code', '=', 'N'), ('active', '=', True)]).mapped('price')),
            'O': sum(Resource.search([('category_id.code', '=', 'O'), ('active', '=', True)]).mapped('price')),
            'P': sum(Resource.search([('category_id.code', '=', 'P'), ('active', '=', True)]).mapped('price')),
        }

        avaluo_total_count = 0
        avaluo_pending_count = 0
        avaluo_inspected_count = 0
        avaluo_calculated_count = 0
        avaluo_approved_count = 0
        latest_avaluos = Avaluo.browse()
        if is_appraiser_dashboard:
            avaluo_domain = self._get_avaluo_domain_for_current_user()
            avaluo_total_count = Avaluo.search_count(avaluo_domain)
            avaluo_pending_count = Avaluo.search_count(avaluo_domain + [('state', '=', 'draft')])
            avaluo_inspected_count = Avaluo.search_count(avaluo_domain + [('state', '=', 'inspected')])
            avaluo_calculated_count = Avaluo.search_count(avaluo_domain + [('state', '=', 'calculated')])
            avaluo_approved_count = Avaluo.search_count(avaluo_domain + [('state', '=', 'approved')])
            latest_avaluos = Avaluo.search(avaluo_domain, order='date desc, id desc', limit=5)

        values = {
            'is_resident_dashboard': is_resident_dashboard,
            'is_supervisor_dashboard': is_supervisor_dashboard,
            'is_appraiser_dashboard': is_appraiser_dashboard,
            'is_direction_dashboard': is_direction_dashboard,
            'project_count': len(all_client_projects),
            'active_project_count': len(all_client_projects.filtered(lambda project: project.state == 'active')),
            'completed_project_count': completed_project_count,
            'delayed_project_count': delayed_project_count,
            'apu_count': Apu.search_count([('active', '=', True)]),
            'resource_count': Resource.search_count([('active', '=', True)]),
            'budget_total_amount': budget_total_amount,
            'executed_total': executed_total,
            'pending_total': pending_total,
            'physical_progress_pct': physical_progress_pct,
            'open_task_count': Task.search_count(open_task_domain),
            'critical_task_count': Task.search_count(critical_task_domain),
            'overdue_task_count': overdue_task_count,
            'approved_bitacora_count': approved_bitacora_count,
            'month_bitacora_count': month_bitacora_count,
            'bitacora_approval_rate': bitacora_approval_rate,
            'planilla_state_counts': planilla_state_counts,
            'month_label': month_start.strftime('%B %Y').capitalize(),
            'latest_projects': latest_projects,
            'res_stats': res_stats,
            'critical_tasks': critical_tasks,
            'cost_dist': cat_subtotals,
            'avaluo_total_count': avaluo_total_count,
            'avaluo_pending_count': avaluo_pending_count,
            'avaluo_inspected_count': avaluo_inspected_count,
            'avaluo_calculated_count': avaluo_calculated_count,
            'avaluo_approved_count': avaluo_approved_count,
            'latest_avaluos': latest_avaluos,
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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        values = self._prepare_portal_layout_values()
        Project = request.env['geosis.project'].sudo()
        domain = self._partner_domain()

        if search:
            domain += ['|', '|', ('name', 'ilike', search), ('code', 'ilike', search), ('location', 'ilike', search)]
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
        if self._is_portal_appraiser():
            return self._deny_portal_access()

        values = self._prepare_portal_layout_values()
        Bitacora = request.env['geosis.bitacora'].sudo()
        domain = self._partner_domain()
        
        project_ids = request.env['geosis.project'].sudo().search(domain).ids
        bitacora_domain = [('project_id', 'in', project_ids)]
        if self._is_portal_resident():
            bitacora_domain.append(('user_id', '=', request.env.user.id))

        if search:
            bitacora_domain += ['|', '|', 
                ('project_id.name', 'ilike', search), 
                ('content', 'ilike', search),
                ('personal_notes', 'ilike', search)
            ]

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
        all_bitacoras = Bitacora.search(bitacora_domain)
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
        if self._is_portal_appraiser():
            return self._deny_portal_access()

        Bitacora = request.env['geosis.bitacora'].sudo()
        bitacora = Bitacora.browse(bitacora_id)
        if not bitacora.exists():
            return request.redirect('/my/bitacoras')

        domain = self._partner_domain()
        project_ids = request.env['geosis.project'].sudo().search(domain).ids
        if bitacora.project_id.id not in project_ids:
            return request.redirect('/my/bitacoras')
        if self._is_portal_resident() and bitacora.user_id.id != request.env.user.id:
            return request.redirect('/my/bitacoras')

        # Procesar Guardado e Instrucciones del Fiscalizador
        if request.httprequest.method == 'POST':
            if not self._can_review_task():
                return self._deny_portal_access()
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
        if self._is_portal_appraiser():
            return self._deny_portal_access()

        Bitacora = request.env['geosis.bitacora'].sudo()
        bitacora = Bitacora.browse(bitacora_id)
        if not bitacora.exists():
            return request.redirect('/my/bitacoras')

        domain = self._partner_domain()
        project_ids = request.env['geosis.project'].sudo().search(domain).ids
        if bitacora.project_id.id not in project_ids:
            return request.redirect('/my/bitacoras')
        if self._is_portal_resident() and bitacora.user_id.id != request.env.user.id:
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

    def _prepare_project_tasks_context(self, project_id=None):
        values = self._prepare_portal_layout_values()
        Project = request.env['geosis.project'].sudo()
        Task = request.env['project.task'].sudo()

        projects = Project.search(
            self._partner_domain(),
            order='write_date desc, id desc',
        )
        if self._is_portal_resident():
            projects = projects.filtered(lambda project: self._project_has_assigned_task(project))
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
                task_domain = [('project_id', 'in', odoo_projects.ids)]
                if self._is_portal_resident():
                    task_domain += self._assigned_task_domain()
                project_tasks = Task.search(
                    task_domain,
                    order='priority desc, planned_date_start asc, date_deadline asc, id asc',
                )
                tasks_with_gantt = self._build_tasks_with_gantt(project_tasks)

        open_task_count = 0
        completed_task_count = 0
        overdue_task_count = 0
        critical_task_count = 0
        schedule_compliance_pct = 0.0
        overdue_rate_pct = 0.0
        delay_index_pct = 0.0
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

        company_partner = self._get_team_company_partner()
        try:
            resident_group = request.env.ref('geosis_base.group_geosis_portal_resident').id
            assignable_domain = [
                ('active', '=', True),
                ('partner_id.commercial_partner_id', '=', company_partner.id),
                ('groups_id', 'in', [resident_group])
            ]
        except ValueError:
            # Fallback si por alguna razón no existe el grupo
            assignable_domain = [
                ('active', '=', True),
                ('partner_id.commercial_partner_id', '=', company_partner.id)
            ]
            
        assignable_users = request.env['res.users'].sudo().search(assignable_domain, order='name asc')
        stage_domain = []
        if odoo_projects:
            stage_domain = ['|', ('project_ids', '=', False), ('project_ids', 'in', odoo_projects.ids)]
        project_stages = request.env['project.task.type'].sudo().search(stage_domain, order='sequence asc, name asc') if stage_domain else request.env['project.task.type'].sudo().browse()
        gantt_years = self._build_gantt_years(tasks_with_gantt)
        task_board_columns = self._build_task_board_columns(project_tasks, project_stages.ids)
        schedule_kpis = self._compute_schedule_kpis(project_tasks, task_board_columns)
        open_task_count = schedule_kpis['open_task_count']
        completed_task_count = schedule_kpis['completed_task_count']
        overdue_task_count = schedule_kpis['overdue_task_count']
        schedule_compliance_pct = schedule_kpis['schedule_compliance_pct']
        overdue_rate_pct = schedule_kpis['overdue_rate_pct']
        delay_index_pct = schedule_kpis['delay_index_pct']
        task_state_choices = []
        if 'state' in Task._fields and getattr(Task._fields['state'], 'selection', None):
            task_state_choices = Task._fields['state'].selection
        else:
            task_state_choices = [
                ('01_in_progress', 'In Progress'),
                ('02_changes_requested', 'Changes Requested'),
                ('03_approved', 'Approved'),
                ('04_cancelled', 'Canceled'),
                ('01_done', 'Done'),
            ]

        values.update({
            'projects': projects,
            'selected_project': selected_project,
            'selected_odoo_project': selected_odoo_project,
            'budgets': budgets,
            'odoo_projects': odoo_projects,
            'project_tasks': project_tasks,
            'tasks_with_gantt': tasks_with_gantt,
            'task_durations': task_durations,
            'gantt_years': gantt_years,
            'gantt_task_count': len(project_tasks),
            'gantt_open_count': open_task_count,
            'gantt_completed_count': completed_task_count,
            'gantt_overdue_count': overdue_task_count,
            'gantt_critical_count': critical_task_count,
            'gantt_scheduled_count': len(tasks_with_gantt),
            'gantt_schedule_compliance_pct': schedule_compliance_pct,
            'gantt_overdue_rate_pct': overdue_rate_pct,
            'gantt_delay_index_pct': delay_index_pct,
            'gantt_stage_progress': schedule_kpis['stage_progress'],
            'assignable_users': assignable_users,
            'task_board_columns': task_board_columns,
            'task_stages': project_stages,
            'task_state_choices': task_state_choices,
        })
        return values

    @http.route(['/my/gantt'], type='http', auth="user", website=True)
    def portal_my_gantt(self, project_id=None, **kw):
        if self._is_portal_appraiser():
            return self._deny_portal_access()

        import json
        values = self._prepare_project_tasks_context(project_id)
        
        timeline_data = []
        seen_groups = set()
        groups = []
        
        for item in values.get('tasks_with_gantt', []):
            task = item['task']
            start_dt = item['start_dt']
            end_dt = item['end_dt']
            if not start_dt:
                start_dt = self._get_task_start(task)
            if not end_dt:
                end_dt = self._get_task_end(task)
                
            if start_dt and end_dt:
                try:
                    start_str = start_dt.strftime('%Y-%m-%d')
                    end_str = end_dt.strftime('%Y-%m-%d')
                except Exception:
                    start_str = str(start_dt)[:10]
                    end_str = str(end_dt)[:10]
                
                task_code = getattr(task, 'code', '') or ''
                task_name = task.name or ''
                content = f"[{task_code}] {task_name}" if task_code else task_name
                
                is_critical = False
                if 'is_critical' in task._fields:
                    is_critical = bool(task.is_critical)
                priority = task.priority or '0'
                
                group_id = task.project_id.id or 0
                group_name = task.project_id.name or 'Tareas Generales'
                
                timeline_data.append({
                    'id': task.id,
                    'group': group_id,
                    'content': content,
                    'start': start_str,
                    'end': end_str,
                    'is_critical': is_critical,
                    'priority': priority,
                })
                
                if group_id not in seen_groups:
                    seen_groups.add(group_id)
                    groups.append({
                        'id': group_id,
                        'content': group_name
                    })

        values.update({
            'page_name': 'gantt',
            'page_title': 'Cronograma (Gantt)',
            'page_subtitle': 'Tareas generadas desde las fechas del presupuesto',
            'action_url': '/my/gantt',
            'timeline_data_json': json.dumps(timeline_data),
            'timeline_groups_json': json.dumps(groups),
            'today_date': fields.Date.context_today(request.env.user).strftime('%Y-%m-%d'),
        })
        return request.render("geosis_website.portal_my_gantt_restored", values)

    @http.route(['/my/tasks'], type='http', auth="user", website=True)
    def portal_my_tasks(self, project_id=None, **kw):
        if self._is_portal_appraiser():
            return self._deny_portal_access()

        values = self._prepare_project_tasks_context(project_id)
        values.update({
            'page_name': 'tasks',
            'page_title': 'Tablero de Tareas',
            'page_subtitle': 'Gestión interactiva de tareas del proyecto',
            'action_url': '/my/tasks',
        })
        return request.render("geosis_website.portal_my_tasks_restored", values)

    @http.route(['/my/task/<int:task_id>/toggle_priority'], type='json', auth="user", methods=['POST'])
    def portal_task_toggle_priority(self, task_id, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists():
            return {'success': False, 'error': 'Tarea no encontrada'}
        
        if not self._check_task_access(task):
            return {'success': False, 'error': 'Acceso no permitido'}
        if not self._can_review_task():
            return self._deny_json_access()
        
        new_priority = '1' if task.priority == '0' else '0'
        task.write({'priority': new_priority})
        return {'success': True, 'new_priority': new_priority}

    @http.route(['/my/task/<int:task_id>/update_state'], type='json', auth="user", methods=['POST'])
    def portal_task_update_state(self, task_id, state_val, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists():
            return {'success': False, 'error': 'Tarea no encontrada'}
        
        if not self._check_task_access(task):
            return {'success': False, 'error': 'Acceso no permitido'}
        if not self._can_update_task_state(task):
            return self._deny_json_access()
        
        vals = {}
        if 'state' in task._fields:
            vals['state'] = state_val
        elif 'kanban_state' in task._fields:
            mapping = {
                '01_in_progress': 'normal',
                '02_changes_requested': 'blocked',
                '03_approved': 'done',
                '04_cancelled': 'blocked',
                '01_done': 'done'
            }
            vals['kanban_state'] = mapping.get(state_val, 'normal')
        
        if vals:
            task.write(vals)
            return {'success': True}
        return {'success': False, 'error': 'No se pudo actualizar el estado'}

    @http.route(['/my/task/<int:task_id>/update_assignee'], type='json', auth="user", methods=['POST'])
    def portal_task_update_assignee(self, task_id, user_id, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists():
            return {'success': False, 'error': 'Tarea no encontrada'}
        
        if not self._check_task_access(task):
            return {'success': False, 'error': 'Acceso no permitido'}
        if not self._can_manage_admin_portal():
            return self._deny_json_access()
        
        vals = {}
        if user_id:
            user = request.env['res.users'].sudo().browse(int(user_id))
            if not user.exists():
                return {'success': False, 'error': 'Usuario no encontrado'}
            if 'user_ids' in task._fields:
                vals['user_ids'] = [(6, 0, [user.id])]
            elif 'user_id' in task._fields:
                vals['user_id'] = user.id
        else:
            if 'user_ids' in task._fields:
                vals['user_ids'] = [(5, 0, 0)]
            elif 'user_id' in task._fields:
                vals['user_id'] = False
        
        task.write(vals)
        return {'success': True}

    @http.route(['/my/task/<int:task_id>/update_stage'], type='json', auth="user", methods=['POST'])
    def portal_task_update_stage(self, task_id, stage_id, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists():
            return {'success': False, 'error': 'Tarea no encontrada'}
        
        if not self._check_task_access(task):
            return {'success': False, 'error': 'Acceso no permitido'}
        if not self._can_manage_admin_portal():
            return self._deny_json_access()
        
        if stage_id:
            stage = request.env['project.task.type'].sudo().browse(int(stage_id))
            if not stage.exists():
                return {'success': False, 'error': 'Etapa no encontrada'}
            task.write({'stage_id': stage.id})
        else:
            task.write({'stage_id': False})
            
        return {'success': True}

    @http.route(['/my/task/<int:task_id>/update_dates'], type='json', auth="user", methods=['POST'])
    def portal_task_update_dates(self, task_id, start_date, end_date, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists():
            return {'success': False, 'error': 'Tarea no encontrada'}
        
        if not self._check_task_access(task):
            return {'success': False, 'error': 'Acceso no permitido'}
        if not self._can_manage_admin_portal():
            return self._deny_json_access()
            
        vals = {}
        if 'planned_date_start' in task._fields:
            vals['planned_date_start'] = start_date
        if 'planned_date_end' in task._fields:
            vals['planned_date_end'] = end_date
            
        # Fallbacks for standard task fields if planned_date_start/end do not exist
        if 'planned_date_start' not in task._fields:
            if 'date_assign' in task._fields:
                vals['date_assign'] = start_date
        if 'planned_date_end' not in task._fields:
            if 'date_deadline' in task._fields:
                vals['date_deadline'] = end_date
                
        if vals:
            task.write(vals)
            return {'success': True}
        return {'success': False, 'error': 'No hay campos de fecha modificables'}

    def _check_task_access(self, task):
        if self._is_portal_resident() and not self._task_assigned_to_current_user(task):
            return False
        Project = request.env['geosis.project'].sudo()
        projects = Project.search(self._partner_domain())
        all_odoo_project_ids = []
        for p in projects:
            budgets, _, odoo_projects = self._get_project_budget_context(p)
            if odoo_projects:
                all_odoo_project_ids.extend(odoo_projects.ids)
        return task.project_id.id in all_odoo_project_ids

    def _check_project_access(self, project_id):
        Project = request.env['geosis.project'].sudo()
        projects = Project.search(self._partner_domain())
        if self._is_portal_resident():
            projects = projects.filtered(lambda project: self._project_has_assigned_task(project))
        all_odoo_project_ids = []
        for p in projects:
            budgets, _, odoo_projects = self._get_project_budget_context(p)
            if odoo_projects:
                all_odoo_project_ids.extend(odoo_projects.ids)
        return project_id in all_odoo_project_ids

    @http.route(['/my/project/<int:project_id>/add_stage'], type='json', auth="user", methods=['POST'])
    def portal_project_add_stage(self, project_id, name, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_json_access()

        if not self._check_project_access(project_id):
            return {'success': False, 'error': 'Acceso no permitido'}
        
        if not name:
            return {'success': False, 'error': 'El nombre de la etapa es obligatorio'}
            
        stage_vals = {
            'name': name,
            'project_ids': [(4, project_id)]
        }
        existing_stages = request.env['project.task.type'].sudo().search([('project_ids', 'in', [project_id])])
        if existing_stages:
            max_seq = max(existing_stages.mapped('sequence') or [0])
            stage_vals['sequence'] = max_seq + 1
            
        request.env['project.task.type'].sudo().create(stage_vals)
        return {'success': True}

    @http.route(['/my/team'], type='http', auth="user", website=True)
    def portal_my_team(self, **kw):
        if not self._can_manage_admin_portal():
            return request.redirect('/geosis/dashboard')

        company_partner = self._get_team_company_partner()
        team_users = self._get_team_users()
        team_member_values = [self._prepare_team_member_values(user) for user in team_users]
        values = {
            'page_name': 'team',
            'page_title': 'Mi Equipo',
            'page_subtitle': 'Gestiona a tu personal desde el portal',
            'team_company_partner': company_partner,
            'team_members': team_member_values,
            'team_total_count': len(team_member_values),
            'team_active_count': len([member for member in team_member_values if member['user'].active]),
            'team_role_choices': self._get_team_role_choices(),
            'success': kw.get('success'),
            'error_message': kw.get('error_message'),
            'form_data': {
                'name': kw.get('name', ''),
                'email': kw.get('email', ''),
                'phone': kw.get('phone', ''),
                'role': kw.get('role', 'resident'),
            },
        }
        return request.render("geosis_website.portal_my_team", values)

    @http.route(['/my/team/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_create(self, **kw):
        if not self._can_manage_admin_portal():
            return request.redirect('/geosis/dashboard')

        name = (kw.get('name') or '').strip()
        email = (kw.get('email') or '').strip().lower()
        phone = (kw.get('phone') or '').strip()
        role = (kw.get('role') or 'resident').strip()

        if not name or not email or role not in dict(self._get_team_role_choices()):
            return request.redirect('/my/team?error_message=Completa los datos obligatorios del colaborador.')

        User = request.env['res.users'].sudo().with_context(active_test=False)
        if User.search_count(['|', ('login', '=', email), ('partner_id.email', '=', email)]):
            return request.redirect('/my/team?error_message=Ya existe un usuario con ese correo.')

        company_partner = self._get_team_company_partner().sudo()
        partner_vals = {
            'name': name,
            'email': email,
            'phone': phone,
            'parent_id': company_partner.id,
            'company_type': 'person',
            'type': 'contact',
        }
        partner = request.env['res.partner'].sudo().create(partner_vals)

        group_ids = self._get_portal_team_group_ids(role)

        user = User.create({
            'name': name,
            'login': email,
            'email': email,
            'partner_id': partner.id,
            'groups_id': [(6, 0, group_ids)],
            'active': True,
        })
        try:
            user.action_reset_password()
            return request.redirect('/my/team?success=created')
        except Exception as exc:
            message = (
                "El colaborador se creó, pero Odoo no pudo enviar la invitación. "
                "Revisa el servidor de correo saliente y usa Reenviar invitación. "
                f"Detalle: {exc}"
            )
            return request.redirect('/my/team?error_message=%s' % quote(message))

    @http.route(['/my/team/resend-invite/<int:user_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_resend_invite(self, user_id, **kw):
        if not self._can_manage_admin_portal():
            return request.redirect('/geosis/dashboard')

        user = request.env['res.users'].sudo().with_context(active_test=False).browse(user_id)
        company_partner = self._get_team_company_partner()
        if not user.exists() or user.partner_id.commercial_partner_id.id != company_partner.id:
            return request.redirect('/my/team?error_message=No tienes permisos para reenviar esta invitación.')

        try:
            user.action_reset_password()
            return request.redirect('/my/team?success=invite_resent')
        except Exception as exc:
            message = (
                "No se pudo reenviar la invitación. "
                "Revisa el servidor de correo saliente de Odoo. "
                f"Detalle: {exc}"
            )
            return request.redirect('/my/team?error_message=%s' % quote(message))

    @http.route(['/my/team/toggle-active/<int:user_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_team_toggle_active(self, user_id, **kw):
        if not self._can_manage_admin_portal():
            return request.redirect('/geosis/dashboard')

        user = request.env['res.users'].sudo().with_context(active_test=False).browse(user_id)
        if not user.exists():
            return request.redirect('/my/team?error_message=Colaborador no encontrado.')

        company_partner = self._get_team_company_partner()
        if user.partner_id.commercial_partner_id.id != company_partner.id:
            return request.redirect('/my/team?error_message=No tienes permisos para gestionar este colaborador.')

        if user.id == request.env.user.id:
            return request.redirect('/my/team?error_message=No puedes desactivar tu propio usuario desde el portal.')

        user.write({'active': not user.active})
        return request.redirect('/my/team?success=updated')

    @http.route(['/my/projects/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_project_new(self, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        
    @http.route(['/my/project/<int:project_id>/budget/new'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_project_budget_new(self, project_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        project = self._get_accessible_project(project_id)
        if not project:
            return request.redirect('/my/projects?error=project_access')
        
        Budget = request.env['geosis.budget'].sudo()
        new_budget = Budget.create({
            'name': f"Presupuesto Manual - {project.name}",
            'project_id': project.id,
            'location': project.location,
            'partner_id': request.env.user.partner_id.commercial_partner_id.id,
            'budget_date': fields.Date.context_today(request.env.user),
            'state': 'draft',
        })
        return request.redirect('/my/budgets/%s?success=created' % new_budget.id)

    @http.route(['/my/budgets', '/my/budgets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_budgets(self, page=1, search=None, state='all', sort_by='date', **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        values = self._prepare_portal_layout_values()
        Budget = request.env['geosis.budget'].sudo()
        
        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        my_projects = Project.search(partner_domain)
        
        domain = [('project_id', 'in', my_projects.ids)]
        if search:
            domain += ['|', ('code', 'ilike', search), ('name', 'ilike', search)]
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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')

        partner_domain = self._partner_domain()
        my_projects = request.env['geosis.project'].sudo().search(partner_domain, order='name asc')
        partner_tree_domain = [('id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)]
        available_partners = request.env['res.partner'].sudo().search(partner_tree_domain, order='name asc')
        available_offerers = request.env['res.partner'].sudo().search([('active', '=', True)], order='name asc')
        apu_domain = [('active', '=', True)]
        budget_loc = budget.location or (budget.project_id.location if budget.project_id else False)
        if budget_loc:
            apu_domain += [('location', '=', budget_loc)]
        else:
            apu_domain += [('location', 'in', [False, ''])]

        values = {
            'budget': budget,
            'page_name': 'budget',
            'success': kw.get('success'),
            'available_apus': request.env['geosis.apu'].sudo().search(apu_domain, order='name asc'),
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')

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
        if not self._can_manage_admin_portal():
            return request.make_json_response({'ok': False, 'message': 'No tienes permisos'}, status=403)

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.make_json_response({'ok': False, 'message': 'Presupuesto no encontrado'}, status=404)

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')

        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if line.exists() and line.budget_id.id == budget_id:
            line.sudo().unlink()
        return request.redirect('/my/budgets/%s?success=line_deleted' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/create-odoo-project'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_create_odoo_project(self, budget_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if budget.exists() and kw.get('name'):
            request.env['geosis.budget.chapter'].sudo().create({
                'budget_id': budget.id,
                'name': kw.get('name'),
                'parent_id': int(kw.get('parent_id')) if kw.get('parent_id') else False
            })
        return request.redirect('/my/budgets/%s?tab=chapters' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/line/<int:line_id>/move'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_line_move_chapter(self, budget_id, line_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')

        line = request.env['geosis.budget.line'].sudo().browse(line_id)
        if line.exists() and line.budget_id.id == budget_id:
            line.write({'chapter_id': int(kw.get('chapter_id')) if kw.get('chapter_id') else False})
        return request.redirect('/my/budgets/%s?line_moved=1' % budget_id)

    @http.route(['/my/projects/<int:project_id>/task/<int:task_id>/predecessor'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_project_task_update_predecessor(self, project_id, task_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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

    @http.route(['/my/rubro/<int:apu_id>/pdf', '/my/rubros/<int:apu_id>/pdf'], type='http', auth="user", website=True)
    def portal_my_rubro_pdf(self, apu_id, **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if budget.exists() and budget.state == 'draft':
            budget.sudo().write({'state': 'approved'})
        return request.redirect('/my/budgets/%s?success=approved' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/chapter/<int:chapter_id>/delete'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_chapter_delete(self, budget_id, chapter_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')

        chapter = request.env['geosis.budget.chapter'].sudo().browse(chapter_id)
        if chapter.exists() and chapter.budget_id.id == budget_id:
            chapter.sudo().unlink()
        return request.redirect('/my/budgets/%s?tab=chapters' % budget_id)

    @http.route(['/my/budgets/<int:budget_id>/calculate-polynomial'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_budget_calculate_polynomial(self, budget_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
        if not budget.exists():
            return request.redirect('/my/projects')
        try:
            budget.action_calculate_polynomial()
            return request.redirect('/my/budgets/%s?polynomial_calculated=1' % budget_id)
        except Exception as e:
            return request.redirect('/my/budgets/%s?error=%s' % (budget_id, str(e)))

    @http.route(['/my/budgets/<int:budget_id>/msproject'], type='http', auth="user", website=True)
    def portal_my_budget_msproject(self, budget_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        budget = self._get_accessible_budget(budget_id)
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        line = request.env['geosis.apu.line'].sudo().browse(line_id)
        if line.exists() and line.apu_id.id == apu_id:
            line.write({
                'quantity': self._parse_portal_float(kw.get('quantity'), line.quantity),
                'performance': self._parse_portal_float(kw.get('performance'), line.performance),
                'rate': self._parse_portal_float(kw.get('rate'), line.rate),
                'percentage': self._parse_portal_float(kw.get('percentage'), line.percentage),
                'distance': self._parse_portal_float(kw.get('distance'), line.distance),
                'note': kw.get('note', line.note),
            })
        return request.redirect('/my/rubro/%s?line_updated=1' % apu_id)

    @http.route(['/my/rubros', '/my/rubros/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rubros(self, page=1, search=None, active='active', sort_by='name', location='all', **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        Apu = request.env['geosis.apu'].sudo()
        domain = []
        if search:
            domain += ['|', '|', ('name', 'ilike', search), ('code', 'ilike', search), ('uom_name', 'ilike', search)]
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
            step=10,
        )
        rubros = Apu.search(domain, order=order, limit=10, offset=pager['offset'])

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
            'rubro_avg_total': (sum(Apu.search(domain).mapped('total_cost')) / Apu.search_count(domain)) if Apu.search_count(domain) else 0.0,
            'rubro_created': kw.get('success') == 'rubro_created',
            'rubro_updated': kw.get('success') == 'rubro_updated',
            'rubro_deleted': kw.get('success') == 'rubro_deleted',
        }
        return request.render("geosis_website.portal_my_rubros", values)

    @http.route(['/my/rubro/<int:apu_id>', '/my/rubro/<int:apu_id>/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rubro_detail(self, apu_id, page=1, **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if not apu.exists():
            return request.redirect('/my/rubros')
        resource_categories = {}
        for cat in request.env['geosis.resource.category'].sudo().search([]):
            resource_categories[cat.id] = {'label': cat.name, 'description': cat.code}
            
        resource_domain = [('active', '=', True)]
        if apu.location:
            resource_domain += [('location', 'in', [apu.location, False, ''])]
        resource_available = request.env['geosis.resource'].sudo().search(resource_domain, order='category_id, name asc')

        resource_grouped_lines = {cid: [] for cid in resource_categories}
        resource_subtotals = {cid: 0.0 for cid in resource_categories}
        for line in apu.line_ids.sorted(lambda l: (l.sequence, l.id)):
            cat_id = line.category_id.id or line.resource_id.category_id.id
            if cat_id not in resource_grouped_lines:
                resource_grouped_lines[cat_id] = []
                resource_subtotals[cat_id] = 0.0
            resource_grouped_lines[cat_id].append(line)
            resource_subtotals[cat_id] += (line.cost or 0.0)

        lines = apu.line_ids.sorted(lambda l: (l.sequence, l.id))
        line_count = len(lines)
        pager = portal_pager(
            url=f"/my/rubro/{apu_id}",
            total=line_count,
            page=page,
            step=10
        )
        lines_paged = lines[pager['offset']:pager['offset'] + 10]

        values = {
            'apu': apu,
            'lines_paged': lines_paged,
            'pager': pager,
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
                    'indirect_percent': self._parse_portal_float(kw.get('indirect_percent'), 0.0),
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
                    'indirect_percent': self._parse_portal_float(kw.get('indirect_percent'), 0.0),
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            apu.sudo().unlink()
        return request.redirect('/my/rubros?success=rubro_deleted')

    @http.route(['/my/rubro/resource/add', '/my/rubro/<int:apu_id>/add-resource'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_resource_add(self, apu_id=None, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        apu_id = apu_id or int(kw.get('apu_id'))
        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if not apu.exists():
            return request.redirect('/my/rubros')
        
        category = kw.get('category')
        category_id = int(category) if category and str(category).isdigit() else False
        resource = False
        
        Resource = request.env['geosis.resource'].sudo()
        if kw.get('resource_id'):
            resource = Resource.browse(int(kw.get('resource_id')))

        resource_name = kw.get('resource_name') or (resource.name if resource else False)
        if not resource:
            resource = Resource.create({
                'name': resource_name,
                'category_id': category_id,
                'uom_id': request.env.ref('uom.product_uom_unit').id,
                'price': float(kw.get('rate', 0)),
            })
            
        request.env['geosis.apu.line'].sudo().create({
            'apu_id': apu.id,
            'resource_id': resource.id,
            'category_id': category_id,
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        line = request.env['geosis.apu.line'].sudo().browse(line_id)
        if line.exists():
            apu_id = line.apu_id.id
            line.sudo().unlink()
        return request.redirect('/my/rubro/%s?resource_line_deleted=1' % apu_id)

    @http.route(['/my/rubro/<int:apu_id>/generate-ia'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_generate_ia(self, apu_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            apu.sudo().action_generate_with_ia()
        return request.redirect('/my/rubro/%s?ia_generated=1' % apu.id)

    @http.route(['/my/rubro/<int:apu_id>/update-indirects'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_rubro_update_indirects(self, apu_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        apu = request.env['geosis.apu'].sudo().browse(apu_id)
        if apu.exists():
            try:
                new_indirect = self._parse_portal_float(kw.get('indirect_percent'), apu.indirect_percent)
                apu.sudo().write({'indirect_percent': new_indirect})
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/rubro/%s?success=indirects_updated' % apu_id)

    @http.route(['/my/import-excel'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_import_excel(self, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        Resource = request.env['geosis.resource'].sudo()

        domain = [('active', '=', True)]
        if search:
            domain += ['|', '|',
                ('name', 'ilike', search),
                ('code', 'ilike', search),
                ('description', 'ilike', search),
            ]
        if category and category != 'all':
            domain += [('category_id.id', '=', int(category))]
            
        if location and location != 'all':
            domain += [('location', '=', location)]

        sortings = {
            'name':     {'label': 'Nombre A-Z',      'order': 'name asc'},
            'name_desc':{'label': 'Nombre Z-A',      'order': 'name desc'},
            'price':    {'label': 'Precio mayor',    'order': 'price desc'},
            'price_asc':{'label': 'Precio menor',    'order': 'price asc'},
            'category': {'label': 'Categoría',       'order': 'category_id, name'},
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

        # Obtener un conteo de cuántos APUs usan cada recurso cargado en esta página
        ApuLine = request.env['geosis.apu.line'].sudo()
        resource_apu_counts = {}
        if resources:
            for line in ApuLine.search([('resource_id', 'in', resources.ids)]):
                if line.apu_id and line.apu_id.active:
                    resource_apu_counts.setdefault(line.resource_id.id, set()).add(line.apu_id.id)
        
        resource_counts = {r_id: len(apu_ids) for r_id, apu_ids in resource_apu_counts.items()}

        values = {
            'resources': resources,
            'resource_counts': resource_counts,
            'resource_total_count': resource_count,
            'resource_equipment_count': Resource.search_count([('active', '=', True), ('category_id.code', '=', 'M')]),
            'resource_labor_count':     Resource.search_count([('active', '=', True), ('category_id.code', '=', 'N')]),
            'resource_material_count':  Resource.search_count([('active', '=', True), ('category_id.code', '=', 'O')]),
            'pager': pager,
            'search': search or '',
            'selected_category': category,
            'selected_location': location,
            'locations': sorted(locations),
            'categories': request.env['geosis.resource.category'].sudo().search([]),
            'sort_by': sort_by,
            'sortings': sortings,
            'page_name': 'resource',
            'success': kw.get('success'),
        }
        return request.render("geosis_website.portal_my_resources", values)

    def _process_portal_category(self, kw):
        category = kw.get('category')
        if category == 'other':
            new_cat_name = kw.get('new_category_name')
            if new_cat_name:
                new_cat = request.env['geosis.resource.category'].sudo().create({
                    'name': new_cat_name,
                    'code': new_cat_name[:2].upper(),
                })
                return new_cat.id
        try:
            return int(category) if category else False
        except (ValueError, TypeError):
            return False

    @http.route(['/my/resources/new'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_resource_new(self, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        Resource = request.env['geosis.resource'].sudo()
        Uom = request.env['uom.uom'].sudo()
        Inec = request.env['geosis.inec.index'].sudo()

        if request.httprequest.method == 'POST':
            try:
                vals = {
                    'code': kw.get('code') or False,
                    'name': kw.get('name'),
                    'category_id': self._process_portal_category(kw),
                    'uom_id': int(kw.get('uom_id')) if kw.get('uom_id') else False,
                    'price': self._parse_portal_float(kw.get('price'), 0.0),
                    'cpc_code': kw.get('cpc_code') or False,
                    'vae_percent': self._parse_portal_float(kw.get('vae_percent'), 0.0),
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
                    'categories': request.env['geosis.resource.category'].sudo().search([]),
                }
                return request.render("geosis_website.portal_resource_form", values)

        values = {
            'page_name': 'resource',
            'resource': False,
            'form_data': {'category_id': False, 'price': 0.0, 'vae_percent': 0.0, 'active': True},
            'selected_uom_id': '',
            'selected_inec_index_id': '',
            'uoms': Uom.search([], order='name asc'),
            'inec_indices': Inec.search([('active', '=', True)], order='code asc'),
            'error_message': False,
            'categories': request.env['geosis.resource.category'].sudo().search([]),
        }
        return request.render("geosis_website.portal_resource_form", values)

    @http.route(['/my/resources/<int:resource_id>'], type='http', auth="user", website=True)
    def portal_my_resource_detail(self, resource_id, **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        resource = request.env['geosis.resource'].sudo().browse(resource_id)
        if not resource.exists():
            return request.redirect('/my/resources')

        # Buscar todos los APUs que utilicen este recurso
        apu_lines = request.env['geosis.apu.line'].sudo().search([('resource_id', '=', resource.id)])
        apus = apu_lines.mapped('apu_id').filtered(lambda a: a.active)

        values = {
            'page_name': 'resource',
            'resource': resource,
            'success': kw.get('success'),
            'related_apus': apus,
        }
        return request.render("geosis_website.portal_my_resource_detail", values)

    @http.route(['/my/resources/<int:resource_id>/edit'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_my_resource_edit(self, resource_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
                    'category_id': self._process_portal_category(kw) or resource.category_id.id,
                    'uom_id': int(kw.get('uom_id')) if kw.get('uom_id') else False,
                    'price': self._parse_portal_float(kw.get('price'), resource.price),
                    'cpc_code': kw.get('cpc_code') or False,
                    'vae_percent': self._parse_portal_float(kw.get('vae_percent'), resource.vae_percent),
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
                    'categories': request.env['geosis.resource.category'].sudo().search([]),
                }
                return request.render("geosis_website.portal_resource_form", values)

        values = {
            'page_name': 'resource',
            'resource': resource,
            'form_data': resource.read([
                'code', 'name', 'category_id', 'uom_id', 'price', 'cpc_code',
                'vae_percent', 'inec_index_id', 'location', 'description', 'active'
            ])[0],
            'selected_uom_id': str(resource.uom_id.id or ''),
            'selected_inec_index_id': str(resource.inec_index_id.id or ''),
            'uoms': Uom.search([], order='name asc'),
            'inec_indices': Inec.search([('active', '=', True)], order='code asc'),
            'error_message': False,
            'categories': request.env['geosis.resource.category'].sudo().search([]),
        }
        return request.render("geosis_website.portal_resource_form", values)

    @http.route(['/my/resources/<int:resource_id>/update-price'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_resource_update_price(self, resource_id, **kw):
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        resource = request.env['geosis.resource'].sudo().browse(resource_id)
        if resource.exists():
            try:
                new_price = self._parse_portal_float(kw.get('price'), resource.price)
                resource.sudo().write({'price': new_price})
            except (ValueError, TypeError):
                pass
        return request.redirect('/my/resources?success=price_updated')

    # -------------------------------------------------------
    # PLANILLAS DE AVANCE (FISCALIZACIÓN)
    # -------------------------------------------------------

    @http.route(['/my/inec-indices', '/my/inec-indices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inec_indices(self, page=1, search=None, status='active', sort_by='code', **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        value_record = request.env['geosis.inec.index.value'].sudo().browse(value_id)
        if value_record.exists() and value_record.index_id.id == index_id:
            value_record.unlink()
            return request.redirect('/my/inec-indices/%s?success=value_deleted' % index_id)
        return request.redirect('/my/inec-indices/%s' % index_id)

    @http.route(['/my/estimations', '/my/estimations/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_estimations(self, page=1, search=None, state='all', **kw):
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        values = self._prepare_portal_layout_values()
        Estimation = request.env['geosis.estimation'].sudo()
        
        # Filtramos por los proyectos que pertenecen al cliente actual
        partner_domain = self._partner_domain()
        Project = request.env['geosis.project'].sudo()
        my_projects = Project.search(partner_domain)
        
        domain = [('project_id', 'in', my_projects.ids)]
        if search:
            domain += ['|', ('code', 'ilike', search), ('notes', 'ilike', search)]
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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        estimation = self._get_accessible_estimation(estimation_id)
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
        if not self._can_manage_admin_portal():
            return self._deny_portal_access()

        project_id = int(kw.get('project_id'))
        budget_id = int(kw.get('budget_id'))
        
        budget = self._get_accessible_budget(budget_id)
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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        estimation = self._get_accessible_estimation(estimation_id)
        if not estimation.exists():
            return request.redirect('/my/estimations')

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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        estimation = self._get_accessible_estimation(estimation_id)
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
        if self._is_portal_resident() or self._is_portal_appraiser():
            return self._deny_portal_access()

        projects = request.env['geosis.project'].sudo().search(self._partner_domain() + [
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

    @http.route(['/my/avaluos', '/my/avaluos/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_avaluos(self, page=1, search=None, sort_by='date', **kw):
        if not self._can_access_avaluos():
            return self._deny_portal_access()

        values = self._prepare_portal_layout_values()
        Avaluo = request.env['geosis.avaluo'].sudo()
        domain = self._get_avaluo_domain_for_current_user()
            
        if search:
            domain += ['|', '|', '|',
                ('name', 'ilike', search),
                ('title', 'ilike', search),
                ('owner_name', 'ilike', search),
                ('location', 'ilike', search)
            ]
            
        sortings = {
            'date': {'label': 'Fecha Reciente', 'order': 'date desc, id desc'},
            'name': {'label': 'Código', 'order': 'name asc'},
            'owner': {'label': 'Propietario', 'order': 'owner_name asc'},
        }
        order = sortings.get(sort_by, sortings['date'])['order']
        
        avaluo_count = Avaluo.search_count(domain)
        pager = portal_pager(
            url="/my/avaluos",
            url_args={'search': search, 'sort_by': sort_by},
            total=avaluo_count,
            page=page,
            step=10
        )
        avaluos = Avaluo.search(domain, order=order, limit=10, offset=pager['offset'])
        
        # Calcular métricas globales para las tarjetas superiores
        total_count = Avaluo.search_count(domain)
        inspected_count = Avaluo.search_count(domain + [('state', '=', 'inspected')])
        calculated_count = Avaluo.search_count(domain + [('state', '=', 'calculated')])
        approved_count = Avaluo.search_count(domain + [('state', '=', 'approved')])
        
        # Obtener peritos de la empresa del usuario
        commercial_partner = request.env.user.partner_id.commercial_partner_id
        has_perito_group = request.env.ref('geosis_base.group_geosis_portal_appraiser', raise_if_not_found=False)
        peritos = request.env['res.users'].sudo()
        if has_perito_group:
            peritos = request.env['res.users'].sudo().search([
                ('partner_id', 'child_of', commercial_partner.id),
                ('groups_id', 'in', has_perito_group.id)
            ])
            
        values.update({
            'avaluos': avaluos,
            'peritos': peritos,
            'page_name': 'avaluo',
            'pager': pager,
            'search': search,
            'sort_by': sort_by,
            'sortings': sortings,
            'page_title': 'Avalúos Inmobiliarios',
            'page_subtitle': 'Seguimiento, inspección de campo y valoraciones de terrenos y edificaciones',
            'dashboard_metrics': {
                'total_count': total_count,
                'inspected_count': inspected_count,
                'calculated_count': calculated_count,
                'approved_count': approved_count,
            }
        })
        return request.render("geosis_website.portal_my_avaluos", values)

    @http.route(['/my/avaluo/<int:avaluo_id>'], type='http', auth="user", website=True)
    def portal_my_avaluo_detail(self, avaluo_id, **kw):
        if not self._can_access_avaluos():
            return self._deny_portal_access()

        Avaluo = request.env['geosis.avaluo'].sudo()
        avaluo = Avaluo.browse(avaluo_id)
        if not avaluo.exists():
            return request.redirect('/my/avaluos')

        domain = self._get_avaluo_domain_for_current_user() + [('id', '=', avaluo.id)]
        if not Avaluo.search_count(domain):
            return request.redirect('/my/avaluos')
            
        values = self._prepare_portal_layout_values()
        values.update({
            'avaluo': avaluo,
            'page_name': 'avaluo',
            'page_title': f"Detalle de Avalúo - {avaluo.name}",
            'page_subtitle': avaluo.title or 'Avalúo General',
        })
        return request.render("geosis_website.portal_my_avaluo_detail", values)

    @http.route('/my/avaluos/nueva', type='http', auth="user", methods=['POST'], website=True)
    def portal_my_avaluos_nueva(self, **post):
        if not self._can_access_avaluos():
            return self._deny_portal_access()

        title = post.get('title')
        owner_name = post.get('owner_name')
        location = post.get('location')
        appraiser_id = post.get('appraiser_id')
        date_avaluo = post.get('date_avaluo')

        if not all([title, appraiser_id, date_avaluo]):
            return request.redirect('/my/avaluos?error=missing_fields')

        Avaluo = request.env['geosis.avaluo'].sudo()
        Avaluo.create({
            'title': title,
            'owner_name': owner_name,
            'location': location,
            'inspector_id': int(appraiser_id),
            'date': date_avaluo,
            'state': 'draft',
            'partner_id': request.env.user.partner_id.id
        })

        return request.redirect('/my/avaluos?success=created')
