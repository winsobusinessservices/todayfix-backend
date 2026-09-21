import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from fix_coins.choices import FixCoinReferenceType, FixCoinTransactionType


class FixCoinSettings(models.Model):
    """
    Singleton configuration for Fix-Coins business rules.
    Only one active record should exist.
    """
    coins_per_rupee = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Number of Fix-Coins equivalent to 1 INR (e.g. 10 coins = ₹1)",
    )
    signup_bonus_coins = models.PositiveIntegerField(
        default=500,
        validators=[MinValueValidator(0)],
        help_text="Bonus coins awarded upon successful new user verification",
    )
    reward_coins_per_100_rupees = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text="Coins earned per ₹100 of eligible spend",
    )
    minimum_redemption_coins = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(0)],
        help_text="Minimum coins required to execute a redemption",
    )
    maximum_redemption_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Maximum percentage of eligible booking value that can be paid via coins",
    )
    expiry_days = models.PositiveIntegerField(
        default=180,
        validators=[MinValueValidator(0)],
        help_text="Default days until credited coins expire",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates if this configuration is active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fix-Coin Setting"
        verbose_name_plural = "Fix-Coin Settings"

    def clean(self):
        super().clean()
        if self.coins_per_rupee < 1:
            raise ValidationError({"coins_per_rupee": "Coins per rupee must be at least 1."})
        if self.maximum_redemption_percentage < Decimal("0.00") or self.maximum_redemption_percentage > Decimal("100.00"):
            raise ValidationError({"maximum_redemption_percentage": "Percentage must be between 0 and 100."})
        if self.is_active:
            qs = FixCoinSettings.objects.filter(is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"is_active": "There can only be one active Fix-Coin Settings record."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"FixCoinSettings (active={self.is_active}, coins/INR={self.coins_per_rupee})"


class FixCoinWallet(models.Model):
    """
    User wallet tracking available Fix-Coins and aggregate lifetime stats.
    """
    wallet_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fix_coin_wallet",
    )
    available_coins = models.PositiveIntegerField(
        default=0,
        help_text="Current spendable Fix-Coins balance",
    )
    reserved_coins = models.PositiveIntegerField(
        default=0,
        help_text="Coins reserved for pending bookings",
    )
    lifetime_earned_coins = models.PositiveIntegerField(
        default=0,
        help_text="Total coins ever credited",
    )
    lifetime_redeemed_coins = models.PositiveIntegerField(
        default=0,
        help_text="Total coins ever debited via redemption",
    )
    lifetime_expired_coins = models.PositiveIntegerField(
        default=0,
        help_text="Total coins expired",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fix-Coin Wallet"
        verbose_name_plural = "Fix-Coin Wallets"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_coins__gte=0),
                name="fix_coin_wallet_available_coins_gte_0",
            ),
        ]

    def __str__(self):
        return f"Wallet({self.user}) - {self.available_coins} coins"


class FixCoinTransaction(models.Model):
    """
    Double-entry / audit ledger for every coin balance modification.
    Positive coins => credit. Negative coins => debit.
    """
    transaction_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    wallet = models.ForeignKey(
        FixCoinWallet,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=32,
        choices=FixCoinTransactionType.choices,
        db_index=True,
    )
    coins = models.IntegerField(
        help_text="Delta in coins: positive for credit, negative for debit",
    )
    balance_before = models.PositiveIntegerField(
        help_text="Wallet available coins before transaction",
    )
    balance_after = models.PositiveIntegerField(
        help_text="Wallet available coins after transaction",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    reference_type = models.CharField(
        max_length=32,
        choices=FixCoinReferenceType.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of related entity (e.g. SIGNUP, BOOKING, PAYMENT)",
    )
    reference_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifier of related entity (UUID, booking ID, etc.)",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when credited coins expire",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Fix-Coin Transaction"
        verbose_name_plural = "Fix-Coin Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
            models.Index(fields=["transaction_type", "wallet"]),
        ]

    def __str__(self):
        sign = "+" if self.coins > 0 else ""
        return f"{self.wallet.user}: {self.transaction_type} ({sign}{self.coins} coins)"
