from django.urls import path

from .views import (
    SubmitBusinessUpgradeAPIView,
    BusinessUpgradeStatusAPIView,
    AdminUpgradeRequestListAPIView,
    AdminApproveUpgradeAPIView,
    AdminRejectUpgradeAPIView,
    BusinessProfileListCreateAPIView,
    ManagedBusinessCreateAPIView,
)

urlpatterns = [
    path("upgrade/", SubmitBusinessUpgradeAPIView.as_view(), name="business-upgrade"),
    path("upgrade/status/", BusinessUpgradeStatusAPIView.as_view(), name="business-upgrade-status"),
    path("profiles/", BusinessProfileListCreateAPIView.as_view(), name="business-profiles"),
    path("management/", ManagedBusinessCreateAPIView.as_view(), name="managed-business-create"),
    path("admin/upgrades/", AdminUpgradeRequestListAPIView.as_view(), name="admin-upgrade-list"),
    path("admin/upgrades/<int:pk>/approve/", AdminApproveUpgradeAPIView.as_view(), name="admin-upgrade-approve"),
    path("admin/upgrades/<int:pk>/reject/", AdminRejectUpgradeAPIView.as_view(), name="admin-upgrade-reject"),
]
