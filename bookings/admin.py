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
        "created_at",
        "updated_at",
    )

    def get_readonly_fields(self, request, obj=None):
        # price is a locked-in snapshot once a booking exists, but it
        # has to be enterable when creating a booking directly through
        # admin - otherwise the add form can never provide a value and
        # saving always fails with a NULL 'price' column.
        if obj is not None:
            return self.readonly_fields + ("price",)
        return self.readonly_fields

@admin.register(BookingEmployee)
class BookingEmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "employee")
    search_fields = ("booking__uuid", "employee__name")
