from django.db import models
from django.utils.translation import gettext_lazy as _

class PayoutStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    PROCESSING = "PROCESSING", _("Processing")
    COMPLETED = "COMPLETED", _("Completed")
    FAILED = "FAILED", _("Failed")
    REJECTED = "REJECTED", _("Rejected")

class PayoutType(models.TextChoices):
    WEEKLY = "WEEKLY", _("Weekly")
    EMERGENCY = "EMERGENCY", _("Emergency")

class AccountType(models.TextChoices):
    BANK_ACCOUNT = "BANK_ACCOUNT", _("Bank Account")
    UPI = "UPI", _("UPI")
