from rest_framework import serializers
from .models import PaymentOrder, PaymentTransaction

class PaymentOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentOrder
        fields = [
            "order_uuid",
            "billing_record",
            "amount",
            "currency",
            "razorpay_order_id",
            "status",
            "created_at",
        ]
        read_only_fields = fields

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            "transaction_uuid",
            "order",
            "amount",
            "currency",
            "razorpay_payment_id",
            "status",
            "error_code",
            "error_description",
            "created_at",
        ]
        read_only_fields = fields

class CreatePaymentRequestSerializer(serializers.Serializer):
    billing_uuid = serializers.UUIDField()

class VerifyPaymentRequestSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=255)
