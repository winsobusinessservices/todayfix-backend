import uuid

from django.db import models
from core.models.base import TimeStampedModel
from accounts.models import CustomUser, Address
from business.models import BusinessProfile, Employee
from services.models import Service

from .choices import BookingStatus, BookingSlotType


class Booking(TimeStampedModel):
    """
    Booking created by a User for a Business's Service.
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="bookings",
        null=True,
        blank=True,
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    scheduled_date = models.DateField()

    scheduled_time = models.TimeField()

    slot_type = models.CharField(
        max_length=10,
        choices=BookingSlotType.choices,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Snapshot of the service price at the time of booking.",
    )

    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the booking transitioned to COMPLETED.",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["business", "status"]),
            models.Index(fields=["scheduled_date"]),
        ]

    def __str__(self):
        return f"Booking {self.uuid} - {self.status}"

class BookingEmployee(TimeStampedModel):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_employees",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="booking_assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "employee"],
                name="unique_booking_employee",
            ),
        ]

    def __str__(self):
        return (
            f"{self.booking.uuid} - "
            f"{self.employee.name}"
        )

class BookingCompletionOTP(TimeStampedModel):
    """
    One-time passcode emailed to the customer when the provider
    marks a scheduled or instant booking as complete. The booking
    only moves to COMPLETED once this OTP is verified.

    Exactly one of `booking` / `instant_booking` is set.
    """

    otp_verification_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="completion_otps",
        null=True,
        blank=True,
    )

    instant_booking = models.ForeignKey(
        "instant_bookings.InstantBooking",
        on_delete=models.CASCADE,
        related_name="completion_otps",
        null=True,
        blank=True,
    )

    otp = models.CharField(
        max_length=6,
        default="",
    )

    otp_hash = models.CharField(
        max_length=128,
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0,
    )

    is_used = models.BooleanField(
        default=False,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["booking", "is_used"]),
            models.Index(fields=["instant_booking", "is_used"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(booking__isnull=False, instant_booking__isnull=True)
                    | models.Q(booking__isnull=True, instant_booking__isnull=False)
                ),
                name="completion_otp_exactly_one_booking_type",
            ),
        ]

    def __str__(self):
        target = self.booking or self.instant_booking
        return f"Completion OTP for {target}"