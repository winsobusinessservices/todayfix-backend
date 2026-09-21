from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.exceptions import ValidationError as ApplicationError
from billing.models import BillingRecord
from .models import PaymentOrder, PaymentTransaction
from .serializers import (
    PaymentOrderSerializer,
    PaymentTransactionSerializer,
    CreatePaymentRequestSerializer,
    VerifyPaymentRequestSerializer
)
from .services import PaymentService, RazorpayClient

@extend_schema(tags=["Payments"])
class PaymentOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing payment orders.
    """
    serializer_class = PaymentOrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_uuid"

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return PaymentOrder.objects.all()
        return PaymentOrder.objects.filter(customer=user)

    @extend_schema(
        tags=["Payments"],
        request=CreatePaymentRequestSerializer,
        responses={201: PaymentOrderSerializer}
    )
    @action(detail=False, methods=["post"])
    def create_order(self, request):
        serializer = CreatePaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        billing_uuid = serializer.validated_data["billing_uuid"]
        billing_record = get_object_or_404(BillingRecord, billing_uuid=billing_uuid)
        
        # Verify ownership
        booking = billing_record.booking
        instant = billing_record.instant_booking
        owner = booking.user if booking else instant.customer
        
        if owner != request.user and request.user.role != "ADMIN":
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            order = PaymentService.create_payment_order(billing_record, request.user)
            return Response(PaymentOrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ApplicationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Gateway error: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

    @extend_schema(
        tags=["Payments"],
        request=VerifyPaymentRequestSerializer,
        responses={200: PaymentOrderSerializer}
    )
    @action(detail=False, methods=["post"])
    def verify(self, request):
        serializer = VerifyPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            order = PaymentService.process_successful_payment(
                razorpay_order_id=data["razorpay_order_id"],
                razorpay_payment_id=data["razorpay_payment_id"],
                razorpay_signature=data["razorpay_signature"]
            )
            return Response(PaymentOrderSerializer(order).data)
        except ApplicationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(views.APIView):
    """
    Webhook endpoint for Razorpay server-to-server events.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(tags=["Webhooks"], exclude=True)
    def post(self, request, *args, **kwargs):
        webhook_body = request.body.decode('utf-8')
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        # Verify Webhook Signature (requires setting RAZORPAY_WEBHOOK_SECRET)
        # client = RazorpayClient.get_client()
        # secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        # try:
        #     client.utility.verify_webhook_signature(webhook_body, webhook_signature, secret)
        # except Exception:
        #     return Response(status=status.HTTP_400_BAD_REQUEST)
        
        payload = request.data
        event = payload.get("event")
        
        if event == "payment.captured":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            
            if order_id and payment_id:
                try:
                    PaymentService.process_successful_payment(
                        razorpay_order_id=order_id,
                        razorpay_payment_id=payment_id,
                        webhook_payload=payload
                    )
                except Exception:
                    # Log error but return 200 to acknowledge webhook
                    pass
                    
        elif event == "payment.failed":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            error_code = payment_entity.get("error_code", "")
            error_desc = payment_entity.get("error_description", "")
            
            if order_id and payment_id:
                try:
                    PaymentService.process_failed_payment(
                        razorpay_order_id=order_id,
                        razorpay_payment_id=payment_id,
                        error_code=error_code,
                        error_desc=error_desc,
                        webhook_payload=payload
                    )
                except Exception:
                    pass
                    
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
