from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from bookings.models import Booking, BookingEmployee
from business.models import Employee
from bookings.permissions import (
    IsBookingUser,
    IsBookingBusiness,
)

from bookings.choices import BookingStatus
from instant_bookings.models import InstantBooking, InstantBookingStatus

from instant_bookings.api.views import expire_booking_if_required

from rest_framework.pagination import PageNumberPagination

from bookings.services import BookingService
from .serializers import (
    BookingReadSerializer,
    BookingCreateSerializer,
    BookingEmployeeAssignSerializer,
    BookingEmployeeReassignSerializer,
    BookingHistorySerializer,
)

from django.shortcuts import get_object_or_404

from services.models import ServiceEmployee

from django.utils.dateparse import parse_date
from business.choices import BusinessType

@extend_schema(
    tags=["Scheduled Bookings"],
    summary="Check Booking Slot Availability",
    description=(
        "Check Morning, Afternoon and Evening availability "
        "for a service on a selected future date."
    ),
    parameters=[
        OpenApiParameter(
            name="service_uuid",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=True,
            description="UUID of the service to check availability for.",
        ),
        OpenApiParameter(
            name="scheduled_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Future date in YYYY-MM-DD format.",
        ),
    ],
    responses={200: dict},
)
class BookingSlotAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        service_uuid = request.query_params.get(
            "service_uuid"
        )

        scheduled_date = request.query_params.get(
            "scheduled_date"
        )

        if not service_uuid:
            return Response(
                {
                    "success": False,
                    "message": "service_uuid is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not scheduled_date:
            return Response(
                {
                    "success": False,
                    "message": "scheduled_date is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed_date = parse_date(scheduled_date)

        if not parsed_date:
            return Response(
                {
                    "success": False,
                    "message": (
                        "scheduled_date must be in YYYY-MM-DD format."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            availability = BookingService.get_slot_availability(
                user=request.user,
                service_uuid=service_uuid,
                scheduled_date=parsed_date,
            )

        except ValueError as e:
            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "Booking slot availability fetched successfully.",
                "data": {
                    "service_uuid": service_uuid,
                    "scheduled_date": scheduled_date,
                    "slots": availability,
                },
            },
            status=status.HTTP_200_OK,
        )


# =============================================================
# USER BOOKING VIEWS
# =============================================================

@extend_schema(
    tags=["Scheduled Bookings"],
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
    tags=["Scheduled Bookings"],
    summary="Assign Employee to Booking",
    request=BookingEmployeeAssignSerializer,
    responses={200: BookingReadSerializer},
)
class BusinessBookingAssignEmployeeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBookingBusiness]

    def post(self, request, uuid):
        booking = get_object_or_404(
            Booking,
            uuid=uuid,
        )

        self.check_object_permissions(request, booking)

        if booking.business.business_type == BusinessType.INDIVIDUAL:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Additional employee assignment is "
                        "not available for individual businesses."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BookingEmployeeAssignSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        employee_uuid = serializer.validated_data["employee_uuid"]

        employee = get_object_or_404(
            Employee,
            employee_uuid=employee_uuid,
        )

        # Employee must belong to the same business
        if employee.business_id != booking.business_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Employee does not belong to this business."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Employee must be assigned to this service
        if not ServiceEmployee.objects.filter(
            service=booking.service,
            employee=employee,
        ).exists():
            return Response(
                {
                    "success": False,
                    "message": (
                        "Employee is not assigned to this service."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Maximum employees = service.required_employees
        current_count = BookingEmployee.objects.filter(
            booking=booking
        ).count()

        if current_count >= booking.service.required_employees:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Maximum required employees already "
                        "assigned to this booking."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate assignment
        if BookingEmployee.objects.filter(
            booking=booking,
            employee=employee,
        ).exists():
            return Response(
                {
                    "success": False,
                    "message": (
                        "Employee is already assigned "
                        "to this booking."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        BookingEmployee.objects.create(
            booking=booking,
            employee=employee,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Employee assigned to booking successfully."
                ),
                "data": BookingReadSerializer(
                    booking
                ).data,
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    tags=["Scheduled Bookings"],
    summary="Reassign Employee for Booking",
    description=(
        "Replace an employee currently assigned to a booking "
        "with another employee from the same business."
    ),
    request=BookingEmployeeReassignSerializer,
    responses={200: BookingReadSerializer},
)
class BusinessBookingReassignEmployeeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBookingBusiness]

    def post(self, request, uuid):
        booking = get_object_or_404(
            Booking,
            uuid=uuid,
        )

        self.check_object_permissions(request, booking)

        if booking.business.business_type == BusinessType.INDIVIDUAL:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Employee reassignment is not "
                        "available for individual businesses."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BookingEmployeeReassignSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        old_employee_uuid = serializer.validated_data[
            "old_employee_uuid"
        ]

        new_employee_uuid = serializer.validated_data[
            "new_employee_uuid"
        ]

        old_employee = get_object_or_404(
            Employee,
            employee_uuid=old_employee_uuid,
        )

        new_employee = get_object_or_404(
            Employee,
            employee_uuid=new_employee_uuid,
        )

        # Both employees must belong to this business
        if (
            old_employee.business_id != booking.business_id
            or new_employee.business_id != booking.business_id
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Employees must belong to the "
                        "same business as the booking."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Old employee must actually be assigned
        assignment = BookingEmployee.objects.filter(
            booking=booking,
            employee=old_employee,
        ).first()

        if not assignment:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The old employee is not assigned "
                        "to this booking."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # New employee must be assigned to the service
        if not ServiceEmployee.objects.filter(
            service=booking.service,
            employee=new_employee,
        ).exists():
            return Response(
                {
                    "success": False,
                    "message": (
                        "New employee is not assigned "
                        "to this service."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent assigning the same employee
        if old_employee == new_employee:
            return Response(
                {
                    "success": False,
                    "message": (
                        "New employee must be different "
                        "from the old employee."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate assignment
        if BookingEmployee.objects.filter(
            booking=booking,
            employee=new_employee,
        ).exists():
            return Response(
                {
                    "success": False,
                    "message": (
                        "New employee is already assigned "
                        "to this booking."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Replace employee
        assignment.employee = new_employee
        assignment.save(
            update_fields=["employee", "updated_at"]
        )

        # Keep the primary booking employee in sync
        if booking.employee_id == old_employee.id:
            booking.employee = new_employee
            booking.save(
                update_fields=["employee", "updated_at"]
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Employee reassigned successfully."
                ),
                "data": BookingReadSerializer(
                    booking
                ).data,
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    tags=["Scheduled Bookings"],
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
    tags=["Booking History"],
    summary="List My Booking History",
    description=(
        "List scheduled and instant bookings for "
        "the authenticated user."
    ),
    parameters=[
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="A page number within the paginated result set.",
        ),
    ],
    responses={200: BookingHistorySerializer(many=True)},
)
class UserBookingHistoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        scheduled_bookings = list(
            Booking.objects.filter(
                status=BookingStatus.PENDING,
            ).select_related(
                "user",
                "business",
                "service",
                "address",
                "employee",
            ).prefetch_related(
                "booking_employees__employee"
            )
        )

        instant_bookings = list(
            InstantBooking.objects.filter(
                customer=request.user
            ).select_related(
                "customer",
                "category",
                "subcategory",
                "address",
                "selected_service",
                "assigned_business",
                "assigned_employee",
            )
        )

        bookings = (
            scheduled_bookings
            + instant_bookings
        )

        bookings.sort(
            key=lambda booking: booking.created_at,
            reverse=True,
        )

        paginator = PageNumberPagination()
        paginator.page_size = 10

        page = paginator.paginate_queryset(
            bookings,
            request,
            view=self,
        )

        serializer = BookingHistorySerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(
            {
                "success": True,
                "message": (
                    "Booking history fetched successfully."
                ),
                "data": serializer.data,
            }
        )

@extend_schema(
    tags=["Booking History"],
    summary="List My Pending Bookings",
    description=(
        "List only pending scheduled and instant bookings "
        "for the authenticated customer."
    ),
    parameters=[
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="A page number within the paginated result set.",
        ),
    ],
    responses={200: BookingHistorySerializer(many=True)},
)
class UserPendingBookingHistoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        # -------------------------------------------------
        # SCHEDULED PENDING BOOKINGS
        # -------------------------------------------------

        scheduled_bookings = list(
            Booking.objects.filter(
                user=request.user,
                status=BookingStatus.PENDING,
            ).select_related(
                "user",
                "business",
                "service",
                "address",
                "employee",
            ).prefetch_related(
                "booking_employees__employee"
            )
        )

        # -------------------------------------------------
        # INSTANT PENDING BOOKINGS
        # -------------------------------------------------

        instant_bookings = list(
            InstantBooking.objects.filter(
                customer=request.user,
                status__in=[
                    InstantBookingStatus.SEARCHING,
                    InstantBookingStatus.TIP_REQUIRED,
                ],
            ).select_related(
                "customer",
                "category",
                "subcategory",
                "address",
                "selected_service",
                "assigned_business",
                "assigned_employee",
            )
        )

        # -------------------------------------------------
        # EXPIRE INSTANT BOOKINGS IF 15-MINUTE DEADLINE
        # HAS PASSED
        # -------------------------------------------------

        active_instant_bookings = []

        for booking in instant_bookings:
            booking = expire_booking_if_required(booking)

            if booking.status in [
                InstantBookingStatus.SEARCHING,
                InstantBookingStatus.TIP_REQUIRED,
            ]:
                active_instant_bookings.append(booking)

        # -------------------------------------------------
        # COMBINE SCHEDULED + INSTANT
        # -------------------------------------------------

        bookings = (
            scheduled_bookings
            + active_instant_bookings
        )

        bookings.sort(
            key=lambda booking: booking.created_at,
            reverse=True,
        )

        # -------------------------------------------------
        # PAGINATION
        # -------------------------------------------------

        paginator = PageNumberPagination()
        paginator.page_size = 10

        page = paginator.paginate_queryset(
            bookings,
            request,
            view=self,
        )

        serializer = BookingHistorySerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(
            {
                "success": True,
                "message": (
                    "Pending bookings fetched successfully."
                ),
                "data": serializer.data,
            }
        )

@extend_schema(
    tags=["Scheduled Bookings"],
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
    tags=["Scheduled Bookings"],
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
    tags=["Scheduled Bookings"],
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
    tags=["Scheduled Bookings"],
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
    tags=["Scheduled Bookings"],
    summary="Accept Booking",
    description="Business accepts a pending booking.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingAcceptAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        updated_booking = BookingService.accept_booking(booking)
        from chat_service.services import ChatService
        ChatService.get_or_create_conversation_for_scheduled_booking(updated_booking)
        return updated_booking


@extend_schema(
    tags=["Scheduled Bookings"],
    summary="Reject Booking",
    description="Business rejects a pending booking.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingRejectAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.reject_booking(booking)


@extend_schema(
    tags=["Scheduled Bookings"],
    summary="Start Booking",
    description="Business marks a confirmed booking as in-progress.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingStartAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.start_booking(booking)


@extend_schema(
    tags=["Scheduled Bookings"],
    summary="Complete Booking",
    description="Business marks an in-progress booking as completed.",
    responses={200: BookingReadSerializer},
)
class BusinessBookingCompleteAPIView(BaseBusinessTransitionAPIView):
    def perform_transition(self, booking):
        return BookingService.complete_booking(booking)
