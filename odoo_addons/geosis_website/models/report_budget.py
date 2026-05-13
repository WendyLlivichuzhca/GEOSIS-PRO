from odoo import models


class GeosisBudgetPortalReport(models.AbstractModel):
    _name = 'report.geosis_website.report_geosis_budget_portal'
    _description = 'Reporte PDF Portal Presupuesto GEOSIS'

    def _get_report_values(self, docids, data=None):
        user = self.env.user
        Budget = self.env['geosis.budget'].sudo()
        domain = [('id', 'in', docids)]

        if not user.has_group('base.group_user'):
            partner = user.partner_id.commercial_partner_id
            domain.append(('partner_id', 'child_of', partner.id))

        docs = Budget.search(domain, order='budget_date desc, id desc')
        return {
            'doc_ids': docs.ids,
            'doc_model': 'geosis.budget',
            'docs': docs,
        }
