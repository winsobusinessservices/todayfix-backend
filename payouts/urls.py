from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PayoutAccountViewSet, PayoutViewSet

router = DefaultRouter()
router.register(r'accounts', PayoutAccountViewSet, basename='payout-account')
router.register(r'requests', PayoutViewSet, basename='payout')

urlpatterns = [
    path('', include(router.urls)),
]
