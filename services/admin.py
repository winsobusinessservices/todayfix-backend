from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "service_uuid",
        "name",
        "business",
        "category",
        "price",
        "duration",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "category",
    )

    search_fields = (
        "service_uuid",
        "name",
        "business__name",
    )

    readonly_fields = (
        "service_uuid",
        "created_at",
        "updated_at",
    )
