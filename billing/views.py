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
    BillingDraftCreateRequestSerializer,
    BillingAdjustmentRequestSerializer,
)
from .services import BillingService
from .choices import BillingStatus

BUSINESS_OWNER_ONLY_FIELDS = {"extended_service_amount", "material_amount"}
CUSTOMER_ONLY_FIELDS = {"tip_amount", "fix_coins_to_redeem"}


def _get_field_authorization_error(request, raw_data, booking=None, instant_booking=None):
    """
    extended_service_amount / material_amount may only be set by the
    business owner (or admin).
    tip_amount / fix_coins_to_redeem may only be set by the customer
    (or admin).
    Checks the raw request payload (not validated_data, since default
    values would otherwise always appear "present").
    Returns a 403 Response if the caller sent a field they are not
    allowed to set, else None.
    """
    user = request.user
    if user.role == "ADMIN":
        return None

    is_customer = False
    is_business_owner = False
    if booking:
        is_customer = booking.user == user
        is_business_owner = getattr(booking.business, "owner", None) == user
    elif instant_booking:
        is_customer = instant_booking.customer == user
        is_business_owner = getattr(instant_booking.assigned_business, "owner", None) == user

    if not is_business_owner:
        sent = BUSINESS_OWNER_ONLY_FIELDS & set(raw_data.keys())
        if sent:
            return Response(
                {"detail": f"Only the business owner can set: {', '.join(sorted(sent))}."},
                status=status.HTTP_403_FORBIDDEN,
            )

    if not is_customer:
        sent = CUSTOMER_ONLY_FIELDS & set(raw_data.keys())
        if sent:
            return Response(
                {"detail": f"Only the customer can set: {', '.join(sorted(sent))}."},
                status=status.HTTP_403_FORBIDDEN,
            )

    return None

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
        # Ensure customers only see their own, and business owners see their jobs
        return BillingRecord.objects.filter(
            models.Q(booking__user=user) | 
            models.Q(instant_booking__customer=user) |
            models.Q(booking__business__owner=user) |
            models.Q(instant_booking__assigned_business__owner=user)
        ).distinct()

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
            # Ensure user is the customer, the business owner, or admin
            is_customer = booking.user == request.user
            is_business_owner = getattr(booking.business, "owner", None) == request.user
            if not is_customer and not is_business_owner and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

            auth_error = _get_field_authorization_error(request, request.data, booking=booking)
            if auth_error:
                return auth_error

            try:
                BillingService.validate_billable_booking(booking=booking)
                calc_result = BillingService.calculate_from_booking(booking, **data)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            instant_booking = get_object_or_404(InstantBooking, instant_booking_uuid=instant_uuid)
            is_customer = instant_booking.customer == request.user
            is_business_owner = getattr(instant_booking.assigned_business, "owner", None) == request.user
            if not is_customer and not is_business_owner and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

            auth_error = _get_field_authorization_error(request, request.data, instant_booking=instant_booking)
            if auth_error:
                return auth_error

            try:
                BillingService.validate_billable_booking(instant_booking=instant_booking)
                calc_result = BillingService.calculate_from_instant_booking(instant_booking, **data)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
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
        request=BillingDraftCreateRequestSerializer,
        responses={201: BillingRecordSerializer}
    )
    @action(detail=False, methods=["post"])
    def create_draft(self, request):
        """
        Business-owner-only. Creates (or updates) the initial DRAFT with
        the business's own charges. Tip and FixCoins redemption are not
        accepted here - the customer adds those later via adjust, after
        this draft has been confirmed.
        """
        serializer = BillingDraftCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        booking_uuid = data.get("booking_uuid")
        instant_uuid = data.get("instant_booking_uuid")

        booking = None
        instant_booking = None

        if booking_uuid:
            booking = get_object_or_404(Booking, uuid=booking_uuid)
            is_business_owner = getattr(booking.business, "owner", None) == request.user
            if not is_business_owner and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            instant_booking = get_object_or_404(InstantBooking, instant_booking_uuid=instant_uuid)
            is_business_owner = getattr(instant_booking.assigned_business, "owner", None) == request.user
            if not is_business_owner and request.user.role != "ADMIN":
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fields the caller actually sent in this request (not defaults
        # filled in by the serializer). Only these are allowed to override
        # an existing DRAFT's stored values for that field.
        explicit_fields = set(request.data.keys()) & {"extended_service_amount", "material_amount"}

        try:
            record = BillingService.create_billing_record(
                booking=booking,
                instant_booking=instant_booking,
                explicit_fields=explicit_fields,
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
        """
        Business-owner-only. Locks in the draft (extended_service_amount
        + material_amount) as final, ready for the customer to adjust
        with tip/FixCoins.
        """
        record = self.get_object()

        user = request.user
        if user.role != "ADMIN":
            is_business_owner = False
            if record.booking:
                is_business_owner = bool(getattr(record.booking, "business", None)) and record.booking.business.owner == user
            elif record.instant_booking:
                is_business_owner = bool(getattr(record.instant_booking, "assigned_business", None)) and record.instant_booking.assigned_business.owner == user

            if not is_business_owner:
                return Response({"detail": "Only the business owner can confirm billing."}, status=status.HTTP_403_FORBIDDEN)

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

    @extend_schema(
        tags=["Billing"],
        request=BillingAdjustmentRequestSerializer,
        responses={201: BillingRecordSerializer}
    )
    @action(detail=True, methods=["post"])
    def adjust(self, request, billing_uuid=None):
        """
        Customer-only. Adds a tip and/or redeems FixCoins on top of an
        already-confirmed (FINALIZED) bill. Auto-finalizes the resulting
        version immediately - this is the last step before payment.
        """
        from django.db import transaction

        serializer = BillingAdjustmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = self.get_object()

        user = request.user
        if user.role != "ADMIN":
            is_customer = False
            if record.booking:
                is_customer = record.booking.user == user
            elif record.instant_booking:
                is_customer = record.instant_booking.customer == user

            if not is_customer:
                return Response({"detail": "Only the customer can adjust billing."}, status=status.HTTP_403_FORBIDDEN)

        try:
            with transaction.atomic():
                locked_record = BillingRecord.objects.select_for_update().get(pk=record.pk)
                adjusted = BillingService.adjust_billing(locked_record, user=request.user, **serializer.validated_data)
                return Response(BillingRecordSerializer(adjusted).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
