from django.contrib import admin

from .models import Booking, BookingEmployee


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

@admin.register(BookingEmployee)
class BookingEmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "employee")
    search_fields = ("booking__uuid", "employee__name")
