
from django.contrib import admin

from .models import CustomUser, PasswordResetToken, PendingRegistration
from .models import EmailTemplate

from .models import OTPVerification, Address, SignupOTPVerification, GoogleIdentity

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

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "otp_verification_uuid", "user", "phone")
    search_fields = ("phone", "user__email", "otp_verification_uuid")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "add_uuid", "user", "address_line", "city", "state", "pincode", "address_type", "is_default")
    list_filter = ("address_type", "is_default", "state")
    search_fields = ("add_uuid", "user__email", "address_line", "city", "pincode")


@admin.register(SignupOTPVerification)
class SignupOTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "signup_otp_verification_uuid", "phone", "attempts", "is_used", "expires_at", "verified_at", "created_at")
    list_filter = ("is_used", "created_at")
    search_fields = ("phone", "signup_otp_verification_uuid")


@admin.register(GoogleIdentity)
class GoogleIdentityAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "google_sub", "google_email", "created_at")
    search_fields = ("user__email", "google_sub", "google_email")
    