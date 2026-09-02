from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from instant_bookings.models import (
    InstantBooking,
    InstantBookingOffer,
    InstantBookingOfferStatus,
    InstantBookingStatus,
)
from instant_bookings.offer_services import (
    InstantBookingOfferService,
)
from instant_bookings.services import (
    InstantBookingQuoteService,
)


class InstantBookingRetryService:
    """
    Manages five-minute provider-offer retry rounds.

    Total search duration:
        15 minutes

    Each round:
        5 minutes

    The customer may increase the tip before a new round.
    """

    ROUND_DURATION_MINUTES = 5
    MAX_SEARCH_DURATION_MINUTES = 15

    @classmethod
    @transaction.atomic
    def retry_search(
        cls,
        booking,
        requested_tip=Decimal("0.00"),
    ):
        """
        Expire the previous round and start another round.

        Returns:
            {
                "status": "SEARCHING",
                "booking": booking,
                "offers": [...]
            }

            or:

            {
                "status": "TIP_REQUIRED",
                "booking": booking,
                "offers": []
            }

            or:

            {
                "status": "NO_PROVIDER",
                "booking": booking,
                "offers": []
            }
        """

        booking = (
            InstantBooking.objects
            .select_for_update()
            .get(pk=booking.pk)
        )

        now = timezone.now()

        # The first booking may not yet have a deadline if it
        # was created before retry support was added.
        if not booking.search_deadline:
            booking.search_deadline = (
                booking.created_at
                + timedelta(
                    minutes=cls.MAX_SEARCH_DURATION_MINUTES
                )
            )

        # No retry is allowed after fifteen minutes.
        if now >= booking.search_deadline:
            cls._mark_no_provider(booking)

            return {
                "status": InstantBookingStatus.NO_PROVIDER,
                "booking": booking,
                "offers": [],
            }

        if requested_tip < booking.tip_amount:
            raise ValueError(
                "The new tip cannot be lower than the "
                "current tip."
            )

        # Expire offers from the previous round.
        InstantBookingOffer.objects.filter(
            instant_booking=booking,
            status=InstantBookingOfferStatus.PENDING,
        ).update(
            status=InstantBookingOfferStatus.EXPIRED,
            updated_at=now,
        )

        booking.tip_amount = requested_tip
        booking.offer_round += 1

        quote = (
            InstantBookingQuoteService.get_quote(
                booking
            )
        )

        if not quote:
            # The customer can retry again while the
            # fifteen-minute deadline has not elapsed.
            booking.status = (
                InstantBookingStatus.TIP_REQUIRED
            )
            booking.expires_at = None

            booking.save(
                update_fields=[
                    "tip_amount",
                    "offer_round",
                    "search_deadline",
                    "expires_at",
                    "status",
                    "updated_at",
                ]
            )

            return {
                "status": InstantBookingStatus.TIP_REQUIRED,
                "booking": booking,
                "offers": [],
            }

        booking.category = quote["category"]
        booking.subcategory = quote["subcategory"]
        booking.average_service_price = (
            quote["average_service_price"]
        )
        booking.travel_charge = (
            quote["travel_charge"]
        )
        booking.platform_fee = (
            quote["platform_fee"]
        )
        booking.gst_percentage = (
            quote["gst_percentage"]
        )
        booking.gst_amount = (
            quote["gst_amount"]
        )
        booking.quoted_price = (
            quote["quoted_price"]
        )

        # Tip is added after the service quote.
        booking.total_payable_price = (
            quote["quoted_price"]
            + booking.tip_amount
        )

        booking.search_distance_km = (
            quote["search_distance_km"]
        )
        booking.status = InstantBookingStatus.SEARCHING

        next_round_expiry = min(
            now + timedelta(
                minutes=cls.ROUND_DURATION_MINUTES
            ),
            booking.search_deadline,
        )

        booking.expires_at = next_round_expiry

        booking.save(
            update_fields=[
                "category",
                "subcategory",
                "average_service_price",
                "travel_charge",
                "platform_fee",
                "gst_percentage",
                "gst_amount",
                "quoted_price",
                "tip_amount",
                "total_payable_price",
                "search_distance_km",
                "offer_round",
                "expires_at",
                "search_deadline",
                "status",
                "updated_at",
            ]
        )

        offers = (
            InstantBookingOfferService.create_offers(
                booking=booking,
                candidates=quote["candidates"],
            )
        )

        # Keep the expiry within the absolute fifteen-minute
        # search deadline.
        booking.expires_at = next_round_expiry
        booking.search_deadline = (
            booking.search_deadline
        )
        booking.save(
            update_fields=[
                "expires_at",
                "search_deadline",
                "updated_at",
            ]
        )

        return {
            "status": InstantBookingStatus.SEARCHING,
            "booking": booking,
            "offers": offers,
        }

    @staticmethod
    def _mark_no_provider(booking):
        """
        Permanently stop searching after fifteen minutes.
        """

        now = timezone.now()

        InstantBookingOffer.objects.filter(
            instant_booking=booking,
            status=InstantBookingOfferStatus.PENDING,
        ).update(
            status=InstantBookingOfferStatus.EXPIRED,
            updated_at=now,
        )

        booking.status = InstantBookingStatus.NO_PROVIDER
        booking.expires_at = None

        booking.save(
            update_fields=[
                "status",
                "expires_at",
                "updated_at",
            ]
        )