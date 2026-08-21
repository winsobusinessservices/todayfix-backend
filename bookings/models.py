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
