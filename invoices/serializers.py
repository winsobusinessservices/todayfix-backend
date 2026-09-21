from rest_framework import serializers
from .models import Invoice, InvoiceLineItem

class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = [
            "id",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "tax_amount",
            "total"
        ]
        read_only_fields = fields

class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            "invoice_uuid",
            "billing_record",
            "invoice_number",
            "status",
            "company_name",
            "company_address",
            "company_gstin",
            "customer_name",
            "customer_email",
            "customer_address",
            "subtotal",
            "tax_total",
            "discount_total",
            "total_amount",
            "currency",
            "pdf_url",
            "created_at",
            "line_items"
        ]
        read_only_fields = fields
