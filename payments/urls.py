from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentOrderViewSet, RazorpayWebhookView

router = DefaultRouter()
router.register(r'orders', PaymentOrderViewSet, basename='payment-order')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]
