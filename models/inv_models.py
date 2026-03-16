from odoo import models, fields, api
from odoo.exceptions import ValidationError


class GoldCategory(models.Model):
    _name = 'gold.category'
    _description = 'Jewelry Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')


class GoldInventory(models.Model):
    _name = 'gold.inventory'
    _description = 'Gold Inventory'
    _rec_name = 'name'
    _order = 'name'

    # Basic Info
    name = fields.Char(string='Reference', required=True, copy=False)
    sku = fields.Char(string='SKU', required=True, copy=False, index=True)
    serial_number = fields.Char(string='Serial Number (Unique)', required=True, copy=False, index=True)
    barcode = fields.Char(string='Barcode (EAN-13/Code128/QR)', copy=False, index=True)
    rfid_tag = fields.Char(string='RFID Tag', copy=False)
    image = fields.Binary(string='Image')
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    notes = fields.Text(string='Internal Notes')

    # Classification
    # Classification
    category_id = fields.Many2one('gold.category', string='Category', required=True)
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
    gross_weight = fields.Float(string='Gross Weight (g)', digits=(10, 3), required=True)
    net_weight = fields.Float(string='Net Weight (g)', digits=(10, 3), required=True)
    stone_weight = fields.Float(string='Stone Weight (g)', digits=(10, 3), default=0.0)

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
    qty_available = fields.Float(string='Available to Sell', compute='_compute_qty_available', store=True, readonly=True)
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
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('in_transit', 'In Transit'),
        ('in_production', 'In Production'),
        ('on_order', 'On Order'),
        ('quality_check', 'Quality Check Pending'),
        ('damaged', 'Damaged/Defective'),
        ('return_pool', 'Return/Exchange Pool'),
        ('consignment', 'Consignment'),
        ('inactive', 'Inactive'),
    ], string='Status', default='draft', index=True)
    is_consignment = fields.Boolean(string='Consignment Item')
    consignment_partner = fields.Char(string='Consignment Partner')

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_available(self):
        for rec in self:
            rec.state = 'available'

    def action_reserve(self):
        for rec in self:
            rec.state = 'reserved'

    def action_sell(self):
        for rec in self:
            rec.state = 'sold'

    def action_mark_damaged(self):
        for rec in self:
            rec.state = 'damaged'

    def action_quality_check(self):
        for rec in self:
            rec.state = 'quality_check'

    def action_approve_qc(self):
        """Pass QC and make item available for sale"""
        for rec in self:
            rec.state = 'available'

    def action_reject_qc(self):
        """Fail QC and move item to damaged state"""
        for rec in self:
            rec.state = 'damaged'

    def action_deactivate(self):
        for rec in self:
            rec.state = 'inactive'

    def action_sold(self, qty=1.0):
        for rec in self:
            rec.state = 'sold' if rec.quantity - qty <= 0 else 'available'
            if rec.quantity >= qty:
                rec.quantity -= qty

    def action_return(self, qty=1.0):
        for rec in self:
            rec.state = 'available'
            rec.quantity += qty


    # Financials
    making_charge = fields.Float(string='Making Charge', default=0.0)
    wastage = fields.Float(string='Wastage (%)', default=0.0)
    stone_cost = fields.Float(string='Stone Cost', default=0.0)
    base_value = fields.Float(string='Base Value', compute='_compute_pricing', store=True, readonly=True)
    total_value = fields.Float(string='Total Value', compute='_compute_pricing', store=True, readonly=True)
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_pricing', store=True, readonly=True)
    currency_name = fields.Char(string='Currency', default='INR')

    # Linked Rate
    rate_id = fields.Many2one('gold.rate', string='Gold Rate Used')

    # Smart Button Counts
    order_count = fields.Integer(compute='_compute_order_count')

    def _compute_order_count(self):
        for rec in self:
            rec.order_count = self.env['gold.purchase.line'].search_count([('inventory_id', '=', rec.id)])

    def action_view_orders(self):
        order_line_ids = self.env['gold.purchase.line'].search([('inventory_id', '=', self.id)]).mapped('order_id').ids
        return {
            'name': 'Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'gold.purchase',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', order_line_ids)],
        }

    @api.depends('quantity', 'qty_reserved')
    def _compute_qty_available(self):
        for rec in self:
            rec.qty_available = max(0, rec.quantity - rec.qty_reserved)

    @api.depends('net_weight', 'rate_id', 'making_charge', 'wastage', 'stone_cost')
    def _compute_pricing(self):
        for rec in self:
            # 1. Base Gold Value
            gold_rate = rec.rate_id.price_per_gram if rec.rate_id else 0.0
            rec.base_value = rec.net_weight * gold_rate
            
            # 2. Taxation (Assume 3% GST on Gold)
            rec.tax_amount = (rec.base_value + rec.making_charge + rec.stone_cost) * 0.03
            
            # 3. Total Final Price
            rec.total_value = rec.base_value + rec.making_charge + rec.stone_cost + rec.tax_amount

    @api.constrains('serial_number')
    def _check_unique_serial(self):
        for rec in self:
            if rec.serial_number:
                domain = [('serial_number', '=', rec.serial_number), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError(f"Serial number '{rec.serial_number}' already exists!")

    @api.constrains('type', 'karat', 'gross_weight', 'net_weight', 'quantity', 'stone_weight')
    def _check_inventory_validity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError("Inventory quantity cannot be negative.")
                
            if rec.type in ('gold', 'silver', 'platinum') and rec.net_weight <= 0:
                raise ValidationError(f"ERROR: Net weight must be strictly greater than 0 for {rec.type} items. You cannot save an item without a weight.")
                
            if rec.stone_weight < 0:
                raise ValidationError("Stone weight cannot be negative.")
                
            if rec.net_weight > rec.gross_weight:
                raise ValidationError("Net weight cannot be greater than gross weight.")
                
            if rec.type == 'gold' and not rec.karat:
                raise ValidationError("ERROR: Karat purity must be specified for all gold items. You cannot save this item without a Karat value.")


class GoldInventoryTransfer(models.Model):
    _name = 'gold.inventory.transfer'
    _description = 'Inventory Transfer'
    _rec_name = 'name'

    name = fields.Char(string='Transfer Reference', copy=False, readonly=True)
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
    actual_arrival = fields.Datetime(string='Actual Arrival')
    cost = fields.Float(string='Transfer Cost')
    notes = fields.Text(string='Notes')
    approved_by = fields.Char(string='Approved By')

    @api.onchange('inventory_id')
    def _onchange_inventory_id(self):
        if self.inventory_id:
            self.from_location = self.inventory_id.store_location

    def action_approve(self):
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.name
            })

    def action_transit(self):
        for rec in self:
            rec.write({
                'state': 'in_transit',
                'transfer_date': fields.Datetime.now()
            })

    def action_done(self):
        for rec in self:
            if rec.state == 'done':
                continue
            
            if not rec.inventory_id:
                raise ValidationError("No inventory item selected for transfer.")
            
            if rec.quantity > rec.inventory_id.quantity:
                raise ValidationError(f"Insufficient quantity in stock. Available: {rec.inventory_id.quantity}")

            # If partial transfer, split the record
            if rec.quantity < rec.inventory_id.quantity:
                # Create a new record for the destination
                new_inv = rec.inventory_id.copy({
                    'quantity': rec.quantity,
                    'store_location': rec.to_location,
                    'state': 'available',
                    'name': f"{rec.inventory_id.name} (Moved)",
                    'sku': f"{rec.inventory_id.sku}-T{fields.Datetime.now().strftime('%M%S')}",
                    'serial_number': f"{rec.inventory_id.serial_number}-T{fields.Datetime.now().strftime('%M%S')}",
                })
                # Subtract from original
                rec.inventory_id.write({'quantity': rec.inventory_id.quantity - rec.quantity})
            else:
                # Full transfer: Just update the location
                rec.inventory_id.write({'store_location': rec.to_location})

            rec.write({
                'state': 'done',
                'actual_arrival': fields.Datetime.now()
            })

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('gold.inventory.transfer.seq') or 'New'
        return super(GoldInventoryTransfer, self).create(vals_list)


class GoldInventoryReservation(models.Model):
    _name = 'gold.inventory.reservation'
    _description = 'Inventory Reservation'
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Reservation Reference', copy=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gold.inventory.reservation.seq') or 'New'
        return super(GoldInventoryReservation, self).create(vals_list)

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
