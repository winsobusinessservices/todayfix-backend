from django.urls import path

from .views import (
    UserBookingCreateAPIView,
    UserBookingListAPIView,
    UserBookingDetailAPIView,
    UserBookingCancelAPIView,
    BusinessBookingListAPIView,
    BusinessBookingDetailAPIView,
    BusinessBookingAcceptAPIView,
    BusinessBookingRejectAPIView,
    BusinessBookingStartAPIView,
    BusinessBookingCompleteAPIView,
    BookingSlotAvailabilityAPIView,
    BusinessBookingAssignEmployeeAPIView,
    BusinessBookingReassignEmployeeAPIView,
)

urlpatterns = [
    # =====================================================
    # USER ENDPOINTS
    # =====================================================
    path(
        "",
        UserBookingListAPIView.as_view(),
        name="user-booking-list"
    ),
    path(
        "create/",
        UserBookingCreateAPIView.as_view(),
        name="user-booking-create"
    ),
    path(
        "<uuid:uuid>/",
        UserBookingDetailAPIView.as_view(),
        name="user-booking-detail"
    ),
    path(
        "<uuid:uuid>/cancel/",
        UserBookingCancelAPIView.as_view(),
        name="user-booking-cancel"
    ),

    # =====================================================
    # BUSINESS ENDPOINTS
    # =====================================================
    path(
        "business/list/",
        BusinessBookingListAPIView.as_view(),
        name="business-booking-list"
    ),
    path(
        "business/<uuid:uuid>/",
        BusinessBookingDetailAPIView.as_view(),
        name="business-booking-detail"
    ),
    path(
        "business/<uuid:uuid>/accept/",
        BusinessBookingAcceptAPIView.as_view(),
        name="business-booking-accept"
    ),
    path(
        "business/<uuid:uuid>/reject/",
        BusinessBookingRejectAPIView.as_view(),
        name="business-booking-reject"
    ),
    path(
        "business/<uuid:uuid>/start/",
        BusinessBookingStartAPIView.as_view(),
        name="business-booking-start"
    ),
    path(
        "business/<uuid:uuid>/complete/",
        BusinessBookingCompleteAPIView.as_view(),
        name="business-booking-complete"
    ),

    path(
        "availability/",
        BookingSlotAvailabilityAPIView.as_view(),
        name="booking-slot-availability",
    ),

    path(
        "business/<uuid:uuid>/assign-employee/",
        BusinessBookingAssignEmployeeAPIView.as_view(),
        name="business-booking-assign-employee",
    ),

    path(
        "business/<uuid:uuid>/reassign-employee/",
        BusinessBookingReassignEmployeeAPIView.as_view(),
        name="business-booking-reassign-employee",
    ),
]
