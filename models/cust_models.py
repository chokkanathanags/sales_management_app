from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class GoldCustomer(models.Model):
    _name = 'gold.customer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Gold Customer'
    _rec_name = 'name'
    _order = 'name'

    # Core Identity
    name = fields.Char(string='Customer Name', required=True, tracking=True)
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    partner_id = fields.Many2one('res.partner', string='Related Odoo Partner')
    unique_customer_id = fields.Char(string='Unique Customer ID', copy=False, index=True)
    active = fields.Boolean(string='Active', default=True)
    image = fields.Binary(string='Profile Photo')

    # Contact
    mobile = fields.Char(string='Mobile (Primary)', required=True, index=True, tracking=True)
    mobile_verified = fields.Boolean(string='Mobile OTP Verified')
    email = fields.Char(string='Email', required=True, index=True, tracking=True)
    email_verified = fields.Boolean(string='Email Verified')

    # Personal Info
    date_of_birth = fields.Date(string='Date of Birth')
    anniversary_date = fields.Date(string='Anniversary Date')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not', 'Prefer Not to Say'),
    ], string='Gender')
    occupation = fields.Char(string='Occupation')
    language = fields.Char(string='Preferred Language', default='English')

    # Corporate
    company_name = fields.Char(string='Company Name')
    gst_number = fields.Char(string='GST Number')
    pan_number = fields.Char(string='PAN Number')
    aadhaar_number = fields.Char(string='Aadhaar (Optional)')
    credit_limit = fields.Float(string='Credit Limit (Corporate)')

    # Addresses
    shipping_address = fields.Text(string='Default Shipping Address')
    billing_address = fields.Text(string='Default Billing Address')
    address_labels = fields.Text(string='Saved Addresses (JSON)')

    # Preferences
    preferred_store = fields.Char(string='Preferred Store')
    comm_email = fields.Boolean(string='Email Communication', default=True)
    comm_sms = fields.Boolean(string='SMS Communication', default=True)
    comm_whatsapp = fields.Boolean(string='WhatsApp Communication', default=True)
    browsing_history = fields.Text(string='Browsing History (JSON)')
    wishlist = fields.Text(string='Wishlist Items (JSON)')
    saved_payment_tokens = fields.Text(string='Saved Payment Tokens (JSON)')

    # Segment
    segment_id = fields.Many2one('gold.segment', string='Customer Segment/Tier', tracking=True)
    segment_code = fields.Char(related='segment_id.code', string='Segment Code', store=True, readonly=True)
    auto_segment_rule = fields.Char(string='Auto-Segment Rule Applied')

    # Source & Acquisition
    customer_source = fields.Char(string='Customer Source')
    registration_date = fields.Datetime(string='Registration Date', default=fields.Datetime.now)

    # Analytics
    last_purchase_date = fields.Date(string='Last Purchase Date')
    total_purchase_value = fields.Float(string='Lifetime Purchase Value')
    total_purchase_count = fields.Integer(string='Total Purchase Count')
    avg_order_value = fields.Float(string='Average Order Value')
    clv = fields.Float(string='Customer Lifetime Value (CLV)')

    # Loyalty
    loyalty_points = fields.Float(string='Loyalty Points Balance')
    loyalty_points_lifetime = fields.Float(string='Lifetime Loyalty Points Earned')

    # Privacy
    consent_marketing = fields.Boolean(string='Marketing Consent', default=False)
    consent_data_sharing = fields.Boolean(string='Data Sharing Consent', default=False)
    data_retention_policy = fields.Char(string='Data Retention Policy')

    # Status
    state = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('vip', 'VIP'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ], string='Status', default='prospect', index=True)

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_make_vip(self):
        for rec in self:
            rec.state = 'vip'

    def action_deactivate(self):
        for rec in self:
            rec.state = 'inactive'

    def action_blacklist(self):
        for rec in self:
            rec.state = 'blacklisted'

    def action_earn_points(self, amount):
        """Earn points based on purchase amount (1% ratio)"""
        for rec in self:
            points_earned = amount * 0.01
            rec.loyalty_points += points_earned
            rec.loyalty_points_lifetime += points_earned

    def action_update_metrics(self):
        """Update lifetime value, order count, and segments"""
        for rec in self:
            orders = self.env['gold.purchase'].search([
                ('customer_id', '=', rec.id),
                ('state', '=', 'delivered')
            ])
            total_value = sum(orders.mapped('total_value'))
            rec.write({
                'total_purchase_value': total_value,
                'total_purchase_count': len(orders),
                'avg_order_value': total_value / len(orders) if orders else 0.0,
                'last_purchase_date': orders[0].delivery_date.date() if orders else False
            })
            
            # Auto-segmentation Logic (Standardized)
            new_seg_code = False
            if total_value >= 500000:
                new_seg_code = 'diamond'
            elif total_value >= 100000:
                new_seg_code = 'gold'
            elif total_value >= 50000:
                new_seg_code = 'silver'
            
            if new_seg_code:
                seg = self.env['gold.segment'].search([('code', '=', new_seg_code)], limit=1)
                if seg:
                    rec.write({'segment_id': seg.id})
                    if new_seg_code == 'diamond':
                        rec.write({'state': 'vip'})
                    else:
                        rec.write({'state': 'active'})

    # Stat Buttons Data
    order_count = fields.Integer(string='Order Count', compute='_compute_order_count')

    def _compute_order_count(self):
        for rec in self:
            rec.order_count = self.env['gold.purchase'].search_count([('customer_id', '=', rec.id)])

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orders',
            'view_mode': 'tree,form',
            'res_model': 'gold.purchase',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
    code = fields.Char(string='Customer Code')
    description = fields.Text(string='Notes')
    category = fields.Char(string='Category')
    karat = fields.Char(string='Preferred Karat')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')
    currency_name = fields.Char(string='Currency', default='INR')
    type = fields.Char(string='Type')

    # Smart Button Fields
    payment_ids = fields.One2many('gold.payment', 'customer_id', string='Payments')
    payment_count = fields.Integer(string='Payment Count', compute='_compute_payment_count')

    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    # Validations
    @api.constrains('name')
    def _check_name_length(self):
        for rec in self:
            if rec.name and len(rec.name.strip()) < 3:
                raise ValidationError(_("Customer name must be at least 3 characters long."))

    @api.constrains('email')
    def _check_email_format(self):
        for rec in self:
            if rec.email:
                if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", rec.email):
                    raise ValidationError(_("Please enter a valid email address (e.g., customer@example.com)."))
                
                # Uniqueness check
                duplicate = self.search([('email', '=', rec.email), ('id', '!=', rec.id)])
                if duplicate:
                    raise ValidationError(_("A customer with this email already exists."))

    @api.constrains('mobile')
    def _check_mobile_format(self):
        for rec in self:
            if rec.mobile:
                if not re.match(r"^\+?[0-9]{10,15}$", rec.mobile):
                    raise ValidationError(_("Please enter a valid mobile number (10-15 digits)."))
                
                # Uniqueness check
                duplicate = self.search([('mobile', '=', rec.mobile), ('id', '!=', rec.id)])
                if duplicate:
                    raise ValidationError(_("A customer with this mobile number already exists."))

    @api.constrains('gst_number')
    def _check_gst_number(self):
        for rec in self:
            if rec.gst_number and not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", rec.gst_number):
                raise ValidationError(_("Invalid GST Number format."))

    @api.constrains('pan_number')
    def _check_pan_number(self):
        for rec in self:
            if rec.pan_number and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", rec.pan_number):
                raise ValidationError(_("Invalid PAN Number format."))

    @api.constrains('aadhaar_number')
    def _check_aadhaar_number(self):
        for rec in self:
            if rec.aadhaar_number and not re.match(r"^[2-9]{1}[0-9]{3}\\s[0-9]{4}\\s[0-9]{4}$|^[2-9]{1}[0-9]{11}$", rec.aadhaar_number):
                raise ValidationError(_("Invalid Aadhaar Number format (12 digits required)."))

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > fields.Date.today():
                raise ValidationError(_("Date of birth cannot be in the future."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New' or not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('gold.customer.seq') or 'New'
        return super(GoldCustomer, self).create(vals_list)

    def action_view_payments(self):
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'gold.payment',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
