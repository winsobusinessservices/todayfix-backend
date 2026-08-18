from rest_framework import serializers

from accounts.models import CustomUser, Address
from business.models import BusinessProfile
from services.models import Service

from bookings.models import Booking

from django.utils import timezone


# =============================================================
# NESTED SERIALIZERS (READ ONLY)
# =============================================================

class BookingUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("user_uuid", "first_name", "last_name", "phone")


class BookingBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = ("business_profile_uuid", "name", "phone")


class BookingServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("service_uuid", "name", "duration")


class BookingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "add_uuid",
            "address_type",
            "address_line",
            "locality",
            "city",
            "state",
            "pincode",
            "location",
        )


# =============================================================
# READ SERIALIZER
# =============================================================

class BookingReadSerializer(serializers.ModelSerializer):
    user = BookingUserSerializer(read_only=True)
    business = BookingBusinessSerializer(read_only=True)
    service = BookingServiceSerializer(read_only=True)
    address = BookingAddressSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = (
            "uuid",
            "user",
            "business",
            "service",
            "address",
            "scheduled_date",
            "scheduled_time",
            "price",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )


# =============================================================
# CREATE SERIALIZER
# =============================================================

class BookingCreateSerializer(serializers.Serializer):
    service_uuid = serializers.UUIDField()
    address_uuid = serializers.UUIDField()
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):
        scheduled_date = attrs["scheduled_date"]
        scheduled_time = attrs["scheduled_time"]

        scheduled_datetime = timezone.make_aware(
            timezone.datetime.combine(
                scheduled_date,
                scheduled_time,
            )
        )

        if scheduled_datetime <= timezone.now():
            raise serializers.ValidationError({
                "scheduled_date": (
                    "Booking date and time must be in the future."
                )
            })

        return attrs
