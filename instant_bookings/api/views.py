from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from instant_bookings.api.serializers import (
    InstantBookingCreateSerializer,
    InstantBookingOfferReadSerializer,
    InstantBookingReadSerializer,
    InstantBookingRetrySerializer,
    InstantServiceSearchResultSerializer,
)

from instant_bookings.models import (
    InstantBooking,
    InstantBookingOffer,
    InstantBookingOfferStatus,
    InstantBookingStatus,
)

from instant_bookings.offer_services import InstantBookingOfferService
from instant_bookings.services import InstantBookingQuoteService
from services.models import Service


# Customer sees a tip prompt after 5 and 10 minutes.
TIP_PROMPT_INTERVAL_MINUTES = 5

# Provider can see and accept the booking for the full 15 minutes.
MAX_PROVIDER_SEARCH_MINUTES = 15


def expire_booking_if_required(booking):
    """
    End the provider search only after the final 15-minute deadline.

    The 5-minute timer is only for customer tip prompts. It must not remove
    the booking from the provider's list.
    """
    now = timezone.now()
    final_deadline = booking.search_deadline or booking.expires_at

    # Compatibility for old bookings that do not have a deadline.
    if not final_deadline:
        final_deadline = booking.created_at + timedelta(
            minutes=MAX_PROVIDER_SEARCH_MINUTES
        )
        booking.search_deadline = final_deadline
        booking.expires_at = final_deadline
        booking.save(
            update_fields=["search_deadline", "expires_at", "updated_at"]
        )

    # Only after 15 minutes should the booking stop accepting providers.
    if (
        booking.status
        in [
            InstantBookingStatus.SEARCHING,
            InstantBookingStatus.TIP_REQUIRED,
        ]
        and final_deadline <= now
    ):
        InstantBookingOffer.objects.filter(
            instant_booking=booking,
            status=InstantBookingOfferStatus.PENDING,
        ).update(status=InstantBookingOfferStatus.EXPIRED)

        booking.status = InstantBookingStatus.NO_PROVIDER
        booking.save(update_fields=["status", "updated_at"])

    return booking


def get_tip_prompt_details(booking):
    """
    Returns data needed by the customer app to show the tip popup.

    The frontend should show a popup only when `tip_prompt_round` changes:
    0 = no prompt yet
    1 = five-minute prompt
    2 = ten-minute prompt
    """
    now = timezone.now()
    final_deadline = booking.search_deadline or booking.expires_at

    if not final_deadline:
        return {
            "tip_prompt_due": False,
            "tip_prompt_round": 0,
            "tip_prompt_message": None,
            "remaining_search_seconds": 0,
        }

    remaining_seconds = max(
        0,
        int((final_deadline - now).total_seconds()),
    )

    if booking.status != InstantBookingStatus.SEARCHING:
        return {
            "tip_prompt_due": False,
            "tip_prompt_round": 0,
            "tip_prompt_message": None,
            "remaining_search_seconds": remaining_seconds,
        }

    elapsed_seconds = max(
        0,
        int((now - booking.created_at).total_seconds()),
    )

    # 0 = first five minutes, 1 = after five minutes, 2 = after ten minutes.
    prompt_round = elapsed_seconds // (TIP_PROMPT_INTERVAL_MINUTES * 60)

    if prompt_round < 1:
        return {
            "tip_prompt_due": False,
            "tip_prompt_round": 0,
            "tip_prompt_message": None,
            "remaining_search_seconds": remaining_seconds,
        }

    return {
        "tip_prompt_due": True,
        "tip_prompt_round": min(prompt_round, 2),
        "tip_prompt_message": (
            "No provider has accepted yet. Add a tip to improve "
            "your chances of getting a provider."
        ),
        "remaining_search_seconds": remaining_seconds,
    }


def booking_response_data(booking):
    """
    Combines normal booking data with live tip-prompt information.
    """
    data = InstantBookingReadSerializer(booking).data
    data.update(get_tip_prompt_details(booking))
    return data


@extend_schema(
    tags=["Instant Bookings"],
    parameters=[
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Service name, for example: Wiring",
        )
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Service search results',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'data': [{'service_uuid': '550e8400-e29b-41d4-a716-446655440010',
           'service_name': 'Wiring',
           'description': 'Electrical wiring service',
           'category_name': 'Electrical',
           'subcategory_name': 'Wiring',
           'indicative_price': '500.00',
           'duration_minutes': 60}]},
                )
            ],
        )
    },
)
class InstantServiceSearchAPIView(APIView):
    """
    Customers search only by service name.
    """

    

    def get(self, request):
        search_text = request.query_params.get("search", "").strip()

        if not search_text:
            return Response(
                {"success": True, "data": []},
                status=status.HTTP_200_OK,
            )

        services = (
            Service.objects.select_related(
                "business",
                "category",
                "subcategory",
            )
            .filter(
                name__icontains=search_text,
                is_active=True,
                business__is_active=True,
            )
            .order_by("name")
        )

        return Response(
            {
                "success": True,
                "data": InstantServiceSearchResultSerializer(
                    services,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Instant Bookings"],
    request=InstantBookingCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Instant booking created',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'message': 'Instant booking created and provider offers sent successfully.',
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },
)
class InstantBookingCreateAPIView(APIView):
    """
    Customer creates an instant booking and eligible providers receive offers.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = InstantBookingCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        address = serializer.validated_data["address"]
        requested_service_name = serializer.validated_data[
            "requested_service_name"
        ]
        customer_note = serializer.validated_data.get("customer_note", "")

        # The quote service reads address and service name from a booking object.
        # It does not need this temporary object to be saved in the database.
        quote_booking = InstantBooking(
            customer=request.user,
            address=address,
            requested_service_name=requested_service_name,
            customer_note=customer_note,
        )

        quote = InstantBookingQuoteService.get_quote(quote_booking)

        # Service exists, but there is currently no eligible provider within 15 km.
        if not quote or not quote.get("candidates"):
            booking = InstantBooking.objects.create(
                customer=request.user,
                address=address,
                requested_service_name=requested_service_name,
                customer_note=customer_note,
                status=InstantBookingStatus.NO_PROVIDER,
            )

            if quote and quote.get("no_provider_reason") == "UNAVAILABLE":
                message = (
                    "A provider for this service is available in your area, "
                    "but no provider is currently available for instant booking. "
                    "Please try again later or book a scheduled service."
                )
            else:
                message = (
                    "No provider is available within 15 km. "
                    "Please book a scheduled service."
                )

            return Response(
                {
                    "success": True,
                    "message": message,
                    "data": booking_response_data(booking),
                },
                status=status.HTTP_201_CREATED,
            )

        search_deadline = timezone.now() + timedelta(
            minutes=MAX_PROVIDER_SEARCH_MINUTES
        )

        booking = InstantBooking.objects.create(
            customer=request.user,
            address=address,
            requested_service_name=requested_service_name,
            customer_note=customer_note,
            category=quote["category"],
            subcategory=quote["subcategory"],
            # The quote service sorts candidates nearest-first.
            selected_service=quote["candidates"][0]["service"],
            average_service_price=quote["average_service_price"],
            travel_charge=quote["travel_charge"],
            platform_fee=quote["platform_fee"],
            gst_percentage=quote["gst_percentage"],
            gst_amount=quote["gst_amount"],
            quoted_price=quote["quoted_price"],
            total_payable_price=quote["quoted_price"],
            search_distance_km=quote["search_distance_km"],
            status=InstantBookingStatus.SEARCHING,
            # Both fields deliberately store the final 15-minute deadline.
            expires_at=search_deadline,
            search_deadline=search_deadline,
            offer_round=1,
        )

        InstantBookingOfferService.create_offers(
            booking=booking,
            candidates=quote["candidates"],
        )

        booking.refresh_from_db()

        return Response(
            {
                "success": True,
                "message": (
                    "Instant booking created and provider offers "
                    "sent successfully."
                ),
                "data": booking_response_data(booking),
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Instant Bookings"],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Instant booking details',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },)
class CustomerInstantBookingDetailAPIView(APIView):
    """
    Customer checks a booking's current status and tip prompt details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, instant_booking_uuid):
        booking = get_object_or_404(
            InstantBooking.objects.select_related(
                "address",
                "category",
                "subcategory",
                "selected_service",
                "assigned_business",
                "assigned_employee",
            ),
            instant_booking_uuid=instant_booking_uuid,
            customer=request.user,
        )

        booking = expire_booking_if_required(booking)

        return Response(
            {
                "success": True,
                "data": booking_response_data(booking),
            },
            status=status.HTTP_200_OK,
        )





@extend_schema(tags=["Instant Bookings"],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Pending instant booking offers',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'data': [{'id': 1,
           'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
           'service_uuid': '550e8400-e29b-41d4-a716-446655440010',
           'service_name': 'Wiring',
           'business_uuid': '550e8400-e29b-41d4-a716-446655440011',
           'business_name': 'ABC Electrical Services',
           'employee_uuid': '550e8400-e29b-41d4-a716-446655440012',
           'employee_name': 'John',
           'distance_km': '4.50',
           'estimated_travel_minutes': 15,
           'status': 'PENDING',
           'accepted_at': None,
           'created_at': '2026-09-04T12:15:00Z',
           'updated_at': '2026-09-04T12:15:00Z'}]},
                )
            ],
        )
    },)
class BusinessInstantBookingOffersAPIView(APIView):
    """
    Business owner views pending offers.

    A provider can see the offer until the final 15-minute deadline.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # Close only bookings whose final 15-minute deadline has passed.
        booking_ids = (
            InstantBookingOffer.objects.filter(
                business__owner=request.user,
                status=InstantBookingOfferStatus.PENDING,
            )
            .values_list("instant_booking_id", flat=True)
            .distinct()
        )

        for booking in InstantBooking.objects.filter(id__in=booking_ids):
            expire_booking_if_required(booking)

        offers = (
            InstantBookingOffer.objects.select_related(
                "instant_booking",
                "service",
                "business",
                "employee",
            )
            .filter(
                business__owner=request.user,
                status=InstantBookingOfferStatus.PENDING,
                instant_booking__status__in=[
                    InstantBookingStatus.SEARCHING,
                    InstantBookingStatus.TIP_REQUIRED,
                ],
                instant_booking__search_deadline__gt=now,
            )
            .order_by("-created_at")
        )

        return Response(
            {
                "success": True,
                "data": InstantBookingOfferReadSerializer(
                    offers,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Instant Bookings"],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Successful response',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'message': 'Instant booking accepted successfully.',
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },)
class BusinessInstantBookingOfferAcceptAPIView(APIView):
    """
    First eligible provider to accept gets the booking.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, offer_id):
        offer = get_object_or_404(
            InstantBookingOffer.objects.select_for_update(),
            id=offer_id,
        )

        if offer.business.owner != request.user:
            return Response(
                {
                    "success": False,
                    "message": "You cannot accept another business's offer.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        booking = InstantBooking.objects.select_for_update().get(
            id=offer.instant_booking_id
        )

        booking = expire_booking_if_required(booking)

        if booking.status not in [
            InstantBookingStatus.SEARCHING,
            InstantBookingStatus.TIP_REQUIRED,
        ]:
            return Response(
                {
                    "success": False,
                    "message": "This booking is no longer accepting providers.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.search_deadline <= timezone.now():
            return Response(
                {
                    "success": False,
                    "message": "This booking is no longer accepting providers.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if offer.status != InstantBookingOfferStatus.PENDING:
            return Response(
                {
                    "success": False,
                    "message": "This offer is no longer available.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # First provider wins; other pending offers are closed.
        offer.status = InstantBookingOfferStatus.ACCEPTED
        offer.accepted_at = timezone.now()
        offer.save(update_fields=["status", "accepted_at", "updated_at"])

        InstantBookingOffer.objects.filter(
            instant_booking=booking,
            status=InstantBookingOfferStatus.PENDING,
        ).exclude(id=offer.id).update(
            status=InstantBookingOfferStatus.EXPIRED
        )

        booking.assigned_business = offer.business
        booking.assigned_employee = offer.employee
        booking.selected_service = offer.service
        booking.status = InstantBookingStatus.ASSIGNED
        booking.save(
            update_fields=[
                "assigned_business",
                "assigned_employee",
                "selected_service",
                "status",
                "updated_at",
            ]
        )

        from chat_service.services import ChatService
        ChatService.get_or_create_conversation_for_instant_booking(booking)

        return Response(
            {
                "success": True,
                "message": "Instant booking accepted successfully.",
                "data": booking_response_data(booking),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Instant Bookings"],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Successful response',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'message': 'Instant booking cancelled successfully.',
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },)
class CustomerInstantBookingCancelAPIView(APIView):
    """
    Customer cancels a booking that has not been completed.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, instant_booking_uuid):
        booking = get_object_or_404(
            InstantBooking.objects.select_for_update(),
            instant_booking_uuid=instant_booking_uuid,
            customer=request.user,
        )

        if booking.status in [
            InstantBookingStatus.COMPLETED,
            InstantBookingStatus.CANCELLED,
        ]:
            return Response(
                {
                    "success": False,
                    "message": "This booking cannot be cancelled.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        InstantBookingOffer.objects.filter(
            instant_booking=booking,
            status=InstantBookingOfferStatus.PENDING,
        ).update(status=InstantBookingOfferStatus.EXPIRED)

        booking.status = InstantBookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "success": True,
                "message": "Instant booking cancelled successfully.",
                "data": booking_response_data(booking),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Instant Bookings"],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Successful response',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'message': 'Instant service started successfully.',
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },)
class BusinessInstantBookingStartAPIView(APIView):
    """
    Assigned business owner marks a booking as in progress.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, instant_booking_uuid):
        booking = get_object_or_404(
            InstantBooking.objects.select_related("assigned_business"),
            instant_booking_uuid=instant_booking_uuid,
        )

        if (
            not booking.assigned_business
            or booking.assigned_business.owner != request.user
        ):
            return Response(
                {
                    "success": False,
                    "message": "You are not assigned to this booking.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status != InstantBookingStatus.ASSIGNED:
            return Response(
                {
                    "success": False,
                    "message": "Only an assigned booking can be started.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = InstantBookingStatus.IN_PROGRESS
        booking.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "success": True,
                "message": "Instant service started successfully.",
                "data": booking_response_data(booking),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Instant Bookings"],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Successful response',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'message': 'Instant service completed successfully.',
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },)
class BusinessInstantBookingCompleteAPIView(APIView):
    """
    Assigned business owner marks a booking as completed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, instant_booking_uuid):
        booking = get_object_or_404(
            InstantBooking.objects.select_related("assigned_business"),
            instant_booking_uuid=instant_booking_uuid,
        )

        if (
            not booking.assigned_business
            or booking.assigned_business.owner != request.user
        ):
            return Response(
                {
                    "success": False,
                    "message": "You are not assigned to this booking.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status != InstantBookingStatus.IN_PROGRESS:
            return Response(
                {
                    "success": False,
                    "message": "Only an in-progress booking can be completed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = InstantBookingStatus.COMPLETED
        booking.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "success": True,
                "message": "Instant service completed successfully.",
                "data": booking_response_data(booking),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Instant Bookings"],
    request=InstantBookingRetrySerializer,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description='Successful response',
            examples=[
                OpenApiExample(
                    "Response",
                    value={'success': True,
 'message': 'Tip updated successfully. Providers can still accept this booking until the search '
            'ends.',
 'data': {'instant_booking_uuid': '550e8400-e29b-41d4-a716-446655440000',
          'category_uuid': '550e8400-e29b-41d4-a716-446655440001',
          'category_name': 'Electrical',
          'subcategory_uuid': '550e8400-e29b-41d4-a716-446655440002',
          'subcategory_name': 'Wiring',
          'address_uuid': '550e8400-e29b-41d4-a716-446655440003',
          'requested_service_name': 'Wiring',
          'customer_note': 'Please check the wiring issue.',
          'average_service_price': '500.00',
          'travel_charge': '50.00',
          'platform_fee': '25.00',
          'gst_percentage': '18.00',
          'gst_amount': '103.50',
          'quoted_price': '678.50',
          'tip_amount': '0.00',
          'total_payable_price': '678.50',
          'search_distance_km': '7.50',
          'offer_round': 1,
          'expires_at': '2026-09-04T12:30:00Z',
          'search_deadline': '2026-09-04T12:30:00Z',
          'status': 'SEARCHING',
          'created_at': '2026-09-04T12:15:00Z',
          'updated_at': '2026-09-04T12:15:00Z',
          'tip_prompt_due': False,
          'tip_prompt_round': 0,
          'tip_prompt_message': None,
          'remaining_search_seconds': 900}},
                )
            ],
        )
    },
)
class CustomerInstantBookingRetryAPIView(APIView):
    """
    Customer adds or increases a tip while the 15-minute provider search
    remains active. Existing provider offers are not removed.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, instant_booking_uuid):
        booking = get_object_or_404(
            InstantBooking.objects.select_for_update(),
            instant_booking_uuid=instant_booking_uuid,
            customer=request.user,
        )

        booking = expire_booking_if_required(booking)

        if booking.status == InstantBookingStatus.NO_PROVIDER:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No provider is available. "
                        "Please book a scheduled service."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.status not in [
            InstantBookingStatus.SEARCHING,
            InstantBookingStatus.TIP_REQUIRED,
        ]:
            return Response(
                {
                    "success": False,
                    "message": "This booking cannot be updated with a tip.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InstantBookingRetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requested_tip = serializer.validated_data["tip_amount"]

        if requested_tip < booking.tip_amount:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Tip amount cannot be lower than the "
                        "existing tip amount."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.tip_amount = requested_tip
        booking.total_payable_price = (
            booking.quoted_price + booking.tip_amount
        )
        booking.status = InstantBookingStatus.SEARCHING

        elapsed_seconds = int(
            (timezone.now() - booking.created_at).total_seconds()
        )
        booking.offer_round = min(
            3,
            max(
                1,
                (elapsed_seconds // (TIP_PROMPT_INTERVAL_MINUTES * 60)) + 1,
            ),
        )

        booking.save(
            update_fields=[
                "tip_amount",
                "total_payable_price",
                "status",
                "offer_round",
                "updated_at",
            ]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Tip updated successfully. Providers can still "
                    "accept this booking until the search ends."
                ),
                "data": booking_response_data(booking),
            },
            status=status.HTTP_200_OK,
        )