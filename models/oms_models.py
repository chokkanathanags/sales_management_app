from odoo import models, fields, api
from odoo.exceptions import ValidationError


class GoldPurchase(models.Model):
    _name = 'gold.purchase'
    _description = 'Gold Order (OMS)'
    _rec_name = 'name'
    _order = 'order_date desc'

    name = fields.Char(string='Order Reference', required=True, default='New', copy=False, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_id = fields.Many2one('gold.customer', string='Gold Customer', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Source
    order_source = fields.Selection([
        ('online', 'Online'),
        ('app', 'Mobile App'),
        ('phone', 'Phone'),
        ('store', 'Store'),
        ('api', 'API'),
    ], string='Order Source', default='online')
    device_type = fields.Selection([
        ('mobile', 'Mobile'),
        ('desktop', 'Desktop'),
        ('tablet', 'Tablet'),
    ], string='Device Type')

    # Special Order Types
    order_type = fields.Selection([
        ('regular', 'Regular'),
        ('customization', 'Customization (Engraving/Resizing)'),
        ('made_to_order', 'Made to Order'),
        ('try_at_home', 'Try at Home'),
        ('preorder', 'Pre-Order / Advance Booking'),
        ('bopis', 'BOPIS (Buy Online, Pick-up In Store)'),
        ('click_collect', 'Click & Collect'),
        ('ship_to_store', 'Ship to Store'),
    ], string='Order Type', default='regular')

    # Order Lines
    order_line_ids = fields.One2many('gold.purchase.line', 'order_id', string='Order Lines')

    # Fulfillment
    fulfillment_model = fields.Selection([
        ('warehouse', 'Ship from Warehouse'),
        ('ship_from_store', 'Ship from Store'),
        ('bopis', 'BOPIS Pickup'),
        ('click_collect', 'Click & Collect'),
        ('ship_to_store', 'Ship to Store'),
        ('same_day', 'Same Day Delivery'),
        ('scheduled', 'Scheduled Delivery'),
    ], string='Fulfillment Model', default='warehouse')
    fulfillment_store = fields.Char(string='Fulfillment Store/Location')
    routing_override = fields.Char(string='Manual Routing Override')

    # Addresses
    shipping_address = fields.Text(string='Shipping Address')
    billing_address = fields.Text(string='Billing Address')
    pincode = fields.Char(string='Delivery Pincode')
    delivery_instructions = fields.Text(string='Delivery Instructions')

    # Delivery
    expected_delivery_date = fields.Date(string='Expected Delivery Date')
    delivery_slot = fields.Char(string='Delivery Time Slot')
    scheduled_delivery_date = fields.Date(string='Scheduled Delivery Date')
    is_gift = fields.Boolean(string='Gift Order')
    gift_message = fields.Text(string='Gift Message')
    gift_wrapping = fields.Boolean(string='Gift Wrapping')

    # Pricing Summary
    karat = fields.Char(string='Karat')
    subtotal = fields.Float(string='Subtotal')
    discount_amount = fields.Float(string='Discount Amount')
    making_charge = fields.Float(string='Making Charges')
    wastage_charge = fields.Float(string='Wastage Charges')
    stone_cost = fields.Float(string='Stone Cost')
    cgst = fields.Float(string='CGST')
    sgst = fields.Float(string='SGST')
    igst = fields.Float(string='IGST')
    tax_amount = fields.Float(string='Total Tax')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    currency_name = fields.Char(string='Currency', default='INR')

    # Promotions
    promotion_id = fields.Many2one('gold.promotions', string='Promotion Applied')
    coupon_code = fields.Char(string='Coupon Code Used')

    # Loyalty
    loyalty_points_used = fields.Float(string='Loyalty Points Used')
    loyalty_points_earned = fields.Float(string='Loyalty Points Earned')

    # Payment
    payment_method = fields.Char(string='Payment Method')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ], string='Payment Status', default='pending')
    payment_transaction_id = fields.Char(string='Payment Transaction ID')
    advance_amount = fields.Float(string='Advance Paid')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('payment_pending', 'Payment Pending'),
        ('payment_received', 'Payment Received'),
        ('in_fulfillment', 'In Fulfillment'),
        ('quality_check', 'Quality Check'),
        ('packed', 'Packed'),
        ('dispatched', 'Dispatched'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('awaiting_pickup', 'Awaiting Pickup'),
        ('cancelled', 'Cancelled'),
        ('return_initiated', 'Return Initiated'),
        ('returned', 'Returned'),
        ('refunded', 'Refunded'),
    ], string='Order Status', default='draft', index=True)

    # Dates
    order_date = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    confirmation_date = fields.Datetime(string='Confirmed On')
    dispatch_date = fields.Datetime(string='Dispatched On')
    delivery_date = fields.Datetime(string='Delivered On')
    cancellation_date = fields.Datetime(string='Cancelled On')
    cancellation_reason = fields.Text(string='Cancellation Reason')

    # Customization
    customization_notes = fields.Text(string='Customization Details')
    engraving_text = fields.Char(string='Engraving Text')
    resize_spec = fields.Char(string='Resize Specification')

    # Webhook / External
    external_order_id = fields.Char(string='External Order ID', copy=False)
    api_idempotency_key = fields.Char(string='API Idempotency Key', copy=False)

    @api.constrains('total_value')
    def _check_total_value(self):
        for rec in self:
            if rec.total_value < 0:
                raise ValidationError("Total order value cannot be negative.")

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({'state': 'confirmed', 'confirmation_date': fields.Datetime.now()})

    def action_cancel(self):
        for rec in self:
            if rec.state in ('delivered', 'cancelled'):
                raise ValidationError("Cannot cancel an order that is already delivered or cancelled.")
            rec.write({'state': 'cancelled', 'cancellation_date': fields.Datetime.now()})

    def action_set_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_delivered(self):
        for rec in self:
            if rec.state != 'dispatched':
                raise ValidationError("Order must be dispatched before it can be marked as delivered.")
            rec.write({'state': 'delivered', 'delivery_date': fields.Datetime.now()})


class GoldPurchaseLine(models.Model):
    _name = 'gold.purchase.line'
    _description = 'Gold Order Line'

    order_id = fields.Many2one('gold.purchase', string='Order', required=True, ondelete='cascade')
    inventory_id = fields.Many2one('gold.inventory', string='Item')
    sku = fields.Char(string='SKU')
    name = fields.Char(string='Item Name', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    karat = fields.Char(string='Karat')
    gross_weight = fields.Float(string='Gross Weight (g)', digits=(10,3))
    net_weight = fields.Float(string='Net Weight (g)', digits=(10,3))
    base_value = fields.Float(string='Base Value')
    making_charge = fields.Float(string='Making Charge')
    wastage_charge = fields.Float(string='Wastage Charge')
    stone_cost = fields.Float(string='Stone Cost')
    discount_amount = fields.Float(string='Discount')
    tax_amount = fields.Float(string='Tax')
    line_total = fields.Float(string='Line Total')
    rate_id = fields.Many2one('gold.rate', string='Gold Rate at Order Time')
    customization = fields.Text(string='Customization Notes')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ], string='Line Status', default='pending')

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")
