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

class EmployeeAvailabilityStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", _("Available")
    UNAVAILABLE = "UNAVAILABLE", _("Unavailable")
    BUSY = "BUSY", _("Busy")

class DayOfWeek(models.TextChoices):
    MONDAY = "MONDAY", _("Monday")
    TUESDAY = "TUESDAY", _("Tuesday")
    WEDNESDAY = "WEDNESDAY", _("Wednesday")
    THURSDAY = "THURSDAY", _("Thursday")
    FRIDAY = "FRIDAY", _("Friday")
    SATURDAY = "SATURDAY", _("Saturday")
    SUNDAY = "SUNDAY", _("Sunday")

    
