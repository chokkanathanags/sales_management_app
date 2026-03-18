from odoo import models, fields, api, _

class GoldSegment(models.Model):
    _name = 'gold.segment'
    _description = 'Customer Segment / Tier'
    _rec_name = 'name'
    _order = 'sequence, id'

    name = fields.Char(string='Segment Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Priority Sequence', default=10)
    
    min_lifetime_value = fields.Float(string='Minimum Lifetime Value (INR)', help="Orders over this value auto-promote customers to this segment.")
    
    active = fields.Boolean(string='Active', default=True)
    
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Segment code must be unique!')
    ]
