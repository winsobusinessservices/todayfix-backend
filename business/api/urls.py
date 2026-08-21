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
    EmployeeCreateAPIView,
    EmployeeListAPIView,
    EmployeeUpdateAPIView,
    EmployeeDeleteAPIView,
    ProviderAvailabilityCreateAPIView,
    ProviderAvailabilityUpdateAPIView,
    ProviderAvailabilityListAPIView,
    EmployeeWorkingScheduleDeleteAPIView,
    EmployeeWorkingScheduleUpdateAPIView,
    EmployeeWorkingScheduleListAPIView,
    EmployeeWorkingScheduleCreateAPIView,
    BusinessApplicationDocumentAPIView,
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
        "applications/<uuid:business_application_uuid>/",
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
        "admin/applications/<uuid:business_application_uuid>/approve/",
        AdminApproveBusinessApplicationAPIView.as_view(),
        name="admin-business-application-approve",
    ),

    path(
        "admin/applications/<uuid:business_application_uuid>/reject/",
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
        "profiles/<uuid:business_profile_uuid>/",
        BusinessProfileUpdateAPIView.as_view(),
        name="business-profile-update",
    ),

    path(
        "employees/create/",
        EmployeeCreateAPIView.as_view(),
        name="employee-create",
    ),

    path(
        "employees/",
        EmployeeListAPIView.as_view(),
        name="employee-list",
    ),

    path(
        "employees/<uuid:employee_uuid>/update/",
        EmployeeUpdateAPIView.as_view(),
        name="employee-update",
    ),

    path(
        "employees/<uuid:employee_uuid>/delete/",
        EmployeeDeleteAPIView.as_view(),
        name="employee-delete",
    ),

    path(
        "applications/<uuid:business_application_uuid>/documents/<str:document_type>/",
        BusinessApplicationDocumentAPIView.as_view(),
        name="business-application-document",
    ),
    # =====================================================
    # PROVIDER AVAILABILITY
    # =====================================================

    path(
        "availability/",
        ProviderAvailabilityListAPIView.as_view(),
        name="provider-availability-list",
    ),

    path(
        "availability/create/",
        ProviderAvailabilityCreateAPIView.as_view(),
        name="provider-availability-create",
    ),

    path(
        "availability/<uuid:provider_availability_uuid>/update/",
        ProviderAvailabilityUpdateAPIView.as_view(),
        name="provider-availability-update",
    ),

    path(
        "working-schedules/",
        EmployeeWorkingScheduleCreateAPIView.as_view(),
        name="working-schedule-create",
    ),

    path(
        "working-schedules/list/",
        EmployeeWorkingScheduleListAPIView.as_view(),
        name="working-schedule-list",
    ),

    path(
        "working-schedules/<uuid:employee_working_schedule_uuid>/",
        EmployeeWorkingScheduleUpdateAPIView.as_view(),
        name="working-schedule-update",
    ),

    path(
        "working-schedules/<uuid:employee_working_schedule_uuid>/delete/",
        EmployeeWorkingScheduleDeleteAPIView.as_view(),
        name="working-schedule-delete",
    ),
]

