from django.contrib import admin

from .models import (
    InstantBooking,
    InstantBookingOffer,
    InstantBookingPricingRule,
)


@admin.register(InstantBookingPricingRule)
class InstantBookingPricingRuleAdmin(admin.ModelAdmin):
    """
    Admin configuration for distance-based instant pricing.

    Travel is charged only above the first 5 km.
    GST is applied to service + travel + platform fee.
    """

    list_display = (
        "minimum_distance_km",
        "maximum_distance_km",
        "platform_fee",
        "travel_fee_per_km",
        "gst_percentage",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    ordering = (
        "minimum_distance_km",
    )


@admin.register(InstantBooking)
class InstantBookingAdmin(admin.ModelAdmin):
    """
    Admin view for monitoring instant bookings.
    """

    list_display = (
        "instant_booking_uuid",
        "customer",
        "requested_service_name",
        "status",
        "average_service_price",
        "travel_charge",
        "platform_fee",
        "gst_amount",
        "quoted_price",
        "created_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "requested_service_name",
        "customer__email",
        "instant_booking_uuid",
    )

    readonly_fields = (
        "instant_booking_uuid",
        "created_at",
        "updated_at",
    )


@admin.register(InstantBookingOffer)
class InstantBookingOfferAdmin(admin.ModelAdmin):
    """
    Admin view for provider offers.

    The provider application normally reads these through
    the API, while Admin is useful for troubleshooting.
    """

    list_display = (
        "instant_booking",
        "business",
        "employee",
        "distance_km",
        "estimated_travel_minutes",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "instant_booking__instant_booking_uuid",
        "business__name",
        "employee__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )