from django.contrib import admin

from .models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessProfile,
)


@admin.register(BusinessApplication)
class BusinessApplicationAdmin(
    admin.ModelAdmin
):

    list_display = (
        "uuid",
        "user",
        "business_type",
        "status",
        "created_at",
        "reviewed_at",
    )

    list_filter = (
        "business_type",
        "status",
    )

    search_fields = (
        "uuid",
        "user__email",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "reviewed_at",
    )


@admin.register(BusinessIdentity)
class BusinessIdentityAdmin(
    admin.ModelAdmin
):

    list_display = (
        "uuid",
        "application",
        "pan_number",
        "aadhaar_number",
        "gst_number",
        "created_at",
    )

    search_fields = (
        "uuid",
        "application__uuid",
        "pan_number",
        "aadhaar_number",
        "gst_number",
    )


@admin.register(BusinessBankAccount)
class BusinessBankAccountAdmin(
    admin.ModelAdmin
):

    list_display = (
        "uuid",
        "application",
        "bank_name",
        "account_holder_name",
        "verification_status",
        "created_at",
    )

    list_filter = (
        "verification_status",
    )

    search_fields = (
        "uuid",
        "application__uuid",
        "bank_name",
        "account_holder_name",
    )


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "owner",
        "business_type",
        "name",
        "is_active",
        "created_at",
    )

    list_filter = (
        "business_type",
        "is_active",
    )

    search_fields = (
        "uuid",
        "owner__email",
        "name",
    )


