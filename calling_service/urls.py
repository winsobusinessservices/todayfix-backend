from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CallSessionViewSet

router = DefaultRouter()
router.register(r'calls', CallSessionViewSet, basename='callsession')

urlpatterns = [
    path('', include(router.urls)),
]
