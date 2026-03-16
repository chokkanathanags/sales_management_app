from odoo import models, fields, api

class GoldAnalyticsDashboard(models.Model):
    _name = 'gold.analytics.dashboard'
    _description = 'Gold ERP Analytics Dashboard'
    _auto = False  # View only model

    def init(self):
        # Placeholder for complex SQL view if needed
        pass
