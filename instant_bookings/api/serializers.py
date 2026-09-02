from rest_framework import serializers

from accounts.models import Address
from instant_bookings.models import (
    InstantBooking,
    InstantBookingOffer,
)
from services.models import Service


class InstantServiceSearchSerializer(serializers.Serializer):
    """
    Query parameters for customer service search.
    """

    search = serializers.CharField(
        min_length=2,
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_search(self, value):
        return value.strip()


class InstantBookingCreateSerializer(serializers.Serializer):
    """
    Customer input for creating an instant booking.

    Category and subcategory are not customer inputs.
    """

    address_uuid = serializers.UUIDField()

    requested_service_name = serializers.CharField(
        max_length=255,
    )

    customer_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_requested_service_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Service name is required."
            )

        # Prevent creating a booking for a service that
        # no active business currently provides.
        service_exists = Service.objects.filter(
            name__iexact=value,
            is_active=True,
            business__is_active=True,
        ).exists()

        if not service_exists:
            raise serializers.ValidationError(
                (
                    f"No active provider currently offers "
                    f"the service '{value}'."
                )
            )

        return value

    def validate(self, attrs):
        user = self.context["request"].user

        address = Address.objects.filter(
            add_uuid=attrs["address_uuid"],
            user=user,
        ).first()

        if not address:
            raise serializers.ValidationError(
                {
                    "address_uuid": (
                        "The selected address does not belong "
                        "to the authenticated customer."
                    )
                }
            )

        if not address.location:
            raise serializers.ValidationError(
                {
                    "address_uuid": (
                        "The selected address must contain "
                        "a Google Maps location embed."
                    )
                }
            )

        attrs["address"] = address

        return attrs

    def create(self, validated_data):
        validated_data.pop("address_uuid")

        return InstantBooking.objects.create(
            customer=self.context["request"].user,
            **validated_data,
        )


class InstantBookingRetrySerializer(serializers.Serializer):
    """
    Input for retrying an instant-booking provider search.

    The customer may send a new tip or retry with no tip.
    """

    tip_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        default=0,
    )


class InstantServiceSearchResultSerializer(
    serializers.Serializer
):
    """
    Service result shown to the customer.
    """

    service_uuid = serializers.UUIDField()

    service_name = serializers.CharField(
        source="name"
    )

    description = serializers.CharField()

    category_name = serializers.CharField(
        source="category.name"
    )

    subcategory_name = serializers.CharField(
        source="subcategory.name",
        allow_null=True
    )

    indicative_price = serializers.DecimalField(
        source="price",
        max_digits=10,
        decimal_places=2,
    )

    duration_minutes = serializers.IntegerField(
        source="duration"
    )


class InstantBookingReadSerializer(serializers.ModelSerializer):
    """
    Booking response shown to the customer.
    """

    category_uuid = serializers.UUIDField(
        source="category.cat_uuid",
        read_only=True,
        allow_null=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        allow_null=True,
    )

    subcategory_uuid = serializers.UUIDField(
        source="subcategory.subCat_uuid",
        read_only=True,
        allow_null=True,
    )

    subcategory_name = serializers.CharField(
        source="subcategory.name",
        read_only=True,
        allow_null=True,
    )

    address_uuid = serializers.UUIDField(
        source="address.add_uuid",
        read_only=True,
    )

    class Meta:
        model = InstantBooking

        fields = [
            "instant_booking_uuid",
            "category_uuid",
            "category_name",
            "subcategory_uuid",
            "subcategory_name",
            "address_uuid",
            "requested_service_name",
            "customer_note",
            "average_service_price",
            "travel_charge",
            "platform_fee",
            "gst_percentage",
            "gst_amount",
            "quoted_price",
            "tip_amount",
            "total_payable_price",
            "search_distance_km",
            "offer_round",
            "expires_at",
            "search_deadline",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class InstantBookingOfferReadSerializer(
    serializers.ModelSerializer
):
    """
    Provider-offer response serializer.
    """

    service_uuid = serializers.UUIDField(
        source="service.service_uuid",
        read_only=True,
    )

    service_name = serializers.CharField(
        source="service.name",
        read_only=True,
    )

    business_uuid = serializers.UUIDField(
        source="business.business_profile_uuid",
        read_only=True,
    )

    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    employee_uuid = serializers.UUIDField(
        source="employee.employee_uuid",
        read_only=True,
        allow_null=True,
    )

    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True,
        allow_null=True,
    )

    instant_booking_uuid = serializers.UUIDField(
        source="instant_booking.instant_booking_uuid",
        read_only=True,
    )

    class Meta:
        model = InstantBookingOffer

        fields = [
            "id",
            "instant_booking_uuid",
            "service_uuid",
            "service_name",
            "business_uuid",
            "business_name",
            "employee_uuid",
            "employee_name",
            "distance_km",
            "estimated_travel_minutes",
            "status",
            "accepted_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields