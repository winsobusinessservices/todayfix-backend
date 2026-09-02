from datetime import timedelta

from django.utils import timezone

from instant_bookings.models import (
    InstantBookingOffer,
    InstantBookingOfferStatus,
    InstantBookingStatus,
)


class InstantBookingOfferService:
    """
    Creates offers for eligible providers.

    Provider offers remain pending until the booking's 15-minute
    search deadline. They are not expired after five minutes.
    """

    @staticmethod
    def create_offers(booking, candidates):
        if not booking.search_deadline:
            booking.search_deadline = timezone.now() + timedelta(minutes=15)

        offers_to_create = []

        for candidate in candidates:
            already_has_pending_offer = InstantBookingOffer.objects.filter(
                instant_booking=booking,
                business=candidate["business"],
                employee=candidate["employee"],
                status=InstantBookingOfferStatus.PENDING,
            ).exists()

            if already_has_pending_offer:
                continue

            offers_to_create.append(
                InstantBookingOffer(
                    instant_booking=booking,
                    service=candidate["service"],
                    business=candidate["business"],
                    employee=candidate["employee"],
                    distance_km=candidate["distance_km"],
                    # Current quote service provides this key.
                    estimated_travel_minutes=candidate["travel_minutes"],
                    status=InstantBookingOfferStatus.PENDING,
                )
            )

        if offers_to_create:
            InstantBookingOffer.objects.bulk_create(offers_to_create)

        booking.status = InstantBookingStatus.SEARCHING
        booking.expires_at = booking.search_deadline
        booking.save(
            update_fields=[
                "status",
                "expires_at",
                "search_deadline",
                "updated_at",
            ]
        )

        return offers_to_create