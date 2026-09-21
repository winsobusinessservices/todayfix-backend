from django.contrib import admin
from .models import PayoutAccount, Payout

@admin.register(PayoutAccount)
class PayoutAccountAdmin(admin.ModelAdmin):
    list_display = ("account_uuid", "user", "account_type", "is_verified", "is_primary", "created_at")
    list_filter = ("account_type", "is_verified", "is_primary")
    search_fields = ("account_uuid", "user__email", "account_number", "upi_id")

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("payout_uuid", "user", "amount", "currency", "payout_type", "status", "created_at")
    list_filter = ("payout_type", "status")
    search_fields = ("payout_uuid", "user__email", "reference_id")
