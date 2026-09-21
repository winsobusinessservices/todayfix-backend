from django.contrib import admin
from .models import BillingRecord, BillingItem, PlatformFeeRule, BookingFeeRule

@admin.register(PlatformFeeRule)
class PlatformFeeRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_uuid", "percentage", "minimum_amount", "maximum_amount", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active",)
    search_fields = ("rule_uuid",)

@admin.register(BookingFeeRule)
class BookingFeeRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_uuid", "fee_type", "fee_value", "minimum_amount", "maximum_amount", "booking_type", "is_active", "effective_from", "effective_to")
    list_filter = ("is_active", "fee_type", "booking_type")
    search_fields = ("rule_uuid",)

class BillingItemInline(admin.TabularInline):
    model = BillingItem
    extra = 0

@admin.register(BillingRecord)
class BillingRecordAdmin(admin.ModelAdmin):
    list_display = ("billing_uuid", "status", "currency", "payable_amount", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("billing_uuid",)
    inlines = [BillingItemInline]
