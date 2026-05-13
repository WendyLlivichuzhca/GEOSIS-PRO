from odoo import http
from odoo.http import request


class GeosisWebsiteController(http.Controller):
    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def geosis_homepage(self, **kw):
        return request.render('website.homepage')

    @http.route('/plataforma', type='http', auth='public', website=True, sitemap=True)
    def geosis_platform_page(self, **kw):
        return request.render('geosis_website.geosis_public_platform_page')

    @http.route('/flujo', type='http', auth='public', website=True, sitemap=True)
    def geosis_flow_page(self, **kw):
        return request.render('geosis_website.geosis_public_flow_page')

    @http.route('/geosis/home-data', type='json', auth='public', website=True)
    def geosis_home_data(self):
        resource_count = request.env['geosis.resource'].sudo().search_count([('active', '=', True)])
        apu_count = request.env['geosis.apu'].sudo().search_count([('active', '=', True)])
        budget_count = request.env['geosis.budget'].sudo().search_count([('active', '=', True)])
        project_count = request.env['geosis.project'].sudo().search_count([('active', '=', True)])
        return {
            'resources': resource_count,
            'apus': apu_count,
            'budgets': budget_count,
            'projects': project_count,
        }
