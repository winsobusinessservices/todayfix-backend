from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from bookings.models import Booking
from bookings.permissions import (
    IsBookingUser,
    IsBookingBusiness,
)
from bookings.services import BookingService
from .serializers import (
    BookingReadSerializer,
    BookingCreateSerializer,
)


# =============================================================
# USER BOOKING VIEWS
# =============================================================

@extend_schema(
    tags=["Bookings"],
    summary="Create Booking",
    description="Create a new booking as a user.",
    request=BookingCreateSerializer,
    responses={201: BookingReadSerializer},
)
class UserBookingCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            booking = BookingService.create_booking(
                user=request.user,
                **serializer.validated_data
            )
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = BookingReadSerializer(booking)

        return Response(
            {
                "success": True,
                "message": "Booking created successfully.",
                "data": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Bookings"],
    summary="List My Bookings",
    description="List all bookings for the authenticated user.",
    responses={200: BookingReadSerializer(many=True)},
)
class UserBookingListAPIView(ListAPIView):
    serializer_class = BookingReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(
            user=self.request.user
        ).select_related(
            "user", "business", "service", "address"
        )


@extend_schema(
    tags=["Bookings"],
    summary="My Booking Detail",
    description="Get details of a specific user booking.",
    responses={200: BookingReadSerializer},
)
class UserBookingDetailAPIView(RetrieveAPIView):
    serializer_class = BookingReadSerializer
    permission_classes = [IsAuthenticated, IsBookingUser]
    lookup_field = "uuid"

    def get_queryset(self):
        return Booking.objects.filter(
            user=self.request.user
        ).select_related(
            "user", "business", "service", "address"
        )


@extend_schema(
    tags=["Bookings"],
    summary="Cancel Booking",
    description="Cancel a pending or confirmed booking.",
    responses={200: BookingReadSerializer},
)
class UserBookingCancelAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBookingUser]

    def get_object(self):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(
            Booking, uuid=self.kwargs["uuid"]
        )
        self.check_object_permissions(self.request, obj)
        return obj

    def post(self, request, uuid):
        booking = self.get_object()
        try:
            booking = BookingService.cancel_booking(booking)
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = BookingReadSerializer(booking)
        return Response(
            {
                "success": True,
                "message": "Booking cancelled successfully.",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================
# BUSINESS BOOKING VIEWS
# =============================================================

@extend_schema(
    tags=["Bookings"],
    summary="List Business Bookings",
    description="List all bookings for the authenticated user's business.",
    responses={200: BookingReadSerializer(many=True)},
)
class BusinessBookingListAPIView(ListAPIView):
    serializer_class = BookingReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(
            business__owner=self.request.user
        ).select_related(
            "user", "business", "service", "address"
        )


@extend_schema(
    tags=["Bookings"],
    summary="Business Booking Detail",
    description="Get details of a specific business booking.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingDetailAPIView(RetrieveAPIView):
    serializer_class = BookingReadSerializer
    permission_classes = [IsAuthenticated, IsBookingBusiness]
    lookup_field = "uuid"

    def get_queryset(self):
        return Booking.objects.filter(
            business__owner=self.request.user
        ).select_related(
            "user", "business", "service", "address"
        )


class BaseBusinessTransitionAPIView(APIView):
    """Base view for business booking transitions."""
    permission_classes = [IsAuthenticated, IsBookingBusiness]

    def get_object(self):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(
            Booking, uuid=self.kwargs["uuid"]
        )
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_transition(self, booking):
        raise NotImplementedError

    def post(self, request, uuid):
        booking = self.get_object()
        try:
            booking = self.perform_transition(booking)
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = BookingReadSerializer(booking)
        return Response(
            {
                "success": True,
                "message": "Booking updated successfully.",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Bookings"],
    summary="Accept Booking",
    description="Business accepts a pending booking.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingAcceptAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.accept_booking(booking)


@extend_schema(
    tags=["Bookings"],
    summary="Reject Booking",
    description="Business rejects a pending booking.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingRejectAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.reject_booking(booking)


@extend_schema(
    tags=["Bookings"],
    summary="Start Booking",
    description="Business marks a confirmed booking as in-progress.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingStartAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.start_booking(booking)


@extend_schema(
    tags=["Bookings"],
    summary="Complete Booking",
    description="Business marks an in-progress booking as completed.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingCompleteAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.complete_booking(booking)
