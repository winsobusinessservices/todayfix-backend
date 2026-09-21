from django.db import models
from django.utils.translation import gettext_lazy as _

class FinanceAccountType(models.TextChoices):
    PLATFORM = "PLATFORM", _("Platform")
    BUSINESS = "BUSINESS", _("Business")
    CUSTOMER = "CUSTOMER", _("Customer")

class LedgerEntryType(models.TextChoices):
    CUSTOMER_PAYMENT = "CUSTOMER_PAYMENT", _("Customer Payment")
    BUSINESS_EARNING = "BUSINESS_EARNING", _("Business Earning")
    PLATFORM_FEE = "PLATFORM_FEE", _("Platform Fee")
    BOOKING_FEE = "BOOKING_FEE", _("Booking Fee")
    REFUND = "REFUND", _("Refund")
    REFUND_REVERSAL = "REFUND_REVERSAL", _("Refund Reversal")
    PAYOUT = "PAYOUT", _("Payout")
    PAYOUT_REVERSAL = "PAYOUT_REVERSAL", _("Payout Reversal")
    TAX = "TAX", _("Tax")
    ADJUSTMENT = "ADJUSTMENT", _("Adjustment")

class AuditAction(models.TextChoices):
    CREATE = "CREATE", _("Create")
    UPDATE = "UPDATE", _("Update")
    DELETE = "DELETE", _("Delete")
    REFUND = "REFUND", _("Refund")
    ADJUST = "ADJUST", _("Adjust")
    APPROVE = "APPROVE", _("Approve")
    CANCEL = "CANCEL", _("Cancel")
