from django.db import models
from django.utils.translation import gettext_lazy as _

class BillingStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    CALCULATED = "CALCULATED", _("Calculated")
    PENDING_PAYMENT = "PENDING_PAYMENT", _("Pending Payment")
    PARTIALLY_PAID = "PARTIALLY_PAID", _("Partially Paid")
    PAID = "PAID", _("Paid")
    ADJUSTED = "ADJUSTED", _("Adjusted")
    REFUNDED = "REFUNDED", _("Refunded")
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", _("Partially Refunded")
    CANCELLED = "CANCELLED", _("Cancelled")
    FINALIZED = "FINALIZED", _("Finalized")

class BillingItemType(models.TextChoices):
    SERVICE = "SERVICE", _("Service")
    EXTENDED_SERVICE = "EXTENDED_SERVICE", _("Extended Service")
    MATERIAL = "MATERIAL", _("Material")
    TRAVEL = "TRAVEL", _("Travel")
    TIP = "TIP", _("Tip")
    PLATFORM_FEE = "PLATFORM_FEE", _("Platform Fee")
    BOOKING_FEE = "BOOKING_FEE", _("Booking Fee")
    TAX = "TAX", _("Tax")
    DISCOUNT = "DISCOUNT", _("Discount")
    FIX_COINS = "FIX_COINS", _("Fix Coins")
    ADJUSTMENT = "ADJUSTMENT", _("Adjustment")
    REFUND = "REFUND", _("Refund")

class FeeType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", _("Percentage")
    FIXED_AMOUNT = "FIXED_AMOUNT", _("Fixed Amount")

class BookingType(models.TextChoices):
    SCHEDULED = "SCHEDULED", _("Scheduled")
    INSTANT = "INSTANT", _("Instant")
    BOTH = "BOTH", _("Both")
