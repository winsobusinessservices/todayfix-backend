import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as ApplicationError
from billing.models import BillingRecord
from billing.choices import BillingStatus
from common.utils.money import quantize_money
from .models import PaymentOrder, PaymentTransaction
from .choices import PaymentStatus, TransactionStatus
from fix_coins.services import reserve_coins, release_coins, redeem_reserved_coins
from fix_coins.choices import FixCoinReferenceType

class RazorpayClient:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            # We assume razorpay keys are in settings or decouple config
            key_id = getattr(settings, 'RAZORPAY_KEY_ID', 'test_key_id')
            key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', 'test_key_secret')
            cls._client = razorpay.Client(auth=(key_id, key_secret))
        return cls._client

class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_payment_order(billing_record: BillingRecord, customer) -> PaymentOrder:
        """
        Creates a PaymentOrder and corresponding Razorpay Order for a Finalized BillingRecord.
        Also reserves FixCoins if any are applied in the discount.
        """
        if billing_record.status != BillingStatus.FINALIZED:
            raise ApplicationError("Only FINALIZED billing records can be paid.")
            
        # Check if there is already an active payment order
        existing_order = PaymentOrder.objects.filter(
            billing_record=billing_record,
            status__in=[PaymentStatus.CREATED, PaymentStatus.ATTEMPTED]
        ).first()
        if existing_order:
            return existing_order
            
        amount_in_rupees = billing_record.payable_amount
        
        # Razorpay expects amount in paise (1 INR = 100 paise)
        amount_in_paise = int(amount_in_rupees * 100)
        
        # If fully paid via fix_coins or 100% discount, bypass Razorpay?
        # Assuming we still create a free order if needed, but for now we'll handle standard flow.
        if amount_in_paise <= 0:
            raise ApplicationError("Payable amount is 0. No payment order required.")
            
        client = RazorpayClient.get_client()
        rzp_order = client.order.create({
            "amount": amount_in_paise,
            "currency": billing_record.currency,
            "receipt": str(billing_record.billing_uuid),
            "payment_capture": 1 # Auto capture
        })
        
        payment_order = PaymentOrder.objects.create(
            billing_record=billing_record,
            customer=customer,
            amount=amount_in_rupees,
            currency=billing_record.currency,
            razorpay_order_id=rzp_order['id'],
            status=PaymentStatus.CREATED
        )
        
        # Reserve Fix-Coins if applied
        if billing_record.fix_coin_discount > 0:
            # Reconstruct coins to redeem from discount
            # This is a bit backwards, we should ideally store coins_redeemed in BillingRecord.
            # Assuming 10 coins = 1 INR
            # We can calculate it or better yet, assume we store it. Since we didn't, calculate:
            coins = int(billing_record.fix_coin_discount * 10)
            reserve_coins(
                user=customer,
                coins=coins,
                description=f"Reserved for Booking payment {payment_order.order_uuid}",
                reference_type=FixCoinReferenceType.PAYMENT,
                reference_id=str(payment_order.order_uuid)
            )
            
        return payment_order

    @staticmethod
    def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature) -> bool:
        """
        Verifies the Razorpay signature sent by the frontend callback.
        """
        client = RazorpayClient.get_client()
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    @staticmethod
    @transaction.atomic
    def process_successful_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature=None, webhook_payload=None):
        """
        Idempotent processor for successful payments.
        Can be called by frontend callback or Razorpay webhook.
        """
        order = PaymentOrder.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()
        if not order:
            raise ApplicationError("PaymentOrder not found.")
            
        if order.status == PaymentStatus.PAID:
            return order # Idempotent
            
        # Verify signature if provided (frontend flow)
        if razorpay_signature:
            is_valid = PaymentService.verify_payment_signature(
                razorpay_order_id, razorpay_payment_id, razorpay_signature
            )
            if not is_valid:
                raise ApplicationError("Invalid payment signature.")
                
        # Create Transaction
        tx = PaymentTransaction.objects.create(
            order=order,
            amount=order.amount,
            currency=order.currency,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            status=TransactionStatus.CAPTURED,
            gateway_response=webhook_payload or {}
        )
        
        # Update Order
        order.status = PaymentStatus.PAID
        order.processed_at = timezone.now()
        order.save()
        
        # Update BillingRecord
        billing = order.billing_record
        billing.status = BillingStatus.PAID
        billing.save()
        
        # Generate Invoice
        from invoices.services import InvoiceService
        InvoiceService.generate_invoice_for_billing(billing)
        
        # Finalize reserved coins
        if billing.fix_coin_discount > 0:
            coins = int(billing.fix_coin_discount * 10)
            redeem_reserved_coins(
                user=order.customer,
                coins=coins,
                description=f"Redeemed for successful payment {order.order_uuid}",
                reference_type=FixCoinReferenceType.PAYMENT,
                reference_id=str(order.order_uuid)
            )
            
        # Trigger Finance Ledger Entry creation
        from finance.services import LedgerService
        from finance.choices import FinanceAccountType, LedgerEntryType
        
        # 1. Platform Fee
        if billing.platform_fee > 0:
            LedgerService.add_pending_funds(
                user=None, # Platform account
                account_type=FinanceAccountType.PLATFORM,
                amount=billing.platform_fee,
                entry_type=LedgerEntryType.PLATFORM_FEE,
                reference_id=str(order.order_uuid),
                description=f"Platform fee for payment {order.order_uuid}"
            )
            
        # 2. Booking Fee
        if billing.booking_fee > 0:
            LedgerService.add_pending_funds(
                user=None,
                account_type=FinanceAccountType.PLATFORM,
                amount=billing.booking_fee,
                entry_type=LedgerEntryType.BOOKING_FEE,
                reference_id=str(order.order_uuid),
                description=f"Booking fee for payment {order.order_uuid}"
            )
            
        # 3. Business Earnings (Net amount)
        business_user = None
        if billing.booking:
            # For standard booking, we need the business user. Assuming booking -> service -> business -> owner
            # We don't have the exact model but `booking.service.business.owner` is typical.
            # Let's dynamically get it or just pass the business profile's user.
            pass
            
        # We will fully hook up business earnings in Phase 7 when Service Completion happens,
        # or we just log pending earnings now.
        
        return order
        
    @staticmethod
    @transaction.atomic
    def process_failed_payment(razorpay_order_id, razorpay_payment_id, error_code, error_desc, webhook_payload=None):
        """
        Idempotent processor for failed payments.
        """
        order = PaymentOrder.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()
        if not order:
            return None
            
        if order.status in [PaymentStatus.PAID, PaymentStatus.FAILED]:
            return order
            
        tx = PaymentTransaction.objects.create(
            order=order,
            amount=order.amount,
            currency=order.currency,
            razorpay_payment_id=razorpay_payment_id,
            status=TransactionStatus.FAILED,
            error_code=error_code,
            error_description=error_desc,
            gateway_response=webhook_payload or {}
        )
        
        order.status = PaymentStatus.FAILED
        order.processed_at = timezone.now()
        order.save()
        
        # Release reserved coins
        billing = order.billing_record
        if billing.fix_coin_discount > 0:
            coins = int(billing.fix_coin_discount * 10)
            release_coins(
                user=order.customer,
                coins=coins,
                description=f"Released due to failed payment {order.order_uuid}",
                reference_type=FixCoinReferenceType.PAYMENT,
                reference_id=str(order.order_uuid)
            )
            
        return order
