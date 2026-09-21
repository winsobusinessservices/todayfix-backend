from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from bookings.models import Booking
from instant_bookings.models import InstantBooking
from fix_coins.services import validate_redemption
from common.utils.money import quantize_money
from django.db import models

from .models import BillingRecord
from .serializers import (
    BillingRecordSerializer,
    BillingPreviewRequestSerializer,
    BillingPreviewResponseSerializer,
)
from .services import BillingService
from .choices import BillingStatus

@extend_schema(tags=["Billing"])
class BillingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing billing records.
    """
    serializer_class = BillingRecordSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "billing_uuid"

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return BillingRecord.objects.all()
        # Ensure customers only see their own
        return BillingRecord.objects.filter(
            models.Q(booking__user=user) | models.Q(instant_booking__customer=user)
        )

    @extend_schema(
        tags=["Billing"],
        request=BillingPreviewRequestSerializer,
        responses={200: BillingPreviewResponseSerializer}
    )
    @action(detail=False, methods=["post"])
    def preview(self, request):
        serializer = BillingPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        booking_uuid = data.get("booking_uuid")
        instant_uuid = data.get("instant_booking_uuid")
        
        booking = None
        instant_booking = None
        
        if booking_uuid:
            booking = get_object_or_404(Booking, uuid=booking_uuid)
            # Ensure user owns it or is admin
            if booking.user != request.user and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
                
            calc_result = BillingService.calculate_from_booking(booking, **data)
        else:
            instant_booking = get_object_or_404(InstantBooking, instant_booking_uuid=instant_uuid)
            if instant_booking.customer != request.user and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
                
            calc_result = BillingService.calculate_from_instant_booking(instant_booking, **data)
            
        # If FixCoins redemption is requested, validate it and apply the discount
        coins_to_redeem = data.get("fix_coins_to_redeem", 0)
        fix_coin_discount = quantize_money("0.00")
        
        if coins_to_redeem > 0:
            # We need the eligible amount without the tip to calculate max discount
            # The calculator gives us subtotal + tax = gross_amount
            # This is exactly the eligible amount for FixCoins.
            eligible_amount = calc_result["gross_amount"]
            try:
                redemption_preview = validate_redemption(request.user, eligible_amount, coins_to_redeem)
                fix_coin_discount = quantize_money(redemption_preview["discount_amount"])
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
            # Re-run calculation with fix coin discount
            data["fix_coin_discount"] = fix_coin_discount
            if booking:
                calc_result = BillingService.calculate_from_booking(booking, **data)
            else:
                calc_result = BillingService.calculate_from_instant_booking(instant_booking, **data)
        
        return Response(calc_result)

    @extend_schema(
        tags=["Billing"],
        request=BillingPreviewRequestSerializer,
        responses={201: BillingRecordSerializer}
    )
    @action(detail=False, methods=["post"])
    def create_draft(self, request):
        serializer = BillingPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        booking_uuid = data.get("booking_uuid")
        instant_uuid = data.get("instant_booking_uuid")
        
        booking = None
        instant_booking = None
        
        if booking_uuid:
            booking = get_object_or_404(Booking, uuid=booking_uuid)
            if booking.user != request.user and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            instant_booking = get_object_or_404(InstantBooking, instant_booking_uuid=instant_uuid)
            if instant_booking.customer != request.user and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        coins_to_redeem = data.get("fix_coins_to_redeem", 0)
        if coins_to_redeem > 0:
            # Perform a preview calculation first to get eligible amount
            if booking:
                preview = BillingService.calculate_from_booking(booking, **data)
            else:
                preview = BillingService.calculate_from_instant_booking(instant_booking, **data)
                
            eligible_amount = preview["gross_amount"]
            try:
                redemption_preview = validate_redemption(request.user, eligible_amount, coins_to_redeem)
                data["fix_coin_discount"] = quantize_money(redemption_preview["discount_amount"])
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
        # Create draft record
        try:
            record = BillingService.create_billing_record(
                booking=booking,
                instant_booking=instant_booking,
                **data
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(BillingRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Billing"],
        responses={200: BillingRecordSerializer}
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request, billing_uuid=None):
        record = self.get_object()
        try:
            record = BillingService.finalize_billing(record)
            return Response(BillingRecordSerializer(record).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @extend_schema(
        tags=["Billing"],
        responses={200: BillingRecordSerializer(many=True)}
    )
    @action(detail=True, methods=["get"])
    def history(self, request, billing_uuid=None):
        record = self.get_object()
        # Find all records with same booking/instant_booking
        if record.booking:
            qs = BillingRecord.objects.filter(booking=record.booking).order_by("version")
        else:
            qs = BillingRecord.objects.filter(instant_booking=record.instant_booking).order_by("version")
            
        return Response(BillingRecordSerializer(qs, many=True).data)
