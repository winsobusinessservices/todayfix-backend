from rest_framework import serializers
from .models import BillingRecord, BillingItem

class BillingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingItem
        fields = [
            "item_uuid",
            "item_type",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "tax_amount",
            "line_amount",
            "metadata",
        ]
        read_only_fields = fields

class BillingRecordSerializer(serializers.ModelSerializer):
    items = BillingItemSerializer(many=True, read_only=True)
    booking_uuid = serializers.UUIDField(source="booking.uuid", read_only=True, allow_null=True)
    instant_booking_uuid = serializers.UUIDField(source="instant_booking.instant_booking_uuid", read_only=True, allow_null=True)

    class Meta:
        model = BillingRecord
        fields = [
            "billing_uuid",
            "booking_uuid",
            "instant_booking_uuid",
            "currency",
            "service_amount",
            "extended_service_amount",
            "material_amount",
            "travel_amount",
            "tip_amount",
            "platform_fee",
            "booking_fee",
            "subtotal",
            "taxable_amount",
            "tax_amount",
            "fix_coin_discount",
            "discount_total",
            "gross_amount",
            "payable_amount",
            "status",
            "version",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

class BillingPreviewRequestSerializer(serializers.Serializer):
    booking_uuid = serializers.UUIDField(required=False, allow_null=True)
    instant_booking_uuid = serializers.UUIDField(required=False, allow_null=True)
    extended_service_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default="0.00")
    material_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default="0.00")
    travel_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default="0.00")
    tip_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default="0.00")
    fix_coins_to_redeem = serializers.IntegerField(default=0, min_value=0)

    def validate(self, attrs):
        booking = attrs.get("booking_uuid")
        instant = attrs.get("instant_booking_uuid")
        if bool(booking) == bool(instant):
            raise serializers.ValidationError("Provide exactly one of booking_uuid or instant_booking_uuid.")
        return attrs

class BillingPreviewResponseSerializer(serializers.Serializer):
    service_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    extended_service_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    material_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    travel_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    tip_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    booking_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    taxable_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    fix_coin_discount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    gross_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payable_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
