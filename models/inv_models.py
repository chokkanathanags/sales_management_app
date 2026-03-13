from odoo import models, fields, api
from odoo.exceptions import ValidationError


class GoldInventory(models.Model):
    _name = 'gold.inventory'
    _description = 'Gold Inventory'
    _rec_name = 'name'
    _order = 'name'

    # Basic Info
    name = fields.Char(string='Reference', required=True, default='New', copy=False)
    sku = fields.Char(string='SKU', required=True, copy=False, index=True)
    serial_number = fields.Char(string='Serial Number (Unique)', copy=False, index=True)
    barcode = fields.Char(string='Barcode (EAN-13/Code128/QR)', copy=False, index=True)
    rfid_tag = fields.Char(string='RFID Tag', copy=False)
    image = fields.Binary(string='Image')
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    notes = fields.Text(string='Internal Notes')

    # Classification
    category = fields.Char(string='Category', required=True)
    type = fields.Selection([
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond Jewelry'),
        ('other', 'Other'),
    ], string='Type', default='gold')
    karat = fields.Selection([
        ('24k', '24K (999)'),
        ('22k', '22K (916)'),
        ('18k', '18K'),
        ('14k', '14K'),
        ('other', 'Other'),
    ], string='Karat/Purity')
    purity = fields.Float(string='Purity (%)')
    collection = fields.Char(string='Collection/Brand')

    # Weight & Physical
    gross_weight = fields.Float(string='Gross Weight (g)', digits=(10, 3))
    net_weight = fields.Float(string='Net Weight (g)', digits=(10, 3))
    stone_weight = fields.Float(string='Stone Weight (g)', digits=(10, 3))

    # Batch/Lot
    lot_number = fields.Char(string='Lot/Batch Number')
    manufacture_date = fields.Date(string='Manufacture Date')
    expiry_date = fields.Date(string='Expiry Date')

    # Location
    warehouse = fields.Char(string='Warehouse')
    store_location = fields.Char(string='Store/Location')
    bin_location = fields.Char(string='Bin/Shelf')

    # Quantities
    quantity = fields.Float(string='On Hand Qty', digits=(10, 3), default=1.0)
    qty_available = fields.Float(string='Available to Sell', compute='_compute_qty_available', store=True)
    qty_reserved = fields.Float(string='Reserved Qty', default=0.0)
    qty_in_transit = fields.Float(string='In-Transit Qty', default=0.0)
    qty_on_order = fields.Float(string='On Order (Supplier)', default=0.0)
    qty_in_production = fields.Float(string='In Production', default=0.0)
    qty_damaged = fields.Float(string='Damaged/Defective', default=0.0)
    qty_return_pool = fields.Float(string='Return Pool', default=0.0)
    safety_stock = fields.Float(string='Safety Stock / Buffer', default=0.0)
    low_stock_threshold = fields.Float(string='Low Stock Alert Threshold', default=1.0)

    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('in_transit', 'In Transit'),
        ('in_production', 'In Production'),
        ('on_order', 'On Order'),
        ('quality_check', 'Quality Check Pending'),
        ('damaged', 'Damaged/Defective'),
        ('return_pool', 'Return/Exchange Pool'),
        ('consignment', 'Consignment'),
        ('inactive', 'Inactive'),
    ], string='Status', default='available', index=True)
    is_consignment = fields.Boolean(string='Consignment Item')
    consignment_partner = fields.Char(string='Consignment Partner')

    # Financials
    making_charge = fields.Float(string='Making Charge')
    wastage = fields.Float(string='Wastage (%)')
    stone_cost = fields.Float(string='Stone Cost')
    base_value = fields.Float(string='Base Value', compute='_compute_base_value', store=True)
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')
    currency_name = fields.Char(string='Currency', default='INR')

    # Linked Rate
    rate_id = fields.Many2one('gold.rate', string='Gold Rate Used')

    @api.depends('quantity', 'qty_reserved')
    def _compute_qty_available(self):
        for rec in self:
            rec.qty_available = max(0, rec.quantity - rec.qty_reserved)

    @api.depends('net_weight', 'rate_id', 'purity')
    def _compute_base_value(self):
        for rec in self:
            if rec.rate_id and rec.net_weight:
                rec.base_value = rec.net_weight * rec.rate_id.price_per_gram
            else:
                rec.base_value = 0.0

    @api.constrains('serial_number')
    def _check_unique_serial(self):
        for rec in self:
            if rec.serial_number:
                domain = [('serial_number', '=', rec.serial_number), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError(f"Serial number '{rec.serial_number}' already exists!")

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError("Inventory quantity cannot be negative.")

    @api.constrains('base_value', 'total_value')
    def _check_values(self):
        for rec in self:
            if rec.base_value < 0 or rec.total_value < 0:
                raise ValidationError("Value fields (Base/Total) cannot be negative.")


class GoldInventoryTransfer(models.Model):
    _name = 'gold.inventory.transfer'
    _description = 'Inventory Transfer'
    _rec_name = 'name'

    name = fields.Char(string='Transfer Reference', required=True, default='New', copy=False)
    inventory_id = fields.Many2one('gold.inventory', string='Item', required=True)
    from_location = fields.Char(string='From Location', required=True)
    to_location = fields.Char(string='To Location', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    transfer_date = fields.Datetime(string='Transfer Date')
    estimated_arrival = fields.Datetime(string='Estimated Arrival')
    cost = fields.Float(string='Transfer Cost')
    notes = fields.Text(string='Notes')
    approved_by = fields.Char(string='Approved By')


class GoldInventoryReservation(models.Model):
    _name = 'gold.inventory.reservation'
    _description = 'Inventory Reservation'
    _rec_name = 'name'

    name = fields.Char(string='Reservation Reference', required=True, default='New', copy=False)
    inventory_id = fields.Many2one('gold.inventory', string='Item', required=True)
    quantity = fields.Float(string='Reserved Qty', required=True, default=1.0)
    reserved_for = fields.Selection([
        ('cart', 'Cart'),
        ('order', 'Order Confirmed'),
        ('manual', 'Manual'),
    ], string='Reserved For', default='cart')
    expiry_time = fields.Datetime(string='Reservation Expiry')
    order_reference = fields.Char(string='Order Reference')
    state = fields.Selection([
        ('active', 'Active'),
        ('released', 'Released'),
        ('expired', 'Expired'),
    ], string='State', default='active')
    source_system = fields.Char(string='Source System')
