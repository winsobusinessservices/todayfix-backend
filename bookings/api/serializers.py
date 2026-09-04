from rest_framework import serializers

from accounts.models import CustomUser, Address
from business.models import BusinessProfile, Employee
from services.models import Service

from bookings.models import Booking, BookingEmployee
from bookings.choices import BookingSlotType

from django.utils import timezone

from instant_bookings.models import InstantBooking

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
    business_uuid = serializers.UUIDField()
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

# =============================================================
# UNIFIED BOOKING HISTORY SERIALIZER
# =============================================================

class BookingHistorySerializer(serializers.Serializer):

    booking_type = serializers.SerializerMethodField()
    booking_uuid = serializers.SerializerMethodField()

    user = BookingUserSerializer(read_only=True)
    business = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    address = BookingAddressSerializer(read_only=True)
    employee = serializers.SerializerMethodField()
    booking_employees = serializers.SerializerMethodField()

    scheduled_date = serializers.SerializerMethodField()
    scheduled_time = serializers.SerializerMethodField()
    slot_type = serializers.SerializerMethodField()

    price = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_booking_type(self, obj):
        if isinstance(obj, InstantBooking):
            return "INSTANT"
        return "SCHEDULED"

    def get_booking_uuid(self, obj):
        if isinstance(obj, InstantBooking):
            return str(obj.instant_booking_uuid)
        return str(obj.uuid)

    def get_business(self, obj):
        if isinstance(obj, InstantBooking):
            business = obj.assigned_business
        else:
            business = obj.business

        if not business:
            return None

        return BookingBusinessSerializer(business).data

    def get_service(self, obj):
        if isinstance(obj, InstantBooking):
            service = obj.selected_service

            if not service:
                return {
                    "service_uuid": None,
                    "name": obj.requested_service_name,
                    "duration": None,
                }
        else:
            service = obj.service

        return BookingServiceSerializer(service).data

    def get_employee(self, obj):
        if isinstance(obj, InstantBooking):
            employee = obj.assigned_employee
        else:
            employee = obj.employee

        if not employee:
            return None

        return BookingEmployeeSerializer(employee).data

    def get_booking_employees(self, obj):
        if isinstance(obj, InstantBooking):
            return []

        return BookingEmployeeAssignmentSerializer(
            obj.booking_employees.all(),
            many=True,
        ).data

    def get_scheduled_date(self, obj):
        if isinstance(obj, InstantBooking):
            return None
        return obj.scheduled_date

    def get_scheduled_time(self, obj):
        if isinstance(obj, InstantBooking):
            return None
        return obj.scheduled_time

    def get_slot_type(self, obj):
        if isinstance(obj, InstantBooking):
            return None
        return obj.slot_type

    def get_price(self, obj):
        if isinstance(obj, InstantBooking):
            return obj.total_payable_price
        return obj.price

    def get_status(self, obj):
        return obj.status

    def get_notes(self, obj):
        if isinstance(obj, InstantBooking):
            return obj.customer_note
        return obj.notes