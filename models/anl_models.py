from odoo import models, fields, api

class GoldAnalyticsDashboard(models.Model):
    _name = 'gold.analytics.dashboard'
    _description = 'Gold ERP Analytics Dashboard'

    name = fields.Char(string='Dashboard Name', default='Main Dashboard')
