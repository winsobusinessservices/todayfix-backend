from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fix_coins.api.serializers import (
    FixCoinBalanceResponseSerializer,
    FixCoinRedeemPreviewRequestSerializer,
    FixCoinRedeemPreviewResponseSerializer,
    FixCoinTransactionSerializer,
)
from fix_coins.models import FixCoinTransaction
from fix_coins.services import (
    calculate_rupee_value,
    get_fix_coin_settings,
    get_or_create_wallet,
    validate_redemption,
)


class FixCoinPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class FixCoinBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Fix-Coins"],
        summary="Get Fix-Coins Balance",
        description="Retrieves the authenticated user's Fix-Coins wallet details and monetary rupee valuation.",
        responses={
            200: OpenApiResponse(
                response=FixCoinBalanceResponseSerializer,
                description="Fix-Coins balance retrieved successfully.",
                examples=[
                    OpenApiExample(
                        "Success Example",
                        value={
                            "success": True,
                            "message": "Fix-Coins balance retrieved successfully.",
                            "data": {
                                "wallet_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "available_coins": 1250,
                                "coin_value_rupees": "125.00",
                                "lifetime_earned_coins": 1750,
                                "lifetime_redeemed_coins": 500,
                                "lifetime_expired_coins": 0,
                                "coins_per_rupee": 10,
                            },
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        settings_obj = get_fix_coin_settings()
        rupee_value = calculate_rupee_value(wallet.available_coins, settings_obj.coins_per_rupee)

        data = {
            "wallet_uuid": wallet.wallet_uuid,
            "available_coins": wallet.available_coins,
            "coin_value_rupees": f"{rupee_value:.2f}",
            "lifetime_earned_coins": wallet.lifetime_earned_coins,
            "lifetime_redeemed_coins": wallet.lifetime_redeemed_coins,
            "lifetime_expired_coins": wallet.lifetime_expired_coins,
            "coins_per_rupee": settings_obj.coins_per_rupee,
        }

        return Response(
            {
                "success": True,
                "message": "Fix-Coins balance retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class FixCoinHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Fix-Coins"],
        summary="Get Fix-Coins History",
        description="Retrieves the paginated audit ledger of all Fix-Coin transactions for the authenticated user.",
        responses={
            200: OpenApiResponse(
                response=FixCoinTransactionSerializer(many=True),
                description="Fix-Coins transaction history retrieved successfully.",
                examples=[
                    OpenApiExample(
                        "History Example",
                        value={
                            "count": 1,
                            "next": None,
                            "previous": None,
                            "results": [
                                {
                                    "transaction_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                    "transaction_type": "SIGNUP_BONUS",
                                    "coins": 500,
                                    "balance_before": 0,
                                    "balance_after": 500,
                                    "description": "Welcome bonus",
                                    "reference_type": "SIGNUP",
                                    "reference_id": None,
                                    "expires_at": "2027-03-15T10:00:00+05:30",
                                    "created_at": "2026-09-15T10:00:00+05:30",
                                }
                            ],
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        transactions = FixCoinTransaction.objects.filter(wallet=wallet).order_by("-created_at")

        paginator = FixCoinPagination()
        page = paginator.paginate_queryset(transactions, request)
        serializer = FixCoinTransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class FixCoinRedeemPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Fix-Coins"],
        summary="Preview Fix-Coins Redemption",
        description=(
            "Validates and previews a proposed Fix-Coin redemption on an eligible booking amount. "
            "Does NOT deduct coins or alter wallet state."
        ),
        request=FixCoinRedeemPreviewRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=FixCoinRedeemPreviewResponseSerializer,
                description="Fix-Coins redemption preview calculated successfully.",
                examples=[
                    OpenApiExample(
                        "Successful Preview",
                        value={
                            "success": True,
                            "message": "Fix-Coins redemption preview calculated successfully.",
                            "data": {
                                "eligible_amount": "1000.00",
                                "requested_coins": 1000,
                                "approved_coins": 1000,
                                "discount_amount": "100.00",
                                "remaining_coins": 250,
                                "maximum_redeemable_coins": 1500,
                                "coins_per_rupee": 10,
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error (insufficient balance, exceeds limit, below minimum, or invalid amount).",
                examples=[
                    OpenApiExample(
                        "Exceeds Maximum Limit",
                        value={
                            "success": False,
                            "message": "Requested Fix-Coins exceed the maximum redemption limit.",
                            "errors": {
                                "coins_to_redeem": [
                                    "Maximum redeemable amount for this booking is 1500 Fix-Coins."
                                ]
                            },
                        },
                    ),
                    OpenApiExample(
                        "Insufficient Coins",
                        value={
                            "success": False,
                            "message": "Insufficient Fix-Coins.",
                            "errors": {
                                "coins_to_redeem": [
                                    "You have 500 Fix-Coins available, but requested 1000."
                                ]
                            },
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def post(self, request):
        serializer = FixCoinRedeemPreviewRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Invalid input provided.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        eligible_amount = serializer.validated_data["eligible_amount"]
        coins_to_redeem = serializer.validated_data["coins_to_redeem"]

        try:
            preview_data = validate_redemption(
                user=request.user,
                eligible_amount=eligible_amount,
                coins_to_redeem=coins_to_redeem,
            )
        except DjangoValidationError as exc:
            err_dict = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            # Custom message phrasing per requirement
            msg = "Validation error."
            coins_err = err_dict.get("coins_to_redeem", [])
            coins_str = " ".join(coins_err) if isinstance(coins_err, list) else str(coins_err)
            if "Insufficient Fix-Coins" in coins_str:
                msg = "Insufficient Fix-Coins."
            elif "Maximum redeemable amount" in coins_str:
                msg = "Requested Fix-Coins exceed the maximum redemption limit."
            elif "Minimum redemption" in coins_str:
                msg = "Requested Fix-Coins are below the minimum redemption limit."
            elif "eligible_amount" in err_dict:
                msg = "Invalid eligible amount."

            return Response(
                {
                    "success": False,
                    "message": msg,
                    "errors": err_dict,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "Fix-Coins redemption preview calculated successfully.",
                "data": preview_data,
            },
            status=status.HTTP_200_OK,
        )
