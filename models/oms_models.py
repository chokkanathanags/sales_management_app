from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class GoldPurchase(models.Model):
    _name = 'gold.purchase'
    _description = 'Gold Order (OMS)'
    _rec_name = 'name'
    _order = 'order_date desc'

    name = fields.Char(string='Order Reference', copy=False, index=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_id = fields.Many2one('gold.customer', string='Gold Customer', required=True)
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('gold.purchase.seq') or 'New'
        return super(GoldPurchase, self).create(vals_list)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancelled'):
                raise UserError(f"Secure ERP Protection: You cannot delete Order '{order.name}' because it is in the '{dict(self._fields['state'].selection).get(order.state)}' state. Please cancel it first if you wish to remove it.")
        return super(GoldPurchase, self).unlink()

    # Source
    order_source = fields.Selection([
        ('online', 'Online'),
        ('app', 'Mobile App'),
        ('phone', 'Phone'),
        ('store', 'Store'),
        ('api', 'API'),
    ], string='Order Source', default='online')
    payment_method = fields.Selection([
        ('cod', 'Cash on Delivery (COD)'),
        ('card_debit', 'Debit Card'),
        ('card_credit', 'Credit Card'),
        ('upi', 'UPI / Online'),
        ('gold_exchange', 'Old Gold Exchange'),
        ('advance', 'Advance / Down Payment'),
    ], string='Payment Method', required=True, default='card_credit')
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ], string='Payment Status', default='unpaid')
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
    karat = fields.Char(string='Karat', compute='_compute_totals', store=True, readonly=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_totals', store=True, readonly=True)
    discount_amount = fields.Float(string='Discount Amount')
    making_charge = fields.Float(string='Making Charges')
    wastage_charge = fields.Float(string='Wastage Charges')
    stone_cost = fields.Float(string='Stone Cost')
    cgst = fields.Float(string='CGST')
    sgst = fields.Float(string='SGST')
    igst = fields.Float(string='IGST')
    tax_amount = fields.Float(string='Total Tax', compute='_compute_totals', store=True, readonly=True)
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value', compute='_compute_totals', store=True, readonly=True)
    currency_name = fields.Char(string='Currency', default='INR')

    # Promotions
    promotion_id = fields.Many2one('gold.promotions', string='Promotion Applied')
    coupon_code = fields.Char(string='Coupon Code Used')
    available_coupon_id = fields.Many2one('gold.coupon', string='Select Promocode', 
                                          domain="[('state', '=', 'active'), '|', ('customer_id', '=', False), ('customer_id', '=', customer_id)]")

    @api.onchange('available_coupon_id')
    def _onchange_available_coupon_id(self):
        if self.available_coupon_id:
            self.coupon_code = self.available_coupon_id.name
            # Automatically apply the coupon logic
            # Since action_apply_coupon returns an effect, we just want the side effects here
            self.action_apply_coupon()

    # Loyalty
    loyalty_points_used = fields.Float(string='Loyalty Points Used')
    loyalty_points_earned = fields.Float(string='Loyalty Points Earned', compute='_compute_loyalty_points_earned', store=True, readonly=True)

    @api.depends('total_value')
    def _compute_loyalty_points_earned(self):
        for rec in self:
            rec.loyalty_points_earned = rec.total_value * 0.01


    @api.depends('order_line_ids', 'loyalty_points_used', 'discount_amount')
    def _compute_totals(self):
        for rec in self:
            lines = rec.order_line_ids
            # Summary Karat from first line
            rec.karat = lines[0].karat if lines else ''
            
            untaxed_subtotal = sum(lines.mapped('base_value')) + \
                               sum(lines.mapped('making_charge')) + \
                               sum(lines.mapped('stone_cost'))
            
            total_tax = sum(lines.mapped('tax_amount'))
            
            loyalty_discount = rec.loyalty_points_used
            rec.subtotal = untaxed_subtotal
            rec.tax_amount = total_tax
            rec.total_value = untaxed_subtotal + total_tax - rec.discount_amount - loyalty_discount

    def action_redeem_loyalty(self):
        """Redeem available loyalty points for the current order"""
        for rec in self:
            if not rec.customer_id:
                raise ValidationError("Please select a customer first.")
            if rec.state != 'draft':
                raise ValidationError("Points can only be redeemed in Draft state.")
            
            available_points = rec.customer_id.loyalty_points
            if available_points <= 0:
                raise ValidationError("This customer has no loyalty points to redeem.")
            
            # Use points up to the order value
            points_to_use = min(available_points, rec.total_value)
            rec.write({
                'loyalty_points_used': points_to_use,
            })
            # Subtract from customer balance immediately to reserve them
            rec.customer_id.loyalty_points -= points_to_use

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
    
    def action_apply_coupon(self):
        """Apply a coupon code with strict validation: assignment, price range, and channel."""
        for rec in self:
            if not rec.coupon_code:
                raise ValidationError("Please enter a coupon code.")
            if rec.state != 'draft':
                raise ValidationError("Coupons can only be applied to Draft orders.")
            if not rec.customer_id:
                raise ValidationError("Please select a customer before applying a coupon.")

            code = rec.coupon_code.strip()
            # 1. Find the coupon
            coupon = self.env['gold.coupon'].search([('name', '=', code)], limit=1)
            if not coupon:
                raise ValidationError(f"Invalid coupon code: '{code}' not found.")

            # 2. Validate Coupon State & Promotion State
            if coupon.state != 'active':
                raise ValidationError(f"This coupon ('{code}') is currently {coupon.state}.")
            
            promo = coupon.promotion_id
            if promo.state != 'active' or not promo.active:
                raise ValidationError(f"The promotion '{promo.name}' is not currently active.")

            # 3. Check Dates
            now = fields.Datetime.now()
            if promo.start_date > now:
                raise ValidationError(f"Promotion '{promo.name}' hasn't started yet (Starts: {promo.start_date}).")
            if promo.end_date < now:
                raise ValidationError(f"Promotion '{promo.name}' expired on {promo.end_date}.")

            # 4. Check Customer Assignment (Specific Coupons)
            if coupon.customer_id and coupon.customer_id != rec.customer_id:
                raise ValidationError(f"Strict Security: This specific coupon is uniquely assigned to '{coupon.customer_id.name}'. You cannot use it for '{rec.customer_id.name}'.")

            # 5. Check Usage Limits (Customer level)
            usage_domain = [
                ('customer_id', '=', rec.customer_id.id),
                ('coupon_code', '=', code),
                ('state', 'not in', ('draft', 'cancelled')),
            ]
            if rec._origin.id:
                usage_domain.append(('id', '!=', rec._origin.id))
            previous_usage = self.env['gold.purchase'].search_count(usage_domain)
            if previous_usage >= 1:
                raise ValidationError(f"Usage Limit: Customer '{rec.customer_id.name}' has already successfully used coupon '{code}' once.")

            # 6. Check Order Price Range (Minimum/Maximum Order Value)
            subtotal = rec.subtotal
            if promo.min_cart_value > 0 and subtotal < promo.min_cart_value:
                raise ValidationError(f"Minimum Spend Required: Your order subtotal (₹{subtotal:,.2f}) is below the required ₹{promo.min_cart_value:,.2f} for this coupon.")
            
            if promo.max_cart_value > 0 and subtotal > promo.max_cart_value:
                raise ValidationError(f"Order Value High: This promotion is only valid for orders up to ₹{promo.max_cart_value:,.2f}. Your order is ₹{subtotal:,.2f}.")

            # 7. Check Channel (Online vs Store)
            if promo.applicable_channel == 'online' and rec.order_source not in ('online', 'app'):
                raise ValidationError(f"Channel Restriction: Promotion '{promo.name}' is only valid for Online/App orders.")
            elif promo.applicable_channel == 'offline' and rec.order_source != 'store':
                raise ValidationError(f"Channel Restriction: Coupon '{code}' can only be redeemed In-Store.")

            # 8. Calculate and Apply Discount
            discount = 0.0
            if promo.promotion_type == 'percentage':
                discount = subtotal * (promo.discount_pct / 100.0)
            elif promo.promotion_type == 'flat':
                discount = promo.discount_amount
            elif promo.promotion_type == 'making_waiver':
                discount = sum(rec.order_line_ids.mapped('making_charge'))
            elif promo.promotion_type == 'wastage_waiver':
                discount = sum(rec.order_line_ids.mapped('wastage_charge'))
            
            # Apply Cap
            if promo.max_discount_cap > 0:
                discount = min(discount, promo.max_discount_cap)
            
            # Final Safety: Discount can't exceed subtotal
            discount = min(discount, subtotal)

            rec.write({
                'promotion_id': promo.id,
                'discount_amount': discount,
            })
            # Recompute total
            rec._compute_totals()
            
            # Success confirmation (optional but helps avoid double-clicking)
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': f"Success! ₹{discount:,.2f} discount applied.",
                    'type': 'rainbow_man',
                }
            }

    def action_refresh_rates(self):
        """Update all order lines with the latest active gold rates for their Karat"""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("Rates can only be refreshed in Draft state.")
            for line in rec.order_line_ids:
                line._onchange_inventory_id() # Re-triggers the rate lookup
            rec._compute_totals()
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

    # Smart Button Counts
    payment_count = fields.Integer(compute='_compute_smart_counts')
    logistics_count = fields.Integer(compute='_compute_smart_counts')
    return_count = fields.Integer(compute='_compute_smart_counts')

    def _compute_smart_counts(self):
        for rec in self:
            rec.payment_count = self.env['gold.payment'].search_count([('order_id', '=', rec.id)])
            rec.logistics_count = self.env['gold.logistics'].search_count([('order_id', '=', rec.id)])
            rec.return_count = self.env['gold.returns'].search_count([('order_id', '=', rec.id)])

    def action_view_payments(self):
        return {
            'name': 'Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'gold.payment',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id, 'default_customer_id': self.customer_id.id},
        }

    def action_view_logistics(self):
        return {
            'name': 'Logistics',
            'type': 'ir.actions.act_window',
            'res_model': 'gold.logistics',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id, 'create': False},
        }

    def action_view_returns(self):
        return {
            'name': 'Returns',
            'type': 'ir.actions.act_window',
            'res_model': 'gold.returns',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id, 'default_customer_id': self.customer_id.id},
        }

    @api.constrains('total_value')
    def _check_total_value(self):
        for rec in self:
            if rec.total_value < 0:
                raise ValidationError("Total order value cannot be negative.")

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            if not rec.customer_id:
                raise ValidationError("Please select a customer before confirming the order.")
            
            if not rec.order_line_ids:
                raise ValidationError("The order must have at least one line item to be confirmed.")
            
            # Recompute totals just in case
            rec._compute_totals()
            if rec.total_value <= 0:
                raise ValidationError("The total value of the order must be greater than zero to confirm. Please ensure items have prices and weights.")

            rec.write({'state': 'confirmed', 'confirmation_date': fields.Datetime.now()})
            
            # ERP Interconnection: Reserve Inventory and Create Payment
            for line in rec.order_line_ids:
                if line.inventory_id:
                    line.inventory_id.action_reserve()
                    # Create Reservation record
                    self.env['gold.inventory.reservation'].create({
                        'name': f"Res for {rec.name}",
                        'inventory_id': line.inventory_id.id,
                        'quantity': line.quantity,
                        'reserved_for': 'order',
                        'order_reference': rec.name,
                    })
            
            # Create Automated Payment Record
            self.env['gold.payment'].create({
                'order_id': rec.id,
                'customer_id': rec.customer_id.id,
                'amount': rec.total_value,
                'payment_method': rec.payment_method,  # Pass the user's selection
                'state': 'initiated',
            })

            # ERP Interconnection: Promotions & Coupons Usage
            if rec.promotion_id:
                rec.promotion_id.write({
                    'times_used': rec.promotion_id.times_used + 1,
                    'total_orders': rec.promotion_id.total_orders + 1,
                    'total_discount_given': rec.promotion_id.total_discount_given + rec.discount_amount,
                })
            if rec.coupon_code:
                coupon = self.env['gold.coupon'].search([('name', '=', rec.coupon_code.strip())], limit=1)
                if coupon:
                    coupon.write({'times_used': coupon.times_used + 1})
                    # Recompute state if exhausted
                    coupon._compute_state()

    def action_quality_check(self):
        for rec in self:
            rec.write({'state': 'quality_check'})

    def action_packed(self):
        for rec in self:
            rec.write({'state': 'packed'})
            # ERP Interconnection: Auto-create Logistics Record
            self.env['gold.logistics'].create({
                'order_id': rec.id,
                'carrier': 'bluedart',  # Default carrier
                'status': 'label_created',
                'to_address': rec.shipping_address,
                'pincode': rec.pincode,
                'quality_check_done': True, # Mark QC as completed when packing
            })

    def action_dispatch(self):
        for rec in self:
            rec.write({'state': 'dispatched', 'dispatch_date': fields.Datetime.now()})

    def action_delivered(self):
        """Finalize order delivery with strict payment checks"""
        for rec in self:
            if rec.state not in ('dispatched', 'in_transit', 'out_for_delivery'):
                raise ValidationError(_("Order must be dispatched before it can be marked as delivered."))
            
            # STRICT VALIDATION: No payment = No delivery (unless COD)
            if rec.payment_method != 'cod' and rec.payment_status != 'paid':
                raise ValidationError(_("ERROR: This order is NOT Cash-on-Delivery. You cannot deliver an order that is not fully paid!"))

            rec.write({'state': 'delivered', 'delivery_date': fields.Datetime.now()})
            
            # ERP Interconnection: Mark Inventory as SOLD
            for line in rec.order_line_ids:
                if line.inventory_id:
                    line.inventory_id.action_sold(qty=line.quantity)

                    # Release reservation
                    res = self.env['gold.inventory.reservation'].search([
                        ('inventory_id', '=', line.inventory_id.id),
                        ('order_reference', '=', rec.name),
                        ('state', '=', 'active')
                    ], limit=1)
                    if res:
                        res.write({'state': 'released'})
            
            # ERP Interconnection: Loyalty & Analytics
            if rec.customer_id:
                rec.customer_id.action_earn_points(rec.total_value)
                rec.customer_id.action_update_metrics()

    def action_cancel(self):
        for rec in self:
            if rec.state in ('delivered', 'cancelled'):
                raise ValidationError("Cannot cancel an order that is already delivered or cancelled.")
            rec.write({'state': 'cancelled', 'cancellation_date': fields.Datetime.now()})
            
            # ERP Interconnection: Release Inventory
            for line in rec.order_line_ids:
                if line.inventory_id:
                    line.inventory_id.action_available()
                    # Expire reservation
                    res = self.env['gold.inventory.reservation'].search([
                        ('inventory_id', '=', line.inventory_id.id),
                        ('order_reference', '=', rec.name),
                        ('state', '=', 'active')
                    ], limit=1)
                    if res:
                        res.write({'state': 'expired'})
            
            # Mark payment as failed/cancelled
            payments = self.env['gold.payment'].search([('order_id', '=', rec.id)])
            payments.write({'state': 'failed'})

            # ERP Interconnection: Return redeemed points
            if rec.customer_id and rec.loyalty_points_used > 0:
                rec.customer_id.loyalty_points += rec.loyalty_points_used
                rec.loyalty_points_used = 0


    def action_set_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    # --- Strict CRUD Validations ---
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancelled') or rec.payment_status != 'unpaid':
                state_label = dict(self._fields['state'].selection).get(rec.state)
                payment_label = dict(self._fields['payment_status'].selection).get(rec.payment_status)
                raise UserError(_("Secure ERP Protection: You cannot delete Order '%s' because it is in the '%s' state or has payment status '%s'. "
                                 "To maintain data integrity, please cancel the order first.") % (rec.name, state_label, payment_label))
        return super(GoldPurchase, self).unlink()

    def write(self, vals):
        # Allow updates during module installation/upgrade (e.g., for demo data)
        if not self._context.get('install_mode'):
            for rec in self:
                # Disable ALL edits if Delivered AND Paid
                if rec.state == 'delivered' and rec.payment_status == 'paid':
                   raise ValidationError(_("Strict Security: This order is FULLY PAID and DELIVERED. No further modifications are allowed to maintain financial and audit integrity."))
                
                # Maintain existing partial restriction for delivered orders
                if rec.state == 'delivered' and any(k in vals for k in ('order_line_ids', 'customer_id', 'total_value')):
                    raise ValidationError(_("Strict Security: You cannot modify core details of a DELIVERED order!"))
        return super(GoldPurchase, self).write(vals)


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
    base_value = fields.Float(string='Base Value', compute='_compute_line_totals', store=True, readonly=True)
    making_charge = fields.Float(string='Making Charge')
    wastage_charge = fields.Float(string='Wastage Charge')
    stone_cost = fields.Float(string='Stone Cost')
    discount_amount = fields.Float(string='Discount')
    total_tax = fields.Float(string='Line Tax (3%)', compute='_compute_line_totals', store=True, readonly=True)
    tax_amount = fields.Float(string='Tax', compute='_compute_line_totals', store=True, readonly=True)
    line_total = fields.Float(string='Line Total', compute='_compute_line_totals', store=True, readonly=True)
    rate_id = fields.Many2one('gold.rate', string='Gold Rate at Order Time')
    customization = fields.Text(string='Customization Notes')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ], string='Line Status', default='pending')

    @api.depends('quantity', 'net_weight', 'making_charge', 'stone_cost', 'rate_id', 'discount_amount')
    def _compute_line_totals(self):
        for rec in self:
            # Base Value = Net Weight * Gold Rate
            rate_per_gram = rec.rate_id.price_per_gram if rec.rate_id else 0.0
            base = rec.net_weight * rate_per_gram * rec.quantity
            
            # Tax = 3% of (Base + Making + Stone) - Standard for Jewelry
            taxable_amount = (base + rec.making_charge + rec.stone_cost)
            tax = taxable_amount * 0.03
            
            rec.base_value = base
            rec.tax_amount = tax
            rec.line_total = taxable_amount + tax - rec.discount_amount

    @api.onchange('inventory_id')
    def _onchange_inventory_id(self):
        if self.inventory_id:
            inv = self.inventory_id
            self.sku = inv.sku
            self.name = inv.name
            self.karat = inv.karat
            self.gross_weight = inv.gross_weight
            self.net_weight = inv.net_weight
            self.making_charge = inv.making_charge
            self.stone_cost = inv.stone_cost
            self.rate_id = inv.rate_id
            
            warning_msg = ""
            if not inv.karat:
                warning_msg += "Karat is missing. "
            if inv.net_weight <= 0:
                warning_msg += "Net Weight is 0. "
                
            # If rate_id is not set on inventory, try to find the latest active rate for the karat
            if not self.rate_id and inv.karat:
                # Robust Karat Mapping (Inventory Label -> Pricing Code)
                karat_map = {
                    '24k': ['999', '24k', '24K'],
                    '22k': ['916', '22k', '22K'],
                    '18k': ['750', '18k', '18K'],
                    '14k': ['585', '14k', '14K'],
                }
                mapped_codes = karat_map.get(inv.karat.lower(), [inv.karat])
                
                latest_rate = self.env['gold.rate'].search([
                    ('karat', 'in', mapped_codes),
                    ('state', '=', 'active')
                ], order='effective_date desc', limit=1)
                
                if latest_rate:
                    self.rate_id = latest_rate

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")
