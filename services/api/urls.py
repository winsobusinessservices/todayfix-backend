from django.urls import path

from .views import (
    ServiceListAPIView,
    ServiceDetailAPIView,
    ServiceCreateAPIView,
    ServiceUpdateAPIView,
    ServiceDeleteAPIView,
    ServiceSearchAPIView,
    ServiceEmployeeCreateAPIView,
    ServiceEmployeeListAPIView,
)


urlpatterns = [

    # =====================================================
    # PUBLIC
    # =====================================================

    path(
        "",
        ServiceListAPIView.as_view(),
        name="service-list",
    ),

    path(
        "search/",
        ServiceSearchAPIView.as_view(),
        name="service-search",
    ),

    path(
        "<uuid:service_uuid>/",
        ServiceDetailAPIView.as_view(),
        name="service-detail",
    ),

    # =====================================================
    # BUSINESS OWNER
    # =====================================================

    path(
        "create/",
        ServiceCreateAPIView.as_view(),
        name="service-create",
    ),

    path(
        "<uuid:service_uuid>/update/",
        ServiceUpdateAPIView.as_view(),
        name="service-update",
    ),

    path(
        "<uuid:service_uuid>/delete/",
        ServiceDeleteAPIView.as_view(),
        name="service-delete",
    ),

    path(
        "assign-employee/",
        ServiceEmployeeCreateAPIView.as_view(),
        name="service-employee-create",
    ),

    path(
        "<uuid:service_uuid>/employees/",
        ServiceEmployeeListAPIView.as_view(),
        name="service-employee-list",
    ),
]
