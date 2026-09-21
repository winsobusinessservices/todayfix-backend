import uuid
from django.db import models
from core.models.base import TimeStampedModel
from django.utils.translation import gettext_lazy as _

class ReconciliationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    MATCHED = "MATCHED", _("Matched")
    DISCREPANCY = "DISCREPANCY", _("Discrepancy")

class ReconciliationReport(TimeStampedModel):
    """
    Nightly report mapping our DB records vs Payment Gateway Settlement records.
    """
    report_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    report_date = models.DateField(unique=True)
    
    total_expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_settled_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    expected_transactions_count = models.IntegerField(default=0)
    settled_transactions_count = models.IntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=ReconciliationStatus.choices, default=ReconciliationStatus.PENDING)
    
    notes = models.TextField(blank=True, default="")
    
    class Meta:
        ordering = ["-report_date"]
        
    def __str__(self):
        return f"Report {self.report_date} - {self.status}"
