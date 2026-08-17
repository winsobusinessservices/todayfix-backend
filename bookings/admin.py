from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "user",
        "business",
        "service",
        "status",
        "scheduled_date",
        "scheduled_time",
    )

    list_filter = (
        "status",
        "scheduled_date",
    )

    search_fields = (
        "uuid",
        "user__email",
        "business__name",
        "service__name",
    )

    readonly_fields = (
        "uuid",
        "price",
        "created_at",
        "updated_at",
    )
