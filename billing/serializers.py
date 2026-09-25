from decimal import Decimal
from rest_framework import serializers
from .models import BillingRecord, BillingItem


class _RejectUnknownFieldsMixin:
    def to_internal_value(self, data):
        unknown_fields = set(data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise serializers.ValidationError(
                {field: "This field is not allowed." for field in unknown_fields}
            )
        return super().to_internal_value(data)

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

class BillingPreviewRequestSerializer(_RejectUnknownFieldsMixin, serializers.Serializer):
    """
    Used by preview only. Stays open to both the customer and the
    business owner as a general estimate tool - either side can see
    what the bill would look like before committing anything.
    """
    booking_uuid = serializers.UUIDField(required=False, allow_null=True)
    instant_booking_uuid = serializers.UUIDField(required=False, allow_null=True)
    extended_service_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), min_value=Decimal("0.00"))
    material_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), min_value=Decimal("0.00"))
    tip_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal("0.00"))
    fix_coins_to_redeem = serializers.IntegerField(default=0, min_value=0)

    def validate(self, attrs):
        booking = attrs.get("booking_uuid")
        instant = attrs.get("instant_booking_uuid")
        if bool(booking) == bool(instant):
            raise serializers.ValidationError("Provide exactly one of booking_uuid or instant_booking_uuid.")
        return attrs


class BillingDraftCreateRequestSerializer(_RejectUnknownFieldsMixin, serializers.Serializer):
    """
    Used by create_draft only. Business-owner-only endpoint: accepts
    just the booking reference plus the business's own charges. Tip
    and FixCoins redemption are the customer's concern and belong to
    the adjust step instead, not here.
    """
    booking_uuid = serializers.UUIDField(required=False, allow_null=True)
    instant_booking_uuid = serializers.UUIDField(required=False, allow_null=True)
    extended_service_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), min_value=Decimal("0.00"))
    material_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), min_value=Decimal("0.00"))

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

class BillingAdjustmentRequestSerializer(_RejectUnknownFieldsMixin, serializers.Serializer):
    """
    Used by adjust only. Customer-only endpoint: adds a tip and/or
    redeems FixCoins on an already-finalized bill. The business
    owner's extended_service_amount/material_amount are carried
    forward automatically and cannot be touched here.
    """
    tip_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=Decimal("0.00"))
    fix_coins_to_redeem = serializers.IntegerField(required=False, min_value=0)
