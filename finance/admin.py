from django.contrib import admin
from .models import FinancialAuditLog, FinanceAccount, LedgerEntry

@admin.register(FinancialAuditLog)
class FinancialAuditLogAdmin(admin.ModelAdmin):
    list_display = ("audit_uuid", "actor", "action", "object_type", "object_id", "created_at")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "audit_uuid", "actor__email")

class LedgerEntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0

@admin.register(FinanceAccount)
class FinanceAccountAdmin(admin.ModelAdmin):
    list_display = ("account_uuid", "account_type", "user", "currency", "pending_balance", "available_balance")
    list_filter = ("account_type", "currency")
    search_fields = ("account_uuid", "user__email")
    inlines = [LedgerEntryInline]
