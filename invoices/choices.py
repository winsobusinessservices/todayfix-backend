from django.db import models
from django.utils.translation import gettext_lazy as _

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    ISSUED = "ISSUED", _("Issued")
    VOID = "VOID", _("Void")
