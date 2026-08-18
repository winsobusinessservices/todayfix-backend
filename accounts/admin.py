
from django.contrib import admin

from .models import CustomUser, PasswordResetToken, PendingRegistration
from .models import EmailTemplate

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_uuid",
        "first_name",
        "last_name",
        "email",
        "phone",
        "role",
        "is_active",
        "is_staff",
        "verified_at",
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




@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "expires_at",
        "is_used",
    )

    list_filter = (
        "is_used",
        "created_at",
    )

    search_fields = (
        "user__email",
        "token",
    )

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "subject",
    )

    search_fields = (
        "name",
        "subject",
    )

@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "pending_registration_uuid",
        "first_name",
        "last_name",
        "email",
        "phone",
        "created_at",
        "expires_at",
    )

    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "token",
        "uuid",
    )

    list_filter = (
        "created_at",
        "expires_at",
    )
    