import uuid
from django.db import models
from django.conf import settings
from core.models.base import TimeStampedModel
from billing.models import BillingRecord
from .choices import PaymentStatus, TransactionStatus

class PaymentOrder(TimeStampedModel):
    """
    Intent to pay for a specific finalized BillingRecord.
    Links 1:1 with Razorpay Order.
    """
    order_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    billing_record = models.ForeignKey(BillingRecord, on_delete=models.PROTECT, related_name="payment_orders")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_orders")
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in INR intended to be paid")
    currency = models.CharField(max_length=3, default="INR")
    
    razorpay_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.CREATED)
    
    # Used for idempotency during webhook processing
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PaymentOrder {self.order_uuid} - {self.status}"


class PaymentTransaction(TimeStampedModel):
    """
    Individual payment attempt (capture, failure, refund).
    """
    transaction_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    order = models.ForeignKey(PaymentOrder, on_delete=models.CASCADE, related_name="transactions")
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    
    razorpay_payment_id = models.CharField(max_length=100, unique=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    
    status = models.CharField(max_length=30, choices=TransactionStatus.choices)
    
    error_code = models.CharField(max_length=100, blank=True, default="")
    error_description = models.TextField(blank=True, default="")
    
    # Information payload from Razorpay webhook
    gateway_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Tx {self.razorpay_payment_id} - {self.status}"
