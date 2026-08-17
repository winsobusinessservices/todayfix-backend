from rest_framework import serializers

from accounts.models import CustomUser, Address
from business.models import BusinessProfile
from services.models import Service

from bookings.models import Booking


# =============================================================
# NESTED SERIALIZERS (READ ONLY)
# =============================================================

class BookingUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("uuid", "first_name", "last_name", "phone")


class BookingBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = ("uuid", "name", "phone")


class BookingServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("uuid", "name", "duration")


class BookingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "uuid",
            "address_type",
            "address_line",
            "locality",
            "city",
            "state",
            "pincode",
            "latitude",
            "longitude",
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
        required=False, allow_blank=True, default=""
    )
