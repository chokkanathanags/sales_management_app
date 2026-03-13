from odoo import models, fields, api
from odoo.exceptions import ValidationError
import random
import string


class GoldPromotions(models.Model):
    _name = 'gold.promotions'
    _description = 'Gold Promotions & Discounts'
    _rec_name = 'name'
    _order = 'start_date desc'

    name = fields.Char(string='Promotion Name', required=True)
    code = fields.Char(string='Promo Code', copy=False)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    priority = fields.Integer(string='Priority', default=10)
    can_stack = fields.Boolean(string='Can Stack with Other Promotions?', default=False)

    promotion_type = fields.Selection([
        ('percentage',         'Percentage Discount on Product'),
        ('flat',               'Flat Amount Discount on Product'),
        ('bogo',               'Buy X Get Y (BOGO)'),
        ('bogo_pct',           'Buy X Get Y% Off'),
        ('cart',               'Cart-Level Discount (Min Purchase)'),
        ('category',           'Category-Wide Discount'),
        ('brand',              'Brand / Collection Discount'),
        ('making_waiver',      'Making Charges Waiver'),
        ('wastage_waiver',     'Wastage Waiver'),
        ('flash',              'Flash Sale with Countdown'),
        ('first_purchase',     'First Purchase Discount'),
        ('payment_method',     'Payment Method Discount'),
        ('free_shipping',      'Free Shipping'),
        ('loyalty_multiplier', 'Loyalty Points Multiplier'),
        ('tiered',             'Tiered Discount (Spend More Save More)'),
        ('bundle',             'Bundle Offer'),
        ('gift',               'Gift with Purchase'),
    ], string='Promotion Type', required=True, default='percentage')

    discount_pct = fields.Float(string='Discount (%)', default=0.0)
    discount_amount = fields.Float(string='Discount Amount (Flat)', default=0.0)
    max_discount_cap = fields.Float(string='Maximum Discount Cap per Order')
    buy_qty = fields.Integer(string='Buy Qty (BOGO)', default=1)
    get_qty = fields.Integer(string='Get Qty (BOGO)', default=1)
    loyalty_multiplier = fields.Float(string='Loyalty Points Multiplier', default=1.0)

    @api.constrains('discount_pct', 'discount_amount')
    def _check_discount(self):
        for rec in self:
            if not (0.0 <= rec.discount_pct <= 100.0):
                raise ValidationError("Discount percentage must be between 0 and 100.")
            if rec.discount_amount < 0:
                raise ValidationError("Discount amount cannot be negative.")

    applicable_category = fields.Char(string='Applicable Category')

    min_cart_value = fields.Float(string='Minimum Cart Value')
    applicable_channel = fields.Selection([
        ('online',  'Online Only'),
        ('offline', 'Store Only'),
        ('all',     'All Channels'),
    ], string='Applicable Channel', default='all')
    applicable_payment_method = fields.Char(string='Payment Method')
    customer_segment = fields.Char(string='Customer Segment')
    applicable_product_ids = fields.Char(string='Applicable Product SKUs')
    exclusion_product_ids = fields.Char(string='Excluded Product SKUs')

    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date <= rec.start_date:
                raise ValidationError("End Date must be after Start Date.")

    usage_limit_total = fields.Integer(string='Total Redemption Limit', default=0)
    usage_limit_per_customer = fields.Integer(string='Per Customer Limit', default=1)
    times_used = fields.Integer(string='Times Used', default=0, readonly=True)

    state = fields.Selection([
        ('draft',            'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active',           'Active'),
        ('expired',          'Expired'),
        ('cancelled',        'Cancelled'),
    ], string='Status', default='draft')

    total_discount_given = fields.Float(string='Total Discount Given', readonly=True)
    total_orders = fields.Integer(string='Total Orders Used', readonly=True)
    roi = fields.Float(string='ROI (%)', readonly=True)

    coupon_ids = fields.One2many('gold.coupon', 'promotion_id', string='Coupons')
    coupon_count = fields.Integer(
        string='Coupon Count',
        compute='_compute_coupon_count',
        store=True,
    )

    @api.depends('coupon_ids')
    def _compute_coupon_count(self):
        for rec in self:
            rec.coupon_count = len(rec.coupon_ids)

    def action_submit_for_approval(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("Only Draft promotions can be submitted for approval.")
            rec.state = 'pending_approval'

    def action_approve(self):
        for rec in self:
            if rec.state != 'pending_approval':
                raise ValidationError("Only Pending Approval promotions can be approved.")
            rec.state = 'active'

    def action_reject(self):
        for rec in self:
            if rec.state != 'pending_approval':
                raise ValidationError("Only Pending Approval promotions can be rejected.")
            rec.state = 'draft'

    def action_expire(self):
        for rec in self:
            if rec.state != 'active':
                raise ValidationError("Only Active promotions can be manually expired.")
            rec.state = 'expired'

    def action_cancel(self):
        for rec in self:
            if rec.state != 'cancelled':
                rec.state = 'cancelled'

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ('cancelled', 'expired'):
                raise ValidationError("Only Cancelled or Expired promotions can be reset to Draft.")
            rec.state = 'draft'

    def action_generate_coupons(self):
        for rec in self:
            if rec.state != 'active':
                raise ValidationError("Coupons can only be generated for Active promotions.")
            existing_codes = set(rec.coupon_ids.mapped('name'))
            created = 0
            attempts = 0
            while created < 10 and attempts < 200:
                attempts += 1
                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                code = f"{rec.code or 'CPN'}-{suffix}"
                if code not in existing_codes:
                    self.env['gold.coupon'].create({
                        'name': code,
                        'promotion_id': rec.id,
                        'max_uses': rec.usage_limit_per_customer or 1,
                    })
                    existing_codes.add(code)
                    created += 1

    def action_view_coupons(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Coupons — {self.name}',
            'res_model': 'gold.coupon',
            'view_mode': 'tree,form',
            'domain': [('promotion_id', '=', self.id)],
            'context': {'default_promotion_id': self.id},
        }


class GoldCoupon(models.Model):
    _name = 'gold.coupon'
    _description = 'Gold Promotion Coupon'
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Coupon Code', required=True, copy=False)
    promotion_id = fields.Many2one(
        'gold.promotions', string='Promotion',
        required=True, ondelete='cascade'
    )
    max_uses = fields.Integer(string='Max Uses', default=1)
    times_used = fields.Integer(string='Times Used', default=0, readonly=True)
    expiry_date = fields.Date(string='Expiry Date')
    customer_id = fields.Many2one('gold.customer', string='Assigned to Customer')

    # FIX: removed buggy `if rec.state == 'cancelled': continue`
    # A computed field cannot read its own previous stored value inside the compute method.
    # Cancelled state is now only set via action_cancel() and is NOT overwritten by this compute.
    state = fields.Selection([
        ('active',    'Active'),
        ('exhausted', 'Exhausted'),
        ('expired',   'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='active')

    @api.depends('times_used', 'max_uses', 'expiry_date')
    def _compute_state(self):
        from odoo.fields import Date
        today = Date.today()
        for rec in self:
            # Do not overwrite manually cancelled coupons
            if rec.state == 'cancelled':
                continue
            if rec.expiry_date and rec.expiry_date < today:
                rec.state = 'expired'
            elif rec.max_uses > 0 and rec.times_used >= rec.max_uses:
                rec.state = 'exhausted'
            else:
                rec.state = 'active'

    @api.constrains('name')
    def _check_unique_code(self):
        for rec in self:
            domain = [('name', '=', rec.name), ('id', '!=', rec.id)]
            if self.search_count(domain):
                raise ValidationError(f"Coupon code '{rec.name}' already exists.")

    def action_cancel(self):
        self.write({'state': 'cancelled'})