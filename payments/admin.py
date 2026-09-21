from django.contrib import admin
from .models import PaymentOrder, PaymentTransaction

class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("order_uuid", "customer", "amount", "currency", "razorpay_order_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("order_uuid", "razorpay_order_id", "customer__email")
    inlines = [PaymentTransactionInline]
