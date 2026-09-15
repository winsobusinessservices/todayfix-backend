import uuid
from datetime import timedelta
from django.db import migrations, transaction
from django.utils import timezone


def backfill_signup_bonus(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    FixCoinSettings = apps.get_model('fix_coins', 'FixCoinSettings')
    FixCoinWallet = apps.get_model('fix_coins', 'FixCoinWallet')
    FixCoinTransaction = apps.get_model('fix_coins', 'FixCoinTransaction')

    # Get settings or use defaults
    settings = FixCoinSettings.objects.filter(is_active=True).first()
    bonus_coins = settings.signup_bonus_coins if settings else 500
    expiry_days = settings.expiry_days if settings else 180

    # We use timezone.now() outside the loop so all backfilled transactions have the same timestamp
    now = timezone.now()
    expires_at = now + timedelta(days=expiry_days)

    for user in CustomUser.objects.all():
        with transaction.atomic():
            wallet, created = FixCoinWallet.objects.get_or_create(user=user)

            # Check if user already received a SIGNUP_BONUS
            has_bonus = FixCoinTransaction.objects.filter(
                wallet=wallet,
                transaction_type="SIGNUP_BONUS"
            ).exists()

            if not has_bonus:
                balance_before = wallet.available_coins

                wallet.available_coins += bonus_coins
                wallet.lifetime_earned_coins += bonus_coins
                wallet.save(update_fields=['available_coins', 'lifetime_earned_coins'])

                FixCoinTransaction.objects.create(
                    transaction_uuid=uuid.uuid4(),
                    wallet=wallet,
                    transaction_type="SIGNUP_BONUS",
                    coins=bonus_coins,
                    balance_before=balance_before,
                    balance_after=wallet.available_coins,
                    description="Backfilled welcome bonus for existing user",
                    reference_type="SIGNUP",
                    reference_id=str(user.user_uuid) if hasattr(user, 'user_uuid') else str(user.pk),
                    expires_at=expires_at,
                    created_at=now,
                )


def reverse_backfill(apps, schema_editor):
    # Idempotent migration, no reversal required
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('fix_coins', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_signup_bonus, reverse_backfill),
    ]
