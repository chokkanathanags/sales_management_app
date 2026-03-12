from odoo import models, fields, api


class GoldReturns(models.Model):
    _name = 'gold.returns'
    _description = 'Gold Returns & Exchanges'
    _rec_name = 'name'
    _order = 'initiation_date desc'

    name = fields.Char(string='RMA Number', required=True, default='New', copy=False, index=True)
    order_id = fields.Many2one('gold.purchase', string='Original Order')
    customer_id = fields.Many2one('gold.customer', string='Customer')
    active = fields.Boolean(string='Active', default=True)

    # Return Type
    return_type = fields.Selection([
        ('full', 'Full Order Return'),
        ('partial', 'Partial Return (Line Item)'),
        ('quantity_partial', 'Quantity-Based Partial Return'),
        ('exchange_same', 'Exchange - Same Product (Size/Variant)'),
        ('exchange_different', 'Exchange - Different Product'),
        ('old_gold', 'Old Gold Exchange'),
    ], string='Return Type', required=True, default='full')

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
    returned_item_sku = fields.Char(string='Returned Item SKU')
    returned_item_name = fields.Char(string='Returned Item Name')
    returned_quantity = fields.Float(string='Returned Quantity', default=1.0)

    # Exchange
    exchange_item_sku = fields.Char(string='Exchange Item SKU')
    exchange_item_name = fields.Char(string='Exchange Item Name')
    exchange_price_diff = fields.Float(string='Price Difference for Exchange')
    old_gold_weight = fields.Float(string='Old Gold Weight (g)', digits=(10, 3))
    old_gold_rate = fields.Float(string='Old Gold Rate per gram')
    old_gold_value = fields.Float(string='Old Gold Exchange Value', compute='_compute_old_gold_value', store=True)

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
    ], string='QC Status', default='pending')
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
    final_refund_amount = fields.Float(string='Final Refund Amount', compute='_compute_final_refund', store=True)
    refund_state = fields.Selection([
        ('pending', 'Refund Pending'),
        ('approved', 'Refund Approved'),
        ('processed', 'Refund Processed'),
        ('rejected', 'Refund Rejected'),
    ], string='Refund Status', default='pending')
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

    # Dates
    initiation_date = fields.Datetime(string='Return Initiated On', default=fields.Datetime.now)
    approval_date = fields.Datetime(string='Approved On')
    completion_date = fields.Datetime(string='Completed On')
    sla_deadline = fields.Date(string='SLA Deadline (7-10 days)')

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
