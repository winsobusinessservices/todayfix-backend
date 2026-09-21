import uuid
from django.db import models
from django.conf import settings
from core.models.base import TimeStampedModel
from .choices import AuditAction

class FinancialAuditLog(TimeStampedModel):
    """
    Audit log for sensitive financial actions.
    Records who did what, when, and why.
    """
    audit_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_audit_logs",
        help_text="User/Admin who performed the action. Null if system.",
    )

    action = models.CharField(
        max_length=50,
        choices=AuditAction.choices,
        db_index=True,
    )

    object_type = models.CharField(
        max_length=100,
        help_text="The type of the object being modified (e.g. 'Payout', 'FinanceAccount', 'FixCoinWallet').",
        db_index=True,
    )

    object_id = models.CharField(
        max_length=255,
        help_text="The unique identifier (UUID or ID) of the modified object.",
        db_index=True,
    )

    old_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="The state of the object before the modification.",
    )

    new_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="The state of the object after the modification.",
    )

    reason = models.TextField(
        blank=True,
        default="",
        help_text="Why this action was performed (especially important for manual adjustments).",
    )

    request_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional ID mapping to the external request or idempotent request ID.",
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "action"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        actor_name = self.actor.email if self.actor else "System"
        return f"{actor_name} {self.action} {self.object_type} {self.object_id}"

from .choices import FinanceAccountType, LedgerEntryType

class FinanceAccount(TimeStampedModel):
    """
    Central financial account for a business, customer, or the platform.
    """
    account_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="finance_accounts")
    account_type = models.CharField(max_length=20, choices=FinanceAccountType.choices)
    
    currency = models.CharField(max_length=3, default="INR")
    
    # Funds that are collected but not yet available for payout (e.g., service not completed)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Funds available for payout
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Analytics
    lifetime_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lifetime_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(account_type=FinanceAccountType.PLATFORM) | models.Q(user__isnull=False),
                name="finance_account_user_required_unless_platform",
            )
        ]

    def __str__(self):
        return f"{self.account_type} Account {self.account_uuid}"

class LedgerEntry(TimeStampedModel):
    """
    Immutable double-entry ledger record.
    """
    entry_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT, related_name="ledger_entries")
    entry_type = models.CharField(max_length=30, choices=LedgerEntryType.choices)
    
    # Positive for credit (incoming), negative for debit (outgoing)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Reference to the source of truth (e.g., PaymentOrder UUID, Payout UUID)
    reference_id = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True, default="")
    
    # True if this moved funds directly into 'available', False if it went into 'pending'
    is_available = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference_id"]),
            models.Index(fields=["account", "entry_type"]),
        ]

    def __str__(self):
        return f"LedgerEntry {self.entry_uuid} ({self.amount})"
