from odoo import models, fields, api


class GoldPayment(models.Model):
    _name = 'gold.payment'
    _description = 'Gold Payment'
    _rec_name = 'name'
    _order = 'payment_date desc'

    name = fields.Char(string='Payment Reference', required=True, default='New', copy=False)
    order_id = fields.Many2one('gold.purchase', string='Order')
    customer_id = fields.Many2one('gold.customer', string='Customer')
    active = fields.Boolean(string='Active', default=True)

    # Payment Method
    payment_method = fields.Selection([
        ('cod', 'Cash on Delivery (COD)'),
        ('card_debit', 'Debit Card'),
        ('card_credit', 'Credit Card'),
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
    ], string='Payment Method', required=True)

    # Gateway
    payment_gateway = fields.Selection([
        ('razorpay', 'Razorpay'),
        ('payu', 'PayU'),
        ('ccavenue', 'CCAvenue'),
        ('paytm', 'Paytm'),
        ('stripe', 'Stripe'),
        ('manual', 'Manual / Offline'),
    ], string='Payment Gateway')
    transaction_id = fields.Char(string='Transaction ID', copy=False, index=True)
    gateway_order_id = fields.Char(string='Gateway Order ID')
    gateway_response = fields.Text(string='Gateway Response (JSON)')

    # Amounts
    amount = fields.Float(string='Payment Amount', required=True)
    currency_name = fields.Char(string='Currency', default='INR')
    gateway_charges = fields.Float(string='Gateway Charges')
    refund_amount = fields.Float(string='Refunded Amount')

    # EMI Details
    emi_months = fields.Integer(string='EMI Tenure (months)')
    emi_provider = fields.Char(string='EMI Provider (Bajaj, ZestMoney, etc.)')
    emi_monthly_amount = fields.Float(string='Monthly EMI Amount')

    # Dates
    payment_date = fields.Datetime(string='Payment Date', default=fields.Datetime.now)
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
    ], string='Payment Status', default='initiated', index=True)

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

    # Old fields kept for compatibility
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    category = fields.Char(string='Category')
    type = fields.Char(string='Type')
    karat = fields.Char(string='Karat Reference')
    base_value = fields.Float(string='Base Value')
    total_value = fields.Float(string='Total Value')
    tax_amount = fields.Float(string='Tax Amount')
