import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from fix_coins.choices import FixCoinReferenceType, FixCoinTransactionType
from fix_coins.models import FixCoinSettings, FixCoinTransaction, FixCoinWallet

logger = logging.getLogger(__name__)


def get_fix_coin_settings() -> FixCoinSettings:
    """
    Returns the active FixCoinSettings singleton or a safe default instance.
    """
    settings_obj = FixCoinSettings.objects.filter(is_active=True).first()
    if not settings_obj:
        # Create an active default instance if none exists
        settings_obj, _ = FixCoinSettings.objects.get_or_create(
            is_active=True,
            defaults={
                "coins_per_rupee": 10,
                "signup_bonus_coins": 500,
                "reward_coins_per_100_rupees": 10,
                "minimum_redemption_coins": 100,
                "maximum_redemption_percentage": Decimal("15.00"),
                "expiry_days": 180,
            },
        )
    return settings_obj


def get_or_create_wallet(user) -> FixCoinWallet:
    """
    Retrieves or creates a FixCoinWallet for the given user.
    """
    wallet, _ = FixCoinWallet.objects.get_or_create(user=user)
    return wallet


def get_balance(user) -> int:
    """
    Returns the current spendable Fix-Coins balance for the user.
    """
    wallet = FixCoinWallet.objects.filter(user=user).first()
    return wallet.available_coins if wallet else 0


def calculate_rupee_value(coins: int, coins_per_rupee: int = None) -> Decimal:
    """
    Calculates the Rupee equivalent of a given number of Fix-Coins.
    10 Fix-Coins = ₹1 -> rupee_value = coins / 10
    """
    if coins <= 0:
        return Decimal("0.00")
    if coins_per_rupee is None:
        settings_obj = get_fix_coin_settings()
        coins_per_rupee = settings_obj.coins_per_rupee
    if coins_per_rupee <= 0:
        coins_per_rupee = 10

    rupees = Decimal(coins) / Decimal(coins_per_rupee)
    return rupees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_coin_value_rupees(coins: int) -> Decimal:
    """
    Alias for calculate_rupee_value using active settings.
    """
    return calculate_rupee_value(coins)


def calculate_booking_reward(eligible_amount: Decimal) -> int:
    """
    Calculates future booking reward coins.
    10 Fix-Coins per ₹100 eligible spend.
    Integer division on whole units of 100 rupees.
    """
    if eligible_amount <= Decimal("0.00"):
        return 0
    settings_obj = get_fix_coin_settings()
    rate = settings_obj.reward_coins_per_100_rupees
    # Calculate per full 100 rupees: int(eligible_amount / 100) * rate
    hundreds = int(eligible_amount // Decimal("100.00"))
    return hundreds * rate


def credit_coins(
    user,
    coins: int,
    transaction_type: str,
    description: str = "",
    reference_type: str = None,
    reference_id: str = None,
    expires_at=None,
) -> FixCoinTransaction:
    """
    Atomically credits coins to user's wallet and creates a ledger record.
    Positive coins only.
    """
    if coins <= 0:
        raise ValidationError("Coins to credit must be a positive integer.")

    settings_obj = get_fix_coin_settings()
    if expires_at is None and settings_obj.expiry_days > 0:
        expires_at = timezone.now() + timedelta(days=settings_obj.expiry_days)

    with transaction.atomic():
        wallet, _ = FixCoinWallet.objects.select_for_update().get_or_create(user=user)
        balance_before = wallet.available_coins
        balance_after = balance_before + coins

        wallet.available_coins = balance_after
        wallet.lifetime_earned_coins += coins
        wallet.save(update_fields=["available_coins", "lifetime_earned_coins", "updated_at"])

        tx = FixCoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            coins=coins,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            expires_at=expires_at,
        )

    return tx


def debit_coins(
    user,
    coins: int,
    transaction_type: str,
    description: str = "",
    reference_type: str = None,
    reference_id: str = None,
) -> FixCoinTransaction:
    """
    Atomically debits coins from user's wallet and creates a ledger record.
    Positive integer parameter `coins` is deducted (stored as -coins).
    Rejects any debit that would result in a negative balance.
    """
    if coins <= 0:
        raise ValidationError("Coins to debit must be a positive integer.")

    with transaction.atomic():
        wallet, _ = FixCoinWallet.objects.select_for_update().get_or_create(user=user)
        balance_before = wallet.available_coins

        if balance_before < coins:
            raise ValidationError(
                f"Insufficient Fix-Coins. Available: {balance_before}, requested: {coins}."
            )

        balance_after = balance_before - coins
        wallet.available_coins = balance_after
        if transaction_type == FixCoinTransactionType.REDEMPTION:
            wallet.lifetime_redeemed_coins += coins
            wallet.save(update_fields=["available_coins", "lifetime_redeemed_coins", "updated_at"])
        elif transaction_type == FixCoinTransactionType.EXPIRY:
            wallet.lifetime_expired_coins += coins
            wallet.save(update_fields=["available_coins", "lifetime_expired_coins", "updated_at"])
        else:
            wallet.save(update_fields=["available_coins", "updated_at"])

        tx = FixCoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            coins=-coins,  # Negative for debits
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    return tx


def validate_redemption(user, eligible_amount: Decimal, coins_to_redeem: int) -> dict:
    """
    Validates a potential coin redemption against business rules without modifying balance.
    Returns preview dict or raises ValidationError.
    """
    if eligible_amount <= Decimal("0.00"):
        raise ValidationError({"eligible_amount": "Eligible amount must be greater than zero."})

    if coins_to_redeem <= 0:
        raise ValidationError({"coins_to_redeem": "Coins to redeem must be greater than zero."})

    settings_obj = get_fix_coin_settings()
    if not settings_obj.is_active:
        raise ValidationError({"detail": "Fix-Coins redemptions are currently inactive."})

    min_coins = settings_obj.minimum_redemption_coins
    if coins_to_redeem < min_coins:
        raise ValidationError({
            "coins_to_redeem": f"Minimum redemption is {min_coins} Fix-Coins."
        })

    # Calculate maximum redeemable coins based on percentage limit
    # max_discount = eligible_amount * (max_pct / 100)
    # max_coins = int(max_discount * coins_per_rupee)
    max_discount = (eligible_amount * settings_obj.maximum_redemption_percentage) / Decimal("100.00")
    max_coins = int(max_discount * Decimal(settings_obj.coins_per_rupee))

    if coins_to_redeem > max_coins:
        raise ValidationError({
            "coins_to_redeem": (
                f"Maximum redeemable amount for this booking is {max_coins} Fix-Coins "
                f"({settings_obj.maximum_redemption_percentage}% of eligible amount)."
            )
        })

    wallet = FixCoinWallet.objects.filter(user=user).first()
    available_coins = wallet.available_coins if wallet else 0

    if coins_to_redeem > available_coins:
        raise ValidationError({
            "coins_to_redeem": f"You have {available_coins} Fix-Coins available, but requested {coins_to_redeem}."
        })

    discount_amount = calculate_rupee_value(coins_to_redeem, settings_obj.coins_per_rupee)
    remaining_coins = available_coins - coins_to_redeem

    return {
        "eligible_amount": f"{eligible_amount:.2f}",
        "requested_coins": coins_to_redeem,
        "approved_coins": coins_to_redeem,
        "discount_amount": f"{discount_amount:.2f}",
        "remaining_coins": remaining_coins,
        "maximum_redeemable_coins": max_coins,
        "coins_per_rupee": settings_obj.coins_per_rupee,
    }


def grant_signup_bonus(user) -> bool:
    """
    Awards 500 Fix-Coins signup bonus to a newly created/verified user.
    Strictly idempotent:
    - Atomically locks wallet
    - Checks if SIGNUP_BONUS transaction already exists for this wallet
    - If already granted, safely returns False without duplicating
    - Returns True if bonus was newly credited
    """
    if not user or not user.pk:
        return False

    settings_obj = get_fix_coin_settings()
    bonus_coins = settings_obj.signup_bonus_coins

    if bonus_coins <= 0:
        return False

    with transaction.atomic():
        wallet, _ = FixCoinWallet.objects.select_for_update().get_or_create(user=user)

        # Check existing signup bonus transactions for this wallet
        already_granted = FixCoinTransaction.objects.filter(
            wallet=wallet,
            transaction_type=FixCoinTransactionType.SIGNUP_BONUS,
        ).exists()

        if already_granted:
            logger.info("Signup bonus already granted for user %s. Skipping.", user.pk)
            return False

        balance_before = wallet.available_coins
        balance_after = balance_before + bonus_coins

        wallet.available_coins = balance_after
        wallet.lifetime_earned_coins += bonus_coins
        wallet.save(update_fields=["available_coins", "lifetime_earned_coins", "updated_at"])

        expires_at = None
        if settings_obj.expiry_days > 0:
            expires_at = timezone.now() + timedelta(days=settings_obj.expiry_days)

        FixCoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=FixCoinTransactionType.SIGNUP_BONUS,
            coins=bonus_coins,
            balance_before=balance_before,
            balance_after=balance_after,
            description="Welcome bonus",
            reference_type=FixCoinReferenceType.SIGNUP,
            reference_id=str(getattr(user, "user_uuid", user.pk)),
            expires_at=expires_at,
        )

        logger.info("Successfully granted %s signup Fix-Coins to user %s", bonus_coins, user.pk)
        return True


def reverse_transaction(tx_uuid: str, reason: str = "") -> FixCoinTransaction:
    """
    Reverses an existing transaction.
    If original was credit (+X), debits X with REFUND_REVERSAL.
    If original was debit (-X), credits X with REFUND_REVERSAL.
    """
    original_tx = FixCoinTransaction.objects.get(transaction_uuid=tx_uuid)
    user = original_tx.wallet.user

    if original_tx.coins > 0:
        # Reversing a credit requires debiting
        return debit_coins(
            user=user,
            coins=original_tx.coins,
            transaction_type=FixCoinTransactionType.REFUND_REVERSAL,
            description=f"Reversal of {original_tx.transaction_uuid}: {reason}",
            reference_type=FixCoinReferenceType.REFUND,
            reference_id=str(original_tx.transaction_uuid),
        )
    else:
        # Reversing a debit requires crediting
        return credit_coins(
            user=user,
            coins=abs(original_tx.coins),
            transaction_type=FixCoinTransactionType.REFUND_REVERSAL,
            description=f"Reversal of {original_tx.transaction_uuid}: {reason}",
            reference_type=FixCoinReferenceType.REFUND,
            reference_id=str(original_tx.transaction_uuid),
        )
