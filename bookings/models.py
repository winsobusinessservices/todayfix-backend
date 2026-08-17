import uuid

from django.db import models
from core.models.base import TimeStampedModel
from accounts.models import CustomUser, Address
from business.models import BusinessProfile
from services.models import Service

from .choices import BookingStatus


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

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    scheduled_date = models.DateField()

    scheduled_time = models.TimeField()

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
