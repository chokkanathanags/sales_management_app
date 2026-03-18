from odoo import models, fields, api
from odoo.exceptions import ValidationError


class GoldRate(models.Model):
    _name = 'gold.rate'
    _description = 'Gold Price Rate'
    _rec_name = 'name'
    _order = 'effective_date desc'

    name = fields.Char(string='Rate Name', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    # Metal Type
    metal_type = fields.Selection([
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('platinum', 'Platinum'),
        ('palladium', 'Palladium'),
    ], string='Metal Type', default='gold', required=True)

    # Purity / Karat
    karat = fields.Selection([
        ('999', '24K (999)'),
        ('916', '22K (916)'),
        ('750', '18K (750)'),
        ('585', '14K (585)'),
        ('custom', 'Custom'),
    ], string='Karat/Purity', default='916')
    purity_factor = fields.Float(string='Purity Factor', default=0.916)

    # Rates
    price_per_gram = fields.Float(string='Price per Gram (INR)', required=True, default=0.0)
    price_per_10g = fields.Float(string='Price per 10g (INR)', compute='_compute_rates', store=True, readonly=True)
    price_per_tola = fields.Float(string='Price per Tola (INR)', compute='_compute_rates', store=True, readonly=True)

    # Date & Source
    effective_date = fields.Datetime(string='Effective From', required=True, default=fields.Datetime.now)
    expiry_date = fields.Datetime(string='Effective To')
    rate_source = fields.Selection([
        ('ibja', 'IBJA'),
        ('mcx', 'MCX'),
        ('local', 'Local Market'),
        ('custom', 'Custom/Manual'),
    ], string='Rate Source', default='custom')
    
    @api.constrains('effective_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.expiry_date and rec.expiry_date <= rec.effective_date:
                raise ValidationError("Expiry date must be after the effective date.")
    region = fields.Char(string='Region (for regional rates)')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
    ], string='Status', default='draft', index=True)

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_deprecate(self):
        for rec in self:
            rec.state = 'deprecated'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(GoldRate, self).create(vals_list)
        for rec in records:
            if rec.price_per_gram > 0:
                self.env['gold.price.history'].create({
                    'rate_id': rec.id,
                    'old_price': 0.0,
                    'new_price': rec.price_per_gram,
                    'changed_by': self.env.user.name,
                    'reason': 'Initial Rate Creation',
                    'approval_state': 'approved',
                })
        return records

    def write(self, vals):
        # Auto-track price history if price_per_gram changes
        if 'price_per_gram' in vals:
            for rec in self:
                old_price = rec.price_per_gram
                new_price = vals['price_per_gram']
                if old_price != new_price:
                    self.env['gold.price.history'].create({
                        'rate_id': rec.id,
                        'old_price': old_price,
                        'new_price': new_price,
                        'changed_by': self.env.user.name,
                        'reason': 'Rate Update',
                        'approval_state': 'approved', 
                    })
        return super(GoldRate, self).write(vals)

    # Price Components
    making_charge_fixed = fields.Float(string='Making Charge (Fixed)')
    making_charge_pct = fields.Float(string='Making Charge (%)')
    wastage_pct = fields.Float(string='Wastage (%)', default=0.0)
    gst_gold = fields.Float(string='GST on Gold (%)', default=3.0)
    gst_making = fields.Float(string='GST on Making (%)', default=5.0)
    gst_diamond = fields.Float(string='GST on Diamond (%)', default=18.0)

    @api.constrains('price_per_gram')
    def _check_price(self):
        for rec in self:
            if rec.price_per_gram <= 0:
                raise ValidationError("Price per gram must be greater than zero.")

    # Price List
    pricelist_id = fields.Many2one('gold.pricelist', string='Price List')
    price_history_ids = fields.One2many('gold.price.history', 'rate_id', string='Price History')

    @api.constrains('price_per_gram')
    def _check_price(self):
        for rec in self:
            if rec.price_per_gram <= 0:
                raise ValidationError("Price per gram must be greater than zero.")
    @api.depends('price_per_gram')
    def _compute_rates(self):
        for rec in self:
            rec.price_per_10g = rec.price_per_gram * 10
            rec.price_per_tola = rec.price_per_gram * 11.6638


class GoldPricelist(models.Model):
    _name = 'gold.pricelist'
    _description = 'Gold Price List'
    _rec_name = 'name'

    name = fields.Char(string='Price List Name', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(string='Active', default=True)

    channel = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline / Store'),
        ('corporate', 'Corporate'),
        ('all', 'All Channels'),
    ], string='Channel', default='all')

    segment_id = fields.Many2one('gold.segment', string='Customer Segment')
    region = fields.Char(string='Region')

    start_date = fields.Date(string='Valid From')
    end_date = fields.Date(string='Valid To')
    priority = fields.Integer(string='Priority', default=10)

    description = fields.Text(string='Description')
    rate_ids = fields.One2many('gold.rate', 'pricelist_id', string='Rates')


class GoldPriceHistory(models.Model):
    _name = 'gold.price.history'
    _description = 'Gold Price History'
    _order = 'change_date desc'

    rate_id = fields.Many2one('gold.rate', string='Rate', required=True)
    old_price = fields.Float(string='Old Price per Gram')
    new_price = fields.Float(string='New Price per Gram')
    change_date = fields.Datetime(string='Changed On', default=fields.Datetime.now)
    changed_by = fields.Char(string='Changed By')
    reason = fields.Text(string='Reason for Change')
    approved_by = fields.Char(string='Approved By')
    approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval State', default='pending')
