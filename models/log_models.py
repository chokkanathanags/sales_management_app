from odoo import models, fields, api


class GoldLogistics(models.Model):
    _name = 'gold.logistics'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Gold Logistics & Shipping'
    _rec_name = 'name'
    _order = 'dispatch_date desc'

    name = fields.Char(string='Tracking / AWB', required=True, default='New', copy=False, index=True, tracking=True)
    order_id = fields.Many2one('gold.purchase', string='Order', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('gold.logistics.seq') or 'New'
        return super(GoldLogistics, self).create(vals)

    # Carrier
    carrier = fields.Selection([
        ('bluedart', 'BlueDart'),
        ('delhivery', 'Delhivery'),
        ('fedex', 'FedEx'),
        ('india_post', 'India Post'),
        ('ecom_express', 'Ecom Express'),
        ('shiprocket', 'Shiprocket'),
        ('xpressbees', 'Xpressbees'),
        ('dtdc', 'DTDC'),
        ('own_fleet', 'Own Delivery Fleet'),
        ('other', 'Other'),
    ], string='Carrier', required=True)
    awb_number = fields.Char(string='AWB Number', copy=False, index=True)
    aggregator = fields.Char(string='Shipping Aggregator (Shiprocket, etc.)')

    # Shipment Type
    shipment_type = fields.Selection([
        ('forward', 'Forward (Outbound)'),
        ('reverse', 'Reverse (Return)'),
    ], string='Shipment Type', default='forward')
    delivery_type = fields.Selection([
        ('standard', 'Standard Delivery'),
        ('express', 'Express / Same Day'),
        ('scheduled', 'Scheduled Delivery'),
        ('weekend', 'Weekend Delivery'),
        ('store_pickup', 'Store Pickup'),
        ('click_collect', 'Click & Collect'),
    ], string='Delivery Type', default='standard')

    # Addresses
    from_address = fields.Text(string='From Address')
    to_address = fields.Text(string='To Address')
    pincode = fields.Char(string='Delivery Pincode')
    is_remote_area = fields.Boolean(string='Remote Area')
    remote_surcharge = fields.Float(string='Remote Area Surcharge')

    # Rates
    shipping_weight = fields.Float(string='Shipping Weight (kg)', digits=(10, 3))
    shipping_volume = fields.Float(string='Volume (cm³)')
    shipping_rate = fields.Float(string='Shipping Rate')
    shipping_zone = fields.Char(string='Zone')

    # Dates
    dispatch_date = fields.Datetime(string='Dispatch Date')
    estimated_delivery = fields.Date(string='Estimated Delivery Date')
    actual_delivery = fields.Datetime(string='Actual Delivery Date')
    scheduled_delivery_date = fields.Date(string='Scheduled Delivery Date')
    scheduled_delivery_slot = fields.Char(string='Scheduled Slot')
    pickup_date = fields.Date(string='Pickup Scheduled Date')

    # Status
    status = fields.Selection([
        ('label_created', 'Label Created'),
        ('pickup_scheduled', 'Pickup Scheduled'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('delivery_failed', 'Delivery Failed'),
        ('rto_initiated', 'RTO Initiated'),
        ('rto_in_transit', 'RTO In Transit'),
        ('rto_received', 'RTO Received'),
        ('return_pickup', 'Return Pickup Scheduled'),
        ('return_in_transit', 'Return In Transit'),
        ('return_delivered', 'Return Delivered'),
    ], string='Tracking Status', default='label_created', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('dispatched', 'Dispatched'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Shipment State', default='draft')

    # Delivery Details
    delivery_instructions = fields.Text(string='Delivery Instructions')
    signature_required = fields.Boolean(string='Signature Required')
    age_verification = fields.Boolean(string='Age Verification Required')
    contactless = fields.Boolean(string='Contactless Delivery')
    pod_image = fields.Binary(string='Proof of Delivery Image')

    # High Value
    is_high_value = fields.Boolean(string='High Value Shipment (>50,000)')
    insurance_required = fields.Boolean(string='Insurance Required')
    insurance_amount = fields.Float(string='Insurance Amount')
    gps_tracking = fields.Boolean(string='GPS Tracking Enabled')
    tamper_proof = fields.Boolean(string='Tamper-Proof Packaging')

    # Documentation
    has_jewelry_cert = fields.Boolean(string='Jewelry Certificate Included')
    has_warranty_card = fields.Boolean(string='Warranty Card Included')
    has_care_instructions = fields.Boolean(string='Care Instructions Included')
    has_gift_card = fields.Boolean(string='Gift Card Included')

    # Warehouse
    is_gift_wrapped = fields.Boolean(string='Gift Wrapped')
    quality_check_done = fields.Boolean(string='Quality Check Completed')
    batch_code = fields.Char(string='Pick/Wave Batch Code')
    packed_by = fields.Char(string='Packed By')

    # Return logistics
    return_awb = fields.Char(string='Return AWB Number')
    return_shipment_id = fields.Many2one('gold.logistics', string='Return Shipment')

    # Old fields for compatibility
    code = fields.Char(string='Code')
    image = fields.Binary(string='Image')
    description = fields.Text(string='Description')
    category = fields.Char(string='Category')
    type = fields.Char(string='Type')
    karat = fields.Char(string='Karat Ref')
    currency_name = fields.Char(string='Currency', default='INR')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')
