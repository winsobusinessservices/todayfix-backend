from django.contrib import admin

from .models import BusinessProfile, BusinessUpgradeRequest, ManagedBusiness


@admin.register(BusinessUpgradeRequest)
class BusinessUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "reviewed_by", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "business_type", "is_active", "created_at")
    list_filter = ("business_type", "is_active")
    search_fields = ("name", "owner__email")


@admin.register(ManagedBusiness)
class ManagedBusinessAdmin(admin.ModelAdmin):
    list_display = ("id", "manager_business", "linked_business", "created_at")
    search_fields = ("manager_business__name", "linked_business__name")
