from django.contrib import admin

from .models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessPortfolio,
    BusinessPortfolioFAQ,
    BusinessPortfolioGalleryImage,
    BusinessProfile,
    Employee,
    ProviderAvailability,
    EmployeeWorkingSchedule,
    BusinessUpgradeRequest,
    BusinessUpgradeIdentity,
    BusinessUpgradeBankAccount,
)


@admin.register(BusinessApplication)
class BusinessApplicationAdmin(
    admin.ModelAdmin
):

    list_display = (
        "business_application_uuid",
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
        "business_application_uuid",
        "user__email",
    )

    readonly_fields = (
        "business_application_uuid",
        "created_at",
        "reviewed_at",
    )


@admin.register(BusinessIdentity)
class BusinessIdentityAdmin(
    admin.ModelAdmin
):

    list_display = (
        "business_identity_uuid",
        "application",
        "pan_number",
        "aadhaar_number",
        "gst_number",
        "created_at",
    )

    search_fields = (
        "business_identity_uuid",
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
        "business_bank_account_uuid",
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
        "business_bank_account_uuid",
        "application__uuid",
        "bank_name",
        "account_holder_name",
    )


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business_profile_uuid",
        "owner",
        "business_type",
        "category",
        "location",
        "name",
        "rank",
        "is_active",
        "created_at",
    )

    list_filter = (
        "business_type",
        "is_active",
    )

    list_editable = (
        "rank",
    )

    ordering = ("-rank", "-created_at")

    search_fields = (
        "business_profile_uuid",
        "owner__email",
        "name",
        "category",
    )

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_uuid",
        "name",
        "business",
        "email",
        "phone",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "employee_uuid",
        "name",
        "email",
        "phone",
        "business__name",
    )


@admin.register(ProviderAvailability)
class ProviderAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "provider_availability_uuid",
        "business",
        "owner",
        "employee",
        "status",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "provider_availability_uuid",
        "business__name",
        "owner__email",
        "employee__name",
    )


@admin.register(EmployeeWorkingSchedule)
class EmployeeWorkingScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "employee_working_schedule_uuid",
        "business",
        "owner",
        "employee",
        "day_of_week",
        "slot_type",
        "start_time",
        "end_time",
        "is_active",
    )

    list_filter = (
        "day_of_week",
        "slot_type",
        "is_active",
    )

    search_fields = (
        "employee_working_schedule_uuid",
        "business__name",
        "owner__email",
        "employee__name",
    )


@admin.register(BusinessUpgradeRequest)
class BusinessUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "business_upgrade_request_uuid",
        "business",
        "current_business_type",
        "requested_business_type",
        "status",
        "created_at",
        "reviewed_at",
    )

    list_filter = (
        "current_business_type",
        "requested_business_type",
        "status",
    )

    search_fields = (
        "business_upgrade_request_uuid",
        "business__name",
    )

    readonly_fields = (
        "business_upgrade_request_uuid",
        "created_at",
        "reviewed_at",
    )


@admin.register(BusinessUpgradeIdentity)
class BusinessUpgradeIdentityAdmin(admin.ModelAdmin):
    list_display = (
        "business_upgrade_identity_uuid",
        "request",
        "pan_number",
        "aadhaar_number",
        "gst_number",
        "created_at",
    )

    search_fields = (
        "business_upgrade_identity_uuid",
        "request__business_upgrade_request_uuid",
        "pan_number",
        "aadhaar_number",
        "gst_number",
    )


@admin.register(BusinessUpgradeBankAccount)
class BusinessUpgradeBankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "request",
        "account_holder_name",
        "bank_name",
        "ifsc_code",
    )

    search_fields = (
        "request__business_upgrade_request_uuid",
        "account_holder_name",
        "bank_name",
        "ifsc_code",
    )

class BusinessPortfolioGalleryImageInline(admin.TabularInline):
    model = BusinessPortfolioGalleryImage
    extra = 0
    fields = ("image", "caption", "created_at")
    readonly_fields = ("created_at",)


class BusinessPortfolioFAQInline(admin.TabularInline):
    model = BusinessPortfolioFAQ
    extra = 0
    fields = ("question", "answer", "order")


@admin.register(BusinessPortfolio)
class BusinessPortfolioAdmin(admin.ModelAdmin):
    list_display = (
        "business_portfolio_uuid",
        "business",
        "established_year",
        "starting_price",
        "response_time",
        "created_at",
    )

    list_filter = (
        "response_time",
    )

    search_fields = (
        "business_portfolio_uuid",
        "business__name",
        "business__owner__email",
    )

    readonly_fields = (
        "business_portfolio_uuid",
        "created_at",
        "updated_at",
    )

    inlines = (
        BusinessPortfolioGalleryImageInline,
        BusinessPortfolioFAQInline,
    )


@admin.register(BusinessPortfolioGalleryImage)
class BusinessPortfolioGalleryImageAdmin(admin.ModelAdmin):
    list_display = (
        "gallery_image_uuid",
        "portfolio",
        "caption",
        "created_at",
    )

    search_fields = (
        "gallery_image_uuid",
        "portfolio__business__name",
    )


@admin.register(BusinessPortfolioFAQ)
class BusinessPortfolioFAQAdmin(admin.ModelAdmin):
    list_display = (
        "faq_uuid",
        "portfolio",
        "question",
        "order",
    )

    search_fields = (
        "faq_uuid",
        "portfolio__business__name",
        "question",
    )

