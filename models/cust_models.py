from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class GoldCustomer(models.Model):
    _name = 'gold.customer'
    _description = 'Gold Customer'
    _rec_name = 'name'
    _order = 'name'

    # Core Identity
    name = fields.Char(string='Customer Name', required=True)
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    partner_id = fields.Many2one('res.partner', string='Related Odoo Partner')
    unique_customer_id = fields.Char(string='Unique Customer ID', copy=False, index=True)
    active = fields.Boolean(string='Active', default=True)
    image = fields.Binary(string='Profile Photo')

    # Contact
    mobile = fields.Char(string='Mobile (Primary)', required=True, index=True)
    mobile_verified = fields.Boolean(string='Mobile OTP Verified')
    email = fields.Char(string='Email', required=True, index=True)
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

    # Addresses (multi-address via text for simplicity; extend with One2many if needed)
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
    segment = fields.Selection([
        ('regular', 'Regular'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('vip', 'VIP'),
        ('diamond', 'Diamond'),
        ('corporate', 'Corporate'),
        ('wholesale', 'Wholesale'),
        ('employee', 'Employee'),
        ('influencer', 'Influencer'),
    ], string='Customer Segment/Tier', default='regular')
    auto_segment_rule = fields.Char(string='Auto-Segment Rule Applied')

    # Source & Acquisition
    customer_source = fields.Char(string='Customer Source')
    registration_date = fields.Datetime(string='Registration Date', default=fields.Datetime.now)

    # Analytics (computed/updated from orders)
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

    # Custom Fields
    custom_field_1 = fields.Char(string='Custom Field 1')
    custom_field_2 = fields.Char(string='Custom Field 2')
    custom_field_3 = fields.Char(string='Custom Field 3')
    custom_field_4 = fields.Char(string='Custom Field 4')
    custom_field_5 = fields.Char(string='Custom Field 5')
    custom_field_6 = fields.Char(string='Custom Field 6')
    custom_field_7 = fields.Char(string='Custom Field 7')
    custom_field_8 = fields.Char(string='Custom Field 8')
    custom_field_9 = fields.Char(string='Custom Field 9')
    custom_field_10 = fields.Char(string='Custom Field 10')

    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ], string='Status', default='active')
    code = fields.Char(string='Customer Code')
    description = fields.Text(string='Notes')
    category = fields.Char(string='Category')
    karat = fields.Char(string='Preferred Karat')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')
    currency_name = fields.Char(string='Currency', default='INR')
    type = fields.Char(string='Type')

    @api.constrains('email')
    def _check_email_format(self):
        for rec in self:
            if rec.email:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", rec.email):
                    raise ValidationError("Please enter a valid email address (e.g., customer@example.com).")

    @api.constrains('mobile')
    def _check_mobile_format(self):
        for rec in self:
            if rec.mobile:
                if not rec.mobile.isdigit() or len(rec.mobile) < 10:
                    raise ValidationError("Please enter a valid mobile number with at least 10 digits.")

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > fields.Date.today():
                raise ValidationError("Date of birth cannot be in the future.")
