
from django.contrib import admin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "role",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
    )
    