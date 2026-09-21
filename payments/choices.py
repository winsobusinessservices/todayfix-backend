from django.db import models
from django.utils.translation import gettext_lazy as _

class PaymentStatus(models.TextChoices):
    CREATED = "CREATED", _("Created")
    ATTEMPTED = "ATTEMPTED", _("Attempted")
    PAID = "PAID", _("Paid")
    FAILED = "FAILED", _("Failed")
    REFUNDED = "REFUNDED", _("Refunded")
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", _("Partially Refunded")

class TransactionStatus(models.TextChoices):
    AUTHORIZED = "AUTHORIZED", _("Authorized")
    CAPTURED = "CAPTURED", _("Captured")
    FAILED = "FAILED", _("Failed")
    REFUNDED = "REFUNDED", _("Refunded")
