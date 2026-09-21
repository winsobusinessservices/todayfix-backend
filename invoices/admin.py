from django.contrib import admin
from .models import Invoice, InvoiceLineItem

class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_uuid", "invoice_number", "customer_name", "total_amount", "currency", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("invoice_uuid", "invoice_number", "customer_email", "customer_name")
    inlines = [InvoiceLineItemInline]
