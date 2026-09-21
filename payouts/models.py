import uuid
from django.db import models
from django.conf import settings
from core.models.base import TimeStampedModel
from .choices import PayoutStatus, PayoutType, AccountType

class PayoutAccount(TimeStampedModel):
    """
    Verified bank account or UPI details for a business payout.
    """
    account_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_accounts")
    
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.BANK_ACCOUNT)
    
    # Encrypted or masked in real life, plain for now depending on scope
    account_number = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=20, blank=True, default="")
    upi_id = models.CharField(max_length=100, blank=True, default="")
    
    beneficiary_name = models.CharField(max_length=255)
    
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}'s {self.account_type}"

class Payout(TimeStampedModel):
    """
    A request to withdraw funds.
    """
    payout_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payouts")
    payout_account = models.ForeignKey(PayoutAccount, on_delete=models.PROTECT)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    
    payout_type = models.CharField(max_length=20, choices=PayoutType.choices, default=PayoutType.WEEKLY)
    status = models.CharField(max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING)
    
    reference_id = models.CharField(max_length=100, blank=True, default="", help_text="Gateway payout ID")
    failure_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payout {self.payout_uuid} - {self.amount} ({self.status})"
