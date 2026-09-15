from django.urls import path
from fix_coins.api.views import (
    FixCoinBalanceAPIView,
    FixCoinHistoryAPIView,
    FixCoinRedeemPreviewAPIView,
)

urlpatterns = [
    path("balance/", FixCoinBalanceAPIView.as_view(), name="fix-coins-balance"),
    path("history/", FixCoinHistoryAPIView.as_view(), name="fix-coins-history"),
    path("redeem/preview/", FixCoinRedeemPreviewAPIView.as_view(), name="fix-coins-redeem-preview"),
]
