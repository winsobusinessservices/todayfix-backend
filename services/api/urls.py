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
    ServiceTypeListCreateAPIView,
    ServiceTypeDetailAPIView,
    UnitListCreateAPIView,
    UnitDetailAPIView,
    MyServicesAPIView,
    ServiceEmployeeDeleteAPIView,
    SubCategoryServiceListAPIView
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

    # =====================================================
    # SERVICE TYPES & UNITS (ADMIN manage, ADMIN+BUSINESS view)
    # =====================================================

    path(
        "types/",
        ServiceTypeListCreateAPIView.as_view(),
        name="service-type-list-create",
    ),

    path(
        "types/<uuid:type_uuid>/",
        ServiceTypeDetailAPIView.as_view(),
        name="service-type-detail",
    ),

    path(
        "subcategory/<uuid:subCat_uuid>/services/",
        SubCategoryServiceListAPIView.as_view(),
        name="subcategory-services",
    ),

    path(
        "my/",
        MyServicesAPIView.as_view(),
        name="my-services",
    ),

    path(
        "types/<uuid:type_uuid>/units/",
        UnitListCreateAPIView.as_view(),
        name="unit-list-create",
    ),

    path(
        "types/units/<uuid:unit_uuid>/",
        UnitDetailAPIView.as_view(),
        name="unit-detail",
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
        "<uuid:service_uuid>/employees/<uuid:employee_uuid>/remove/",
        ServiceEmployeeDeleteAPIView.as_view(),
        name="service-employee-delete",
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