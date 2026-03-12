from odoo import models, fields, api
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

    # Type
    promotion_type = fields.Selection([
        ('percentage', 'Percentage Discount on Product'),
        ('flat', 'Flat Amount Discount on Product'),
        ('bogo', 'Buy X Get Y (BOGO)'),
        ('bogo_pct', 'Buy X Get Y% Off'),
        ('cart', 'Cart-Level Discount (Min Purchase)'),
        ('category', 'Category-Wide Discount'),
        ('brand', 'Brand/Collection Discount'),
        ('making_waiver', 'Making Charges Waiver'),
        ('wastage_waiver', 'Wastage Waiver'),
        ('flash', 'Flash Sale with Countdown'),
        ('first_purchase', 'First Purchase Discount'),
        ('payment_method', 'Payment Method Discount'),
        ('free_shipping', 'Free Shipping'),
        ('loyalty_multiplier', 'Loyalty Points Multiplier'),
        ('tiered', 'Tiered Discount (Spend More Save More)'),
        ('bundle', 'Bundle Offer'),
        ('gift', 'Gift with Purchase'),
    ], string='Promotion Type', required=True, default='percentage')

    # Discount Values
    discount_pct = fields.Float(string='Discount (%)')
    discount_amount = fields.Float(string='Discount Amount (Flat)')
    buy_qty = fields.Integer(string='Buy Qty (BOGO)')
    get_qty = fields.Integer(string='Get Qty (BOGO)')
    max_discount_cap = fields.Float(string='Maximum Discount Cap per Order')

    # Conditions
    min_cart_value = fields.Float(string='Minimum Cart Value')
    applicable_category = fields.Char(string='Applicable Category')
    applicable_channel = fields.Selection([
        ('online', 'Online Only'),
        ('offline', 'Store Only'),
        ('all', 'All Channels'),
    ], string='Applicable Channel', default='all')
    applicable_payment_method = fields.Char(string='Payment Method (for payment discount)')
    customer_segment = fields.Char(string='Customer Segment')
    applicable_product_ids = fields.Char(string='Applicable Product SKUs (comma-separated)')
    exclusion_product_ids = fields.Char(string='Excluded Product SKUs')

    # Validity
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    priority = fields.Integer(string='Priority', default=10)
    can_stack = fields.Boolean(string='Can Stack with other Promotions?', default=False)

    # Usage Limits
    usage_limit_total = fields.Integer(string='Total Redemption Limit', default=0)
    usage_limit_per_customer = fields.Integer(string='Per Customer Limit', default=1)
    times_used = fields.Integer(string='Times Used', default=0, readonly=True)

    # Loyalty
    loyalty_multiplier = fields.Float(string='Loyalty Points Multiplier', default=1.0)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')

    # Analytics
    total_discount_given = fields.Float(string='Total Discount Given', readonly=True)
    total_orders = fields.Integer(string='Total Orders Used', readonly=True)
    roi = fields.Float(string='ROI (%)', readonly=True)

    # Coupon Lines
    coupon_ids = fields.One2many('gold.coupon', 'promotion_id', string='Coupons')

    def action_generate_coupons(self):
        for rec in self:
            for _ in range(10):  # Generate 10 coupons by default
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                self.env['gold.coupon'].create({
                    'name': code,
                    'promotion_id': rec.id,
                    'max_uses': rec.usage_limit_per_customer,
                })


class GoldCoupon(models.Model):
    _name = 'gold.coupon'
    _description = 'Gold Coupon'
    _rec_name = 'name'

    name = fields.Char(string='Coupon Code', required=True, copy=False)
    promotion_id = fields.Many2one('gold.promotions', string='Promotion', required=True)
    max_uses = fields.Integer(string='Max Uses', default=1)
    times_used = fields.Integer(string='Times Used', default=0, readonly=True)
    expiry_date = fields.Date(string='Expiry Date')
    state = fields.Selection([
        ('active', 'Active'),
        ('exhausted', 'Exhausted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='active')
    customer_id = fields.Many2one('gold.customer', string='Assigned to Customer')
