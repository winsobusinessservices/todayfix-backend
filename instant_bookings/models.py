import uuid

from django.conf import settings
from django.db import models

from accounts.models import Address
from business.models import BusinessProfile, Employee
from categories.models import Category, SubCategory
from core.models.base import TimeStampedModel
from services.models import Service


class InstantBookingStatus(models.TextChoices):
    QUOTED = "QUOTED", "Quoted"
    SEARCHING = "SEARCHING", "Searching for provider"
    TIP_REQUIRED = "TIP_REQUIRED", "Tip required"
    ASSIGNED = "ASSIGNED", "Provider assigned"
    CANCELLED = "CANCELLED", "Cancelled"
    NO_PROVIDER = "NO_PROVIDER", "No provider found"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    EXPIRED = "EXPIRED", "Expired"


class InstantBookingOfferStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    DECLINED = "DECLINED", "Declined"
    EXPIRED = "EXPIRED", "Expired"


class InstantBookingPricingRule(TimeStampedModel):
    """
    Admin-managed pricing rule for one distance band.

    Example:
        0.00 to 5.00 km
        5.00 to 10.00 km
        10.00 to 15.00 km
    """

    rule_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    minimum_distance_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    maximum_distance_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    travel_fee_per_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    gst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="GST percentage applied to the subtotal.",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["minimum_distance_km"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "minimum_distance_km",
                    "maximum_distance_km",
                ],
                name="unique_instant_booking_distance_band",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    maximum_distance_km__gt=models.F(
                        "minimum_distance_km"
                    )
                ),
                name="valid_instant_booking_distance_band",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    platform_fee__gte=0
                ),
                name="non_negative_instant_platform_fee",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    travel_fee_per_km__gte=0
                ),
                name="non_negative_instant_travel_fee",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    gst_percentage__gte=0
                ),
                name="non_negative_instant_gst_percentage",
            ),
        ]

    def __str__(self):
        return (
            f"{self.minimum_distance_km} km - "
            f"{self.maximum_distance_km} km"
        )


class InstantBooking(TimeStampedModel):
    """
    Customer's instant service request.

    Category and subcategory are optional because the customer
    searches by service name. They are populated internally
    from the selected provider service.
    """

    instant_booking_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="instant_bookings",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="instant_bookings",
        null=True,
        blank=True,
    )

    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.PROTECT,
        related_name="instant_bookings",
        null=True,
        blank=True,
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="instant_bookings",
    )

    requested_service_name = models.CharField(
        max_length=255,
    )

    customer_note = models.TextField(
        blank=True,
        default="",
    )

    # Optional amount offered by the customer after a provider
    # does not accept during a five-minute offer round.
    tip_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Service quote before the optional customer tip.
    quoted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Final amount payable by the customer, including tip.
    total_payable_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    average_service_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    travel_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    gst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Current five-minute offer round number.
    offer_round = models.PositiveSmallIntegerField(
        default=1,
    )

    # End time of the current offer round.
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Absolute fifteen-minute deadline for the entire search.
    search_deadline = models.DateTimeField(
        null=True,
        blank=True,
    )

    search_distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    selected_service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="accepted_instant_bookings",
        null=True,
        blank=True,
    )

    assigned_business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.PROTECT,
        related_name="assigned_instant_bookings",
        null=True,
        blank=True,
    )

    assigned_employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="assigned_instant_bookings",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=InstantBookingStatus.choices,
        default=InstantBookingStatus.QUOTED,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    tip_amount__gte=0
                ),
                name="non_negative_instant_tip",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quoted_price__gte=0
                ),
                name="non_negative_instant_quoted_price",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    total_payable_price__gte=0
                ),
                name="non_negative_instant_total_price",
            ),
        ]

        indexes = [
            models.Index(
                fields=["customer", "status"]
            ),
            models.Index(
                fields=["status", "expires_at"]
            ),
            models.Index(
                fields=["status", "search_deadline"]
            ),
            models.Index(
                fields=["category", "subcategory"]
            ),
        ]

    def __str__(self):
        return (
            f"Instant booking "
            f"{self.instant_booking_uuid} - "
            f"{self.status}"
        )


class InstantBookingOffer(TimeStampedModel):
    """
    Offer sent to one eligible provider or employee.

    For individual businesses, employee is null.
    For company/investor businesses, employee identifies
    the qualified employee who can perform the service.
    """

    instant_booking = models.ForeignKey(
        InstantBooking,
        on_delete=models.CASCADE,
        related_name="provider_offers",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="instant_booking_offers",
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.PROTECT,
        related_name="instant_booking_offers",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="instant_booking_offers",
        null=True,
        blank=True,
    )

    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    estimated_travel_minutes = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=InstantBookingOfferStatus.choices,
        default=InstantBookingOfferStatus.PENDING,
        db_index=True,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["distance_km", "created_at"]

        indexes = [
            models.Index(
                fields=["instant_booking", "status"]
            ),
            models.Index(
                fields=["business", "status"]
            ),
            models.Index(
                fields=["employee", "status"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.instant_booking.instant_booking_uuid} - "
            f"{self.business.name} - "
            f"{self.status}"
        )