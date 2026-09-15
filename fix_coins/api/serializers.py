from decimal import Decimal
from rest_framework import serializers

from fix_coins.models import FixCoinTransaction, FixCoinWallet
from fix_coins.services import calculate_rupee_value, get_fix_coin_settings


class FixCoinBalanceDataSerializer(serializers.Serializer):
    wallet_uuid = serializers.UUIDField(help_text="Unique UUID of the user wallet")
    available_coins = serializers.IntegerField(help_text="Current spendable Fix-Coins balance")
    coin_value_rupees = serializers.CharField(help_text="Equivalent monetary value in INR (e.g. 125.00)")
    lifetime_earned_coins = serializers.IntegerField(help_text="Total coins ever credited to this wallet")
    lifetime_redeemed_coins = serializers.IntegerField(help_text="Total coins ever redeemed")
    lifetime_expired_coins = serializers.IntegerField(help_text="Total coins ever expired")
    coins_per_rupee = serializers.IntegerField(help_text="Exchange rate: number of Fix-Coins per ₹1")


class FixCoinBalanceResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = FixCoinBalanceDataSerializer()


class FixCoinTransactionSerializer(serializers.ModelSerializer):
    expires_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z", allow_null=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z")

    class Meta:
        model = FixCoinTransaction
        fields = [
            "transaction_uuid",
            "transaction_type",
            "coins",
            "balance_before",
            "balance_after",
            "description",
            "reference_type",
            "reference_id",
            "expires_at",
            "created_at",
        ]


class FixCoinRedeemPreviewRequestSerializer(serializers.Serializer):
    eligible_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=True,
        help_text="Total booking / service amount eligible for coin redemption in INR",
    )
    coins_to_redeem = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Quantity of Fix-Coins the customer wishes to redeem",
    )


class FixCoinRedeemPreviewDataSerializer(serializers.Serializer):
    eligible_amount = serializers.CharField(help_text="Eligible spend amount formatted to two decimal places")
    requested_coins = serializers.IntegerField(help_text="Number of coins requested for redemption")
    approved_coins = serializers.IntegerField(help_text="Number of coins approved for redemption")
    discount_amount = serializers.CharField(help_text="Equivalent discount in INR")
    remaining_coins = serializers.IntegerField(help_text="Projected coins remaining in wallet after redemption")
    maximum_redeemable_coins = serializers.IntegerField(help_text="Maximum coin redemption ceiling for this amount")
    coins_per_rupee = serializers.IntegerField(help_text="Exchange rate: number of Fix-Coins per ₹1")


class FixCoinRedeemPreviewResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = FixCoinRedeemPreviewDataSerializer()
