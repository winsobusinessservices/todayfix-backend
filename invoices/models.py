import uuid
from django.db import models
from django.conf import settings
from core.models.base import TimeStampedModel
from billing.models import BillingRecord
from .choices import InvoiceStatus

class Invoice(TimeStampedModel):
    """
    Immutable legal document representing a finalized sale.
    """
    invoice_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    billing_record = models.OneToOneField(BillingRecord, on_delete=models.PROTECT, related_name="invoice")
    
    # Auto-incrementing legal sequence (e.g. TF-2026-0001)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED)
    
    # Snapshot of company info at the time of issue
    company_name = models.CharField(max_length=255, default="TodayFix Inc.")
    company_address = models.TextField(default="123 Platform Way")
    company_gstin = models.CharField(max_length=20, default="29ABCDE1234F1Z5")
    
    # Snapshot of customer info
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(blank=True, default="")
    customer_address = models.TextField(blank=True, default="")
    
    # Totals (Copied from BillingRecord for immutability)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_total = models.DecimalField(max_digits=10, decimal_places=2)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    
    # Optional URL to the generated PDF
    pdf_url = models.URLField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number}"

class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0) # percentage
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} (x{self.quantity})"
