from rest_framework import serializers

from accounts.models import CustomUser, Address
from business.models import BusinessProfile, Employee
from services.models import Service

from bookings.models import Booking, BookingEmployee
from bookings.choices import BookingSlotType

from django.utils import timezone


# =============================================================
# NESTED SERIALIZERS (READ ONLY)
# =============================================================

class BookingUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "user_uuid",
            "first_name",
            "last_name",
            "phone",
        )


class BookingBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = (
            "business_profile_uuid",
            "name",
            "phone",
        )

class BookingEmployeeSerializer(serializers.ModelSerializer):

    employee_uuid = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "employee_uuid",
            "name",
            "phone",
        )

    def get_employee_uuid(self, obj):
        if not obj.is_active:
            return None
        return str(obj.employee_uuid)

    def get_name(self, obj):
        if not obj.is_active:
            return None
        return obj.name

    def get_phone(self, obj):
        if not obj.is_active:
            return None
        return obj.phone

class BookingEmployeeAssignmentSerializer(serializers.ModelSerializer):
    employee_uuid = serializers.UUIDField(
        source="employee.employee_uuid",
        read_only=True,
    )

    name = serializers.CharField(
        source="employee.name",
        read_only=True,
    )

    phone = serializers.CharField(
        source="employee.phone",
        read_only=True,
    )

    class Meta:
        model = BookingEmployee
        fields = (
            "employee_uuid",
            "name",
            "phone",
        )


class BookingServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "service_uuid",
            "name",
            "duration",
        )


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
    employee = BookingEmployeeSerializer(read_only=True)
    booking_employees = BookingEmployeeAssignmentSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Booking

        fields = (
            "uuid",
            "user",
            "business",
            "employee",
            "booking_employees",
            "service",
            "address",
            "scheduled_date",
            "scheduled_time",
            "slot_type",
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

    slot_type = serializers.ChoiceField(
        choices=BookingSlotType.choices,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):

        scheduled_date = attrs["scheduled_date"]

        slot_type = attrs["slot_type"]

        # -----------------------------------------------------
        # Booking date must be in the future
        # -----------------------------------------------------

        today = timezone.localdate()

        if scheduled_date <= today:
            raise serializers.ValidationError({
                "scheduled_date": (
                    "Booking date must be in the future."
                )
            })

        return attrs

class BookingEmployeeAssignSerializer(serializers.Serializer):

    employee_uuid = serializers.UUIDField()

class BookingEmployeeReassignSerializer(serializers.Serializer):

    old_employee_uuid = serializers.UUIDField()

    new_employee_uuid = serializers.UUIDField()