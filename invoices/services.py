from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as ApplicationError
from billing.models import BillingRecord
from billing.choices import BillingStatus
from .models import Invoice, InvoiceLineItem, InvoiceStatus

class InvoiceService:
    @staticmethod
    def _generate_invoice_number() -> str:
        """
        Generates a unique, sequential invoice number.
        In a real production app, use a sequence or redis counter to guarantee no gaps.
        """
        count = Invoice.objects.count() + 1
        year = timezone.now().year
        return f"TF-{year}-{count:06d}"

    @staticmethod
    @transaction.atomic
    def generate_invoice_for_billing(billing_record: BillingRecord) -> Invoice:
        """
        Generates a legal Invoice based on a PAID BillingRecord.
        """
        if billing_record.status != BillingStatus.PAID:
            raise ApplicationError("Invoices can only be generated for PAID billing records.")
            
        if hasattr(billing_record, 'invoice'):
            return billing_record.invoice
            
        customer = billing_record.booking.user if billing_record.booking else billing_record.instant_booking.customer
        customer_name = customer.get_full_name() or customer.email
        
        invoice = Invoice.objects.create(
            billing_record=billing_record,
            invoice_number=InvoiceService._generate_invoice_number(),
            status=InvoiceStatus.ISSUED,
            customer_name=customer_name,
            customer_email=customer.email,
            subtotal=billing_record.subtotal,
            tax_total=billing_record.tax_total,
            discount_total=billing_record.discount_total,
            total_amount=billing_record.payable_amount,
            currency=billing_record.currency
        )
        
        # Copy line items
        for item in billing_record.items.all():
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.amount,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount,
                total=item.total
            )
            
        # At this point, we could also trigger an async task to generate the PDF and upload to S3
        
        return invoice
