from odoo import models, fields, api
from odoo.exceptions import ValidationError


class GoldReturns(models.Model):
    _name = 'gold.returns'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Gold Returns & Exchanges'
    _rec_name = 'name'
    _order = 'initiation_date desc'

    name = fields.Char(string='RMA Number', copy=False, index=True, tracking=True, readonly=True)
    order_id = fields.Many2one('gold.purchase', string='Original Order', required=True, tracking=True)
    customer_id = fields.Many2one('gold.customer', string='Customer', related='order_id.customer_id', store=True, readonly=True, tracking=True)
    order_line_ids_ref = fields.One2many('gold.purchase.line', related='order_id.order_line_ids', string='Original Order Lines', readonly=True)
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('gold.returns.seq') or 'New'
        return super(GoldReturns, self).create(vals_list)

    # Return Type
    return_type = fields.Selection([
        ('full', 'Full Order Return'),
        ('partial', 'Partial Return (Line Item)'),
        ('quantity_partial', 'Quantity-Based Partial Return'),
        ('exchange_same', 'Exchange - Same Product (Size/Variant)'),
        ('exchange_different', 'Exchange - Different Product'),
        ('old_gold', 'Old Gold Exchange'),
    ], string='Return Type', required=True, default='full', tracking=True)

    # Reason
    reason = fields.Selection([
        ('size_issue', 'Size Issue'),
        ('quality_issue', 'Quality Issue'),
        ('wrong_item', 'Wrong Item Delivered'),
        ('damaged', 'Damaged in Transit'),
        ('changed_mind', 'Changed Mind'),
        ('not_as_described', 'Not as Described'),
        ('defective', 'Defective Item'),
        ('other', 'Other'),
    ], string='Return Reason', required=True)
    reason_notes = fields.Text(string='Detailed Reason')
    customer_images = fields.Binary(string='Customer Uploaded Image')

    # Return Policy
    return_window = fields.Integer(string='Return Window (days)', default=15)
    restocking_fee = fields.Float(string='Restocking Fee (%)')
    is_non_returnable = fields.Boolean(string='Non-Returnable Item', default=False)

    # Items
    order_line_id = fields.Many2one('gold.purchase.line', string='Select Purchased Item', domain="[('order_id', '=', order_id)]", tracking=True)
    returned_item_sku = fields.Char(string='Returned Item SKU')
    returned_item_name = fields.Char(string='Returned Item Name')
    original_qty = fields.Float(string='Original Quantity', readonly=True)
    returned_quantity = fields.Float(string='Returned Quantity', default=1.0)

    @api.onchange('order_line_id', 'return_type', 'returned_quantity')
    def _onchange_return_items(self):
        if self.order_line_id:
            self.returned_item_sku = self.order_line_id.sku
            self.returned_item_name = self.order_line_id.name
            self.original_qty = self.order_line_id.quantity
            
            # If full return is selected, force the quantity to match original
            if self.return_type == 'full':
                self.returned_quantity = self.order_line_id.quantity
            
            # Cap the quantity and show a warning if the user tries to enter more than purchased
            if self.returned_quantity > self.original_qty:
                qty_before = self.returned_quantity
                self.returned_quantity = self.original_qty
                return {
                    'warning': {
                        'title': "Invalid Return Quantity",
                        'message': f"You cannot return {qty_before} units because only {self.original_qty} units were originally purchased. The quantity has been reset to the maximum allowed.",
                        'type': 'notification',
                    }
                }
        else:
            self.returned_item_sku = False
            self.returned_item_name = False
            self.original_qty = 0.0
            self.returned_quantity = 0.0

    @api.constrains('returned_quantity', 'original_qty', 'order_line_id')
    def _check_return_quantity(self):
        for rec in self:
            if rec.order_line_id:
                if rec.returned_quantity <= 0:
                    raise ValidationError("Returned quantity must be greater than zero.")
                if rec.returned_quantity > rec.original_qty:
                    raise ValidationError(f"Invalid Quantity: You cannot return more than the original purchased quantity ({rec.original_qty}).")

    # Exchange
    exchange_item_sku = fields.Char(string='Exchange Item SKU')
    exchange_item_name = fields.Char(string='Exchange Item Name')
    exchange_price_diff = fields.Float(string='Price Difference for Exchange')
    old_gold_weight = fields.Float(string='Old Gold Weight (g)', digits=(10, 3))
    old_gold_rate = fields.Float(string='Old Gold Rate per gram')
    old_gold_value = fields.Float(string='Old Gold Exchange Value', compute='_compute_old_gold_value', store=True, readonly=True)

    # Logistics
    logistics_id = fields.Many2one('gold.logistics', string='Return Shipment')
    return_awb = fields.Char(string='Return AWB')
    return_pickup_date = fields.Date(string='Return Pickup Scheduled')
    return_received_date = fields.Datetime(string='Return Received On')
    shipping_cost_by = fields.Selection([
        ('customer', 'Customer Pays'),
        ('company', 'Free Return (Company Pays)'),
    ], string='Return Shipping Cost', default='company')

    # QC
    qc_status = fields.Selection([
        ('pending', 'QC Pending'),
        ('passed', 'QC Passed'),
        ('failed_damaged', 'Failed - Damaged'),
        ('failed_tampered', 'Failed - Tampered'),
    ], string='QC Status', default='pending', tracking=True)
    qc_notes = fields.Text(string='QC Notes')
    qc_done_by = fields.Char(string='QC Done By')

    # Restocking
    inventory_restocked = fields.Boolean(string='Inventory Restocked', default=False)
    restock_location = fields.Char(string='Restock to Location')
    restock_date = fields.Datetime(string='Restocked On')
    return_to_different_location = fields.Boolean(string='Return to Different Location')

    # Refund
    refund_type = fields.Selection([
        ('original_method', 'Original Payment Method'),
        ('bank_transfer', 'Bank Transfer'),
        ('store_credit', 'Store Credit'),
        ('no_refund', 'No Refund (Exchange)'),
    ], string='Refund Type', default='original_method')
    refund_amount = fields.Float(string='Refund Amount')
    shipping_deduction = fields.Float(string='Shipping Deduction')
    restocking_deduction = fields.Float(string='Restocking Fee Deduction')
    final_refund_amount = fields.Float(string='Final Refund Amount', compute='_compute_final_refund', store=True, readonly=True)
    refund_state = fields.Selection([
        ('pending', 'Refund Pending'),
        ('approved', 'Refund Approved'),
        ('processed', 'Refund Processed'),
        ('rejected', 'Refund Rejected'),
    ], string='Refund Status', default='pending', tracking=True)
    refund_transaction_id = fields.Char(string='Refund Transaction ID')
    refund_date = fields.Datetime(string='Refund Processed On')

    # Cross-channel
    return_channel = fields.Selection([
        ('courier', 'Return by Courier'),
        ('in_store', 'Return to Store'),
        ('store_b', 'Return to Different Store'),
    ], string='Return Channel', default='courier')
    return_store = fields.Char(string='Return Store Name')
    processed_by_store = fields.Boolean(string='Processed by Store POS')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Return Requested'),
        ('approved', 'Approved'),
        ('pickup_scheduled', 'Pickup Scheduled'),
        ('in_transit', 'In Transit'),
        ('received', 'Received at Warehouse'),
        ('qc_in_progress', 'QC In Progress'),
        ('qc_passed', 'QC Passed'),
        ('qc_failed', 'QC Failed'),
        ('refund_initiated', 'Refund Initiated'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ], string='Return Status', default='draft', index=True)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            rec.write({'state': 'approved', 'approval_date': fields.Datetime.now()})

    def action_receive(self):
        for rec in self:
            rec.write({'state': 'received', 'return_received_date': fields.Datetime.now()})

    def action_qc_pass(self):
        for rec in self:
            rec.write({'state': 'qc_passed', 'qc_status': 'passed'})

    def action_qc_fail(self):
        for rec in self:
            rec.write({'state': 'qc_failed', 'qc_status': 'failed_damaged'})

    def action_initiate_refund(self):
        for rec in self:
            rec.write({'state': 'refund_initiated', 'refund_state': 'approved'})

    def action_complete(self):
        for rec in self:
            rec.write({
                'state': 'completed', 
                'completion_date': fields.Datetime.now(),
                'refund_state': 'processed',
                'refund_date': fields.Datetime.now()
            })
            # ERP Interconnection: Restock Inventory
            if rec.order_line_id and rec.order_line_id.inventory_id:
                rec.order_line_id.inventory_id.action_return(qty=rec.returned_quantity)
                rec.write({'inventory_restocked': True, 'restock_date': fields.Datetime.now()})

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    # Dates
    initiation_date = fields.Datetime(string='Return Initiated On', default=fields.Datetime.now)
    approval_date = fields.Datetime(string='Approved On')
    completion_date = fields.Datetime(string='Completed On')
    sla_deadline = fields.Date(string='SLA Deadline (7-10 days)')

    @api.constrains('sla_deadline')
    def _check_sla_deadline(self):
        for rec in self:
            if rec.sla_deadline and rec.sla_deadline < fields.Date.today():
                raise ValidationError("The SLA Deadline cannot be in the past. It must be today or a future date.")

    # Old fields for compatibility
    code = fields.Char(string='Code')
    image = fields.Binary(string='Image')
    description = fields.Text(string='Description')
    category = fields.Char(string='Category')
    type = fields.Char(string='Type')
    karat = fields.Char(string='Karat Reference')
    currency_name = fields.Char(string='Currency', default='INR')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')

    @api.depends('old_gold_weight', 'old_gold_rate')
    def _compute_old_gold_value(self):
        for rec in self:
            rec.old_gold_value = rec.old_gold_weight * rec.old_gold_rate

    @api.depends('refund_amount', 'shipping_deduction', 'restocking_deduction')
    def _compute_final_refund(self):
        for rec in self:
            rec.final_refund_amount = rec.refund_amount - rec.shipping_deduction - rec.restocking_deduction
