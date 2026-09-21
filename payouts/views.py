from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from rest_framework.exceptions import ValidationError as ApplicationError
from .models import PayoutAccount, Payout
from .serializers import (
    PayoutAccountSerializer,
    PayoutSerializer,
    PayoutRequestSerializer
)
from .services import PayoutService

@extend_schema(tags=["Payouts"])
class PayoutAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing business payout accounts.
    """
    serializer_class = PayoutAccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "account_uuid"

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return PayoutAccount.objects.all()
        return PayoutAccount.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@extend_schema(tags=["Payouts"])
class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and requesting payouts.
    """
    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "payout_uuid"

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Payout.objects.all()
        return Payout.objects.filter(user=user)

    @extend_schema(
        tags=["Payouts"],
        responses={200: dict}
    )
    @action(detail=False, methods=["get"])
    def eligibility(self, request):
        user = request.request.user if hasattr(request, "request") else request.user
        eligible_amount = PayoutService.get_eligible_payout_amount(user)
        can_emergency = PayoutService.check_emergency_eligibility(user)
        
        return Response({
            "eligible_amount": eligible_amount,
            "can_request_emergency": can_emergency
        })

    @extend_schema(
        tags=["Payouts"],
        request=PayoutRequestSerializer,
        responses={201: PayoutSerializer}
    )
    @action(detail=False, methods=["post"])
    def request_weekly(self, request):
        serializer = PayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        account_uuid = data["payout_account_uuid"]
        payout_account = get_object_or_404(PayoutAccount, account_uuid=account_uuid, user=request.user)
        
        try:
            payout = PayoutService.request_payout(
                user=request.user,
                payout_account=payout_account,
                amount=data["amount"],
                is_emergency=False
            )
            return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)
        except ApplicationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Payouts"],
        request=PayoutRequestSerializer,
        responses={201: PayoutSerializer}
    )
    @action(detail=False, methods=["post"], url_path="request-emergency")
    def request_emergency(self, request):
        serializer = PayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        account_uuid = data["payout_account_uuid"]
        payout_account = get_object_or_404(PayoutAccount, account_uuid=account_uuid, user=request.user)
        
        try:
            payout = PayoutService.request_payout(
                user=request.user,
                payout_account=payout_account,
                amount=data["amount"],
                is_emergency=True
            )
            return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)
        except ApplicationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
