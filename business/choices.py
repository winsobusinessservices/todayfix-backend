from django.db import models
from django.utils.translation import gettext_lazy as _


class BusinessType(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", _("Individual")
    COMPANY = "COMPANY", _("Company")
    INVESTOR = "INVESTOR", _("Investor")


class BusinessApplicationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class BankVerificationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    VERIFIED = "VERIFIED", _("Verified")
    REJECTED = "REJECTED", _("Rejected")

    