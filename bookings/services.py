from django.db import transaction

from accounts.models import Address
from services.models import Service

from .choices import BookingStatus
from .models import Booking


class BookingService:
    """
    Business logic layer for Bookings.
    Handles creation and state transitions safely.
    """

    @staticmethod
    @transaction.atomic
    def create_booking(
        user,
        service_uuid,
        address_uuid,
        scheduled_date,
        scheduled_time,
        notes="",
    ):
        """
        Create a new booking safely.
        """
        # Fetch and validate service
        try:
            service = Service.objects.get(
                uuid=service_uuid,
                is_active=True,
            )
        except Service.DoesNotExist:
            raise ValueError(
                "Service not found or inactive."
            )

        # Validate business is active
        business = service.business
        if not business.is_active:
            raise ValueError(
                "The business offering this service is currently inactive."
            )

        # Fetch and validate address
        try:
            address = Address.objects.get(
                uuid=address_uuid,
                user=user,
            )
        except Address.DoesNotExist:
            raise ValueError(
                "Address not found or does not belong to you."
            )

        # Create booking (snapshots price)
        booking = Booking.objects.create(
            user=user,
            service=service,
            business=business,
            address=address,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            price=service.price,
            status=BookingStatus.PENDING,
            notes=notes,
        )

        return booking

    # =========================================================
    # STATUS TRANSITIONS
    # =========================================================

    @staticmethod
    def _transition_status(booking, from_statuses, to_status, error_msg):
        if booking.status not in from_statuses:
            raise ValueError(error_msg)
        
        booking.status = to_status
        booking.save(update_fields=["status"])
        return booking

    @staticmethod
    def cancel_booking(booking):
        """User cancels a booking."""
        return BookingService._transition_status(
            booking,
            [BookingStatus.PENDING, BookingStatus.CONFIRMED],
            BookingStatus.CANCELLED,
            "Only pending or confirmed bookings can be cancelled."
        )

    @staticmethod
    def accept_booking(booking):
        """Business accepts a booking."""
        return BookingService._transition_status(
            booking,
            [BookingStatus.PENDING],
            BookingStatus.CONFIRMED,
            "Only pending bookings can be accepted."
        )

    @staticmethod
    def reject_booking(booking):
        """Business rejects a booking."""
        return BookingService._transition_status(
            booking,
            [BookingStatus.PENDING],
            BookingStatus.REJECTED,
            "Only pending bookings can be rejected."
        )

    @staticmethod
    def start_booking(booking):
        """Business starts the service."""
        return BookingService._transition_status(
            booking,
            [BookingStatus.CONFIRMED],
            BookingStatus.IN_PROGRESS,
            "Only confirmed bookings can be started."
        )

    @staticmethod
    def complete_booking(booking):
        """Business completes the service."""
        return BookingService._transition_status(
            booking,
            [BookingStatus.IN_PROGRESS],
            BookingStatus.COMPLETED,
            "Only in-progress bookings can be completed."
        )
