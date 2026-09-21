from rest_framework import serializers
from .models import PayoutAccount, Payout

class PayoutAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutAccount
        fields = [
            "account_uuid",
            "account_type",
            "account_number",
            "ifsc_code",
            "upi_id",
            "beneficiary_name",
            "is_verified",
            "is_primary",
            "created_at",
        ]
        read_only_fields = ["account_uuid", "is_verified", "created_at"]

class PayoutSerializer(serializers.ModelSerializer):
    payout_account = PayoutAccountSerializer(read_only=True)
    payout_account_uuid = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Payout
        fields = [
            "payout_uuid",
            "payout_account",
            "payout_account_uuid",
            "amount",
            "currency",
            "payout_type",
            "status",
            "reference_id",
            "failure_reason",
            "created_at",
        ]
        read_only_fields = [
            "payout_uuid", "currency", "status", "reference_id", "failure_reason", "created_at"
        ]

class PayoutRequestSerializer(serializers.Serializer):
    payout_account_uuid = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
