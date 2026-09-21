from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from .models import Invoice
from .serializers import InvoiceSerializer

@extend_schema(tags=["Invoices"])
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing customer invoices.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "invoice_uuid"

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Invoice.objects.all()
        # Fetching by customer_email is a bit loose, better to check through billing_record
        return Invoice.objects.filter(billing_record__booking__user=user) | \
               Invoice.objects.filter(billing_record__instant_booking__customer=user)

    @extend_schema(
        tags=["Invoices"],
        responses={200: bytes}
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download_pdf(self, request, invoice_uuid=None):
        invoice = self.get_object()
        
        # In a real app, you would generate or fetch a PDF from S3 here.
        # For now, return a dummy text response.
        content = f"INVOICE\n\nNumber: {invoice.invoice_number}\nAmount: {invoice.total_amount} {invoice.currency}\n"
        
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="Invoice_{invoice.invoice_number}.txt"'
        return response
