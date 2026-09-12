from django.urls import path

from .views import (
    BusinessInstantBookingOfferAcceptAPIView,
    BusinessInstantBookingOffersAPIView,
    BusinessInstantBookingCompleteAPIView,
    BusinessInstantBookingStartAPIView,
    CustomerInstantBookingCancelAPIView,
    CustomerInstantBookingDetailAPIView,
    InstantBookingCreateAPIView,
    InstantServiceSearchAPIView,
    CustomerInstantBookingRetryAPIView
)
from .views import (
    BusinessInstantBookingAcceptedListAPIView,
    BusinessInstantBookingOfferAcceptAPIView,
    BusinessInstantBookingOffersAPIView,
    BusinessInstantBookingCompleteAPIView,
    BusinessInstantBookingStartAPIView,
    CustomerInstantBookingCancelAPIView,
    CustomerInstantBookingDetailAPIView,
    InstantBookingCreateAPIView,
    InstantServiceSearchAPIView,
    CustomerInstantBookingRetryAPIView
)

urlpatterns = [
    # Customer searches available services.
    path(
        "services/",
        InstantServiceSearchAPIView.as_view(),
        name="instant-service-search",
    ),

    # Customer creates an instant-booking request.
    path(
        "",
        InstantBookingCreateAPIView.as_view(),
        name="instant-booking-create",
    ),

    # Customer views one booking.
    path(
        "<uuid:instant_booking_uuid>/",
        CustomerInstantBookingDetailAPIView.as_view(),
        name="instant-booking-detail",
    ),

    # Customer views provider offers for a booking.
    

    # Customer cancels a booking.
    path(
        "<uuid:instant_booking_uuid>/cancel/",
        CustomerInstantBookingCancelAPIView.as_view(),
        name="customer-instant-booking-cancel",
    ),

   # Provider/business views their pending pop-ups.
    path(
        "provider/popups/",
        BusinessInstantBookingOffersAPIView.as_view(),
        name="business-instant-booking-popups",
    ),

    # Provider/business views bookings they have accepted (ASSIGNED /
    # IN_PROGRESS), so instant_booking_uuid can be recovered after
    # a logout to start/complete the service.
    path(
        "provider/accepted/",
        BusinessInstantBookingAcceptedListAPIView.as_view(),
        name="business-instant-booking-accepted-list",
    ),
    path(
        "provider/popups/<int:popup_id>/accept/",
        BusinessInstantBookingOfferAcceptAPIView.as_view(),
        name="business-instant-booking-popup-accept",
    ),

    # Assigned provider starts the service.
    path(
        "<uuid:instant_booking_uuid>/start/",
        BusinessInstantBookingStartAPIView.as_view(),
        name="business-instant-booking-start",
    ),

    # Assigned provider completes the service.
    path(
        "<uuid:instant_booking_uuid>/complete/",
        BusinessInstantBookingCompleteAPIView.as_view(),
        name="business-instant-booking-complete",
    ),

    path(
        "<uuid:instant_booking_uuid>/retry/",
        CustomerInstantBookingRetryAPIView.as_view(),
        name="customer-instant-booking-retry",
    ),
]