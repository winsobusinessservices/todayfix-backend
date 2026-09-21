from django.contrib import admin
from .models import ReconciliationReport

@admin.register(ReconciliationReport)
class ReconciliationReportAdmin(admin.ModelAdmin):
    list_display = ("report_uuid", "report_date", "total_expected_amount", "total_settled_amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("report_uuid",)
