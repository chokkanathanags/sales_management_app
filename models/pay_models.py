from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GoldPayment(models.Model):
    _name = 'gold.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Gold Payment'
    _rec_name = 'name'
    _order = 'payment_date desc'

    name = fields.Char(string='Payment Reference', copy=False, readonly=True)
    order_id = fields.Many2one('gold.purchase', string='Order', tracking=True)
    customer_id = fields.Many2one('gold.customer', string='Customer', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True)

    # Payment Method
    payment_method = fields.Selection([
        ('cod', 'Cash on Delivery (COD)'),
        ('card_debit', 'Debit Card'),
        ('card_credit', 'Credit Card'),
        ('card', 'Generic Card Payment'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('wallet_paytm', 'Paytm Wallet'),
        ('wallet_phonepe', 'PhonePe Wallet'),
        ('wallet_amazon', 'Amazon Pay Wallet'),
        ('bnpl', 'Buy Now Pay Later / Cardless EMI'),
        ('emi_bank', 'Bank EMI'),
        ('loyalty_points', 'Loyalty Points Redemption'),
        ('store_credit', 'Store Credit / Wallet'),
        ('gold_exchange', 'Old Gold Exchange'),
        ('split', 'Split Payment'),
        ('advance', 'Advance Payment'),
    ], string='Payment Method', required=True, tracking=True)

    # Gateway
    payment_gateway = fields.Selection([
        ('razorpay', 'Razorpay'),
        ('payu', 'PayU'),
        ('ccavenue', 'CCAvenue'),
        ('paytm', 'Paytm'),
        ('stripe', 'Stripe'),
        ('manual', 'Manual / Offline'),
    ], string='Payment Gateway', tracking=True)
    transaction_id = fields.Char(string='Transaction ID', copy=False, index=True, tracking=True)
    gateway_order_id = fields.Char(string='Gateway Order ID')
    gateway_response = fields.Text(string='Gateway Response (JSON)')

    # Amounts
    amount = fields.Float(string='Payment Amount', required=True, tracking=True)
    currency_name = fields.Char(string='Currency', default='INR')
    gateway_charges = fields.Float(string='Gateway Charges')
    refund_amount = fields.Float(string='Refunded Amount')

    # EMI Details
    emi_months = fields.Integer(string='EMI Tenure (months)')
    emi_provider = fields.Char(string='EMI Provider (Bajaj, ZestMoney, etc.)')
    emi_monthly_amount = fields.Float(string='Monthly EMI Amount')

    # Dates
    payment_date = fields.Datetime(string='Payment Date', default=fields.Datetime.now, tracking=True)
    settlement_date = fields.Date(string='Settlement Date')
    refund_date = fields.Datetime(string='Refund Date')

    # Status
    state = fields.Selection([
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timed Out'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
        ('chargeback', 'Chargeback'),
        ('reconciled', 'Reconciled'),
    ], string='Payment Status', default='initiated', index=True, tracking=True)

    def action_confirm_success(self):
        for rec in self:
            rec.write({'state': 'success', 'payment_date': fields.Datetime.now()})
            # Bidirectional Sync: Update Order payment status
            if rec.order_id:
                rec.order_id.write({'payment_status': 'paid'})

    def action_set_pending(self):
        for rec in self:
            rec.state = 'pending'

    def action_set_failed(self):
        for rec in self:
            rec.state = 'failed'

    def action_reconcile(self):
        for rec in self:
            rec.write({'state': 'reconciled', 'is_reconciled': True, 'reconciliation_date': fields.Date.today()})

    # --- Strict CRUD Validations ---
    def unlink(self):
        for rec in self:
            if rec.state == 'success':
                raise ValidationError(_("Strict Security: You cannot delete a successful payment record!"))
        return super(GoldPayment, self).unlink()

    def write(self, vals):
        for rec in self:
            if rec.state == 'success' and any(k in vals for k in ('amount', 'order_id', 'customer_id')):
                raise ValidationError(_("Strict Security: You cannot modify core details of a SUCCESSFUL payment!"))
        return super(GoldPayment, self).write(vals)

    # Reconciliation
    is_reconciled = fields.Boolean(string='Reconciled', default=False)
    reconciliation_date = fields.Date(string='Reconciliation Date')
    settlement_file_ref = fields.Char(string='Settlement File Reference')
    discrepancy_amount = fields.Float(string='Discrepancy Amount')
    discrepancy_notes = fields.Text(string='Discrepancy Notes')

    # Security
    is_3ds_verified = fields.Boolean(string='3D Secure / OTP Verified')
    attempt_count = fields.Integer(string='Payment Attempt Count', default=1)

    # Refund
    refund_method = fields.Char(string='Refund Method')
    refund_transaction_id = fields.Char(string='Refund Transaction ID')
    refund_reason = fields.Text(string='Refund Reason')

    # Compatibility/Technical fields
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    category = fields.Char(string='Category')
    type = fields.Char(string='Type')
    karat = fields.Char(string='Karat Reference')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')

    # Validations
    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Payment amount must be greater than zero."))

    @api.constrains('payment_date')
    def _check_payment_date(self):
        for rec in self:
            if rec.payment_date and rec.payment_date > fields.Datetime.now():
                raise ValidationError(_("Payment date cannot be in the future."))

    @api.constrains('customer_id')
    def _check_customer_id(self):
        for rec in self:
            if not rec.customer_id:
                raise ValidationError(_("A customer must be selected for the payment."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('gold.payment.seq') or 'New'
        return super(GoldPayment, self).create(vals_list)
