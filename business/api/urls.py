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
    AdminBusinessProfileRankUpdateAPIView,
    AdminBusinessProfileUpdateAPIView,
    ProviderAvailabilityCreateAPIView,
    ProviderAvailabilityUpdateAPIView,
    ProviderAvailabilityListAPIView,
    EmployeeWorkingScheduleDeleteAPIView,
    EmployeeWorkingScheduleUpdateAPIView,
    EmployeeWorkingScheduleListAPIView,
    EmployeeWorkingScheduleCreateAPIView,
    EmployeeWorkingScheduleApplyToDaysAPIView,
    BusinessApplicationPendingListAPIView,
    BusinessApplicationAcceptedListAPIView,
    BusinessApplicationRejectedListAPIView,
    BusinessApplicationDocumentsAPIView,
    BusinessApplicationDocumentViewAPIView,
    BusinessUpgradeRequestCreateAPIView,
    AdminRejectBusinessUpgradeRequestAPIView, 
    BusinessUpgradeRequestListAPIView,
    BusinessUpgradeRequestDocumentsAPIView,
    BusinessUpgradeRequestDocumentViewAPIView,
    AdminApproveBusinessUpgradeRequestAPIView,
    AdminBusinessUpgradeRequestListAPIView,
    PublicBusinessProfileListAPIView,
    BusinessPortfolioCreateAPIView,
    BusinessPortfolioPublicRetrieveAPIView,
    BusinessPortfolioUpdateAPIView,
    BusinessPortfolioGalleryImageDeleteAPIView,
    BusinessPortfolioFAQDeleteAPIView,
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


    path(
        "applications/<uuid:business_application_uuid>/documents/",
        BusinessApplicationDocumentsAPIView.as_view(),
        name="business-application-documents",
    ),

    path(
        "applications/<uuid:business_application_uuid>/documents/<str:document_key>/view/",
        BusinessApplicationDocumentViewAPIView.as_view(),
        name="business-application-document-view",
    ),

    path(
        "upgrade-requests/list/",
        BusinessUpgradeRequestListAPIView.as_view(),
        name="business-upgrade-request-list",
    ),

    path(
        "upgrade-requests/<uuid:business_upgrade_request_uuid>/documents/",
        BusinessUpgradeRequestDocumentsAPIView.as_view(),
        name="business-upgrade-request-documents",
    ),

    path(
        "upgrade-requests/<uuid:business_upgrade_request_uuid>/documents/<str:document_key>/view/",
        BusinessUpgradeRequestDocumentViewAPIView.as_view(),
        name="business-upgrade-request-document-view",
    ),

    # =====================================================
    # ADMIN - BUSINESS UPGRADE REQUEST

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

    path(
        "admin/applications/accepted/",
        BusinessApplicationAcceptedListAPIView.as_view(),
        name="admin-business-application-accepted-list",
    ),

    path(
        "admin/applications/rejected/",
        BusinessApplicationRejectedListAPIView.as_view(),
        name="admin-business-application-rejected-list",
    ),

    path(
        "admin/applications/pending/",
        BusinessApplicationPendingListAPIView.as_view(),
        name="admin-business-application-pending-list",
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
        "admin/profiles/<uuid:business_profile_uuid>/rank/",
        AdminBusinessProfileRankUpdateAPIView.as_view(),
        name="admin-business-profile-rank-update",
    ),

    path(
        "admin/profiles/<uuid:business_profile_uuid>/update/",
        AdminBusinessProfileUpdateAPIView.as_view(),
        name="admin-business-profile-update",
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
        "profiles/public/<subCat_uuid>/s",
        PublicBusinessProfileListAPIView.as_view(),
        name="public-business-profile-list",
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
        "working-schedules/apply-to-days/",
        EmployeeWorkingScheduleApplyToDaysAPIView.as_view(),
        name="working-schedule-apply-to-days",
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

    # =====================================================
    # USER - BUSINESS UPGRADE REQUEST
    # =====================================================

    path(
        "upgrade-requests/",
        BusinessUpgradeRequestCreateAPIView.as_view(),
        name="business-upgrade-request-create",
    ),

    path(
        "upgrade-requests/list/",
        BusinessUpgradeRequestListAPIView.as_view(),
        name="business-upgrade-request-list",
    ),

    # =====================================================
    # ADMIN - BUSINESS UPGRADE REQUEST
    # =====================================================

    path(
        "admin/upgrade-requests/",
        AdminBusinessUpgradeRequestListAPIView.as_view(),
        name="admin-business-upgrade-request-list",
    ),

    path(
        "admin/upgrade-requests/<uuid:business_upgrade_request_uuid>/approve/",
        AdminApproveBusinessUpgradeRequestAPIView.as_view(),
        name="admin-business-upgrade-request-approve",
    ),

    path(
        "admin/upgrade-requests/<uuid:business_upgrade_request_uuid>/reject/",
        AdminRejectBusinessUpgradeRequestAPIView.as_view(),
        name="admin-business-upgrade-request-reject",
    ),

    # =====================================================
    # BUSINESS PORTFOLIO
    # =====================================================

    path(
        "portfolio/create/",
        BusinessPortfolioCreateAPIView.as_view(),
        name="business-portfolio-create",
    ),

    path(
        "portfolio/update/",
        BusinessPortfolioUpdateAPIView.as_view(),
        name="business-portfolio-update",
    ),

    path(
        "portfolio/<uuid:business_profile_uuid>/",
        BusinessPortfolioPublicRetrieveAPIView.as_view(),
        name="business-portfolio-public-detail",
    ),

    path(
        "portfolio/gallery/<uuid:gallery_image_uuid>/delete/",
        BusinessPortfolioGalleryImageDeleteAPIView.as_view(),
        name="business-portfolio-gallery-image-delete",
    ),

    path(
        "portfolio/faqs/<uuid:faq_uuid>/delete/",
        BusinessPortfolioFAQDeleteAPIView.as_view(),
        name="business-portfolio-faq-delete",
    ),

]

