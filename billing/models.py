import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models.base import TimeStampedModel
from bookings.models import Booking
from instant_bookings.models import InstantBooking
from .choices import BillingStatus, BillingItemType, FeeType, BookingType

class PlatformFeeRule(TimeStampedModel):
    """
    Configurable platform fee rules based on amount slabs.
    """
    rule_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2)
    maximum_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["minimum_amount"]

    def __str__(self):
        return f"Platform Fee Rule ({self.percentage}%) for {self.minimum_amount} - {self.maximum_amount or 'MAX'}"

class BookingFeeRule(TimeStampedModel):
    """
    Configurable booking fee rules.
    """
    rule_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fee_type = models.CharField(max_length=20, choices=FeeType.choices, default=FeeType.FIXED_AMOUNT)
    fee_value = models.DecimalField(max_digits=10, decimal_places=2)
    booking_type = models.CharField(max_length=20, choices=BookingType.choices, default=BookingType.BOTH)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["minimum_amount"]

    def __str__(self):
        return f"Booking Fee Rule ({self.fee_type}: {self.fee_value})"

class BillingRecord(TimeStampedModel):
    """
    The central financial record for a customer booking.
    """
    billing_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, null=True, blank=True, related_name="billing_records")
    instant_booking = models.ForeignKey(InstantBooking, on_delete=models.PROTECT, null=True, blank=True, related_name="billing_records")
    currency = models.CharField(max_length=3, default="INR")
    
    # Core Components
    service_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    extended_service_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    material_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    travel_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Fees & Taxes
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    booking_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Totals & Discounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fix_coin_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Business settlement info
    business_gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    business_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    business_net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=30, choices=BillingStatus.choices, default=BillingStatus.DRAFT, db_index=True)
    version = models.PositiveIntegerField(default=1)
    
    calculation_snapshot = models.JSONField(default=dict, blank=True, help_text="A snapshot of all applied rules, rates, and parameters at the time of finalization.")
    
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(booking__isnull=False, instant_booking__isnull=True) |
                    models.Q(booking__isnull=True, instant_booking__isnull=False)
                ),
                name="billing_record_exactly_one_booking_type",
            ),
            models.UniqueConstraint(
                fields=["booking", "status"],
                condition=models.Q(status=BillingStatus.DRAFT),
                name="unique_draft_per_booking"
            ),
            models.UniqueConstraint(
                fields=["instant_booking", "status"],
                condition=models.Q(status=BillingStatus.DRAFT),
                name="unique_draft_per_instant_booking"
            ),
        ]

    def clean(self):
        super().clean()
        if bool(self.booking) == bool(self.instant_booking):
            raise ValidationError("Billing record must be attached to exactly one of Booking or InstantBooking.")

    def __str__(self):
        return f"Billing {self.billing_uuid} - v{self.version} - {self.status}"

class BillingItem(TimeStampedModel):
    """
    Extensible line items for a billing record.
    """
    item_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    billing = models.ForeignKey(BillingRecord, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=30, choices=BillingItemType.choices)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_amount = models.DecimalField(max_digits=10, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.item_type} - {self.line_amount}"
