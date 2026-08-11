from django.urls import path

from .views import (
    AdminApproveBusinessApplicationAPIView,
    AdminBusinessApplicationListAPIView,
    AdminRejectBusinessApplicationAPIView,
    BusinessApplicationCreateAPIView,
    BusinessApplicationDetailAPIView,
    BusinessApplicationListAPIView,
    BusinessProfileListAPIView,
    BusinessProfileUpdateAPIView,
)


urlpatterns = [

    # =====================================================
    # USER - BUSINESS APPLICATION
    # =====================================================

    path(
        "applications/",
        BusinessApplicationCreateAPIView.as_view(),
        name="business-application-create",
    ),

    path(
        "applications/list/",
        BusinessApplicationListAPIView.as_view(),
        name="business-application-list",
    ),

    path(
        "applications/<uuid:uuid>/",
        BusinessApplicationDetailAPIView.as_view(),
        name="business-application-detail",
    ),

    # =====================================================
    # ADMIN - BUSINESS APPLICATION
    # =====================================================

    path(
        "admin/applications/",
        AdminBusinessApplicationListAPIView.as_view(),
        name="admin-business-application-list",
    ),

    path(
        "admin/applications/<uuid:uuid>/approve/",
        AdminApproveBusinessApplicationAPIView.as_view(),
        name="admin-business-application-approve",
    ),

    path(
        "admin/applications/<uuid:uuid>/reject/",
        AdminRejectBusinessApplicationAPIView.as_view(),
        name="admin-business-application-reject",
    ),

    # =====================================================
    # BUSINESS PROFILE
    # =====================================================

    path(
        "profiles/",
        BusinessProfileListAPIView.as_view(),
        name="business-profile-list",
    ),

    path(
        "profiles/<uuid:uuid>/",
        BusinessProfileUpdateAPIView.as_view(),
        name="business-profile-update",
    ),
]

