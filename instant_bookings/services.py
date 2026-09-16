import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from django.db.models import Q
from django.utils import timezone

from bookings.choices import BookingStatus
from bookings.models import Booking, BookingEmployee

from business.choices import (
    BusinessType,
    DayOfWeek,
    EmployeeAvailabilityStatus,
)
from business.models import (
    EmployeeWorkingSchedule,
    ProviderAvailability,
)
from rapidfuzz import fuzz
from instant_bookings.models import (
    InstantBookingPricingRule,
)

from services.models import Service, ServiceEmployee
from services.search_utils import expand_search_words

from instant_bookings.utils.geo import (
    calculate_distance_km,
    extract_coordinates,
)

from services.models import Service, ServiceEmployee


class InstantBookingQuoteService:
    """
    Finds eligible providers and calculates the instant quote.

    Travel charging rule:
        First 5 km is free.
        Only kilometres above 5 km are chargeable.

    Final price:
        service price
        + travel charge
        + platform fee
        + GST
    """

    FREE_TRAVEL_DISTANCE_KM = Decimal("5.00")
    PROVIDER_SPEED_KMH = 30
    FUZZY_MATCH_THRESHOLD = 70
    MINIMUM_MATCHING_WORD_LENGTH = 3

    @staticmethod
    def _normalize_search_text(value):
        """
        Normalize service text for matching.

        Keeps the matching case-insensitive and removes punctuation
        differences so searches such as:

            AC-installation
            AC installation
            ac installation

        are treated consistently.
        """
        value = (value or "").strip().lower()

        normalized = []

        for character in value:
            if character.isalnum() or character.isspace():
                normalized.append(character)
            else:
                normalized.append(" ")

        return " ".join(
            "".join(normalized).split()
        )

    @classmethod
    def _service_matches_search(
        cls,
        requested_service_name,
        service,
    ):
        """
        Determine whether a provider service is relevant to the
        customer's requested service.

        Matching layers:

        1. Exact/substring phrase matching.
        2. Word matching.
        3. WordNet/manual synonym matching.
        4. Typo-tolerant fuzzy matching.
        5. Matching against both service name and description.

        The existing fuzzy threshold of 70 is retained.
        """

        requested_text = cls._normalize_search_text(
            requested_service_name
        )

        if not requested_text:
            return False

        service_name = cls._normalize_search_text(
            service.name
        )

        service_description = cls._normalize_search_text(
            service.description
        )

        searchable_text = " ".join(
            part
            for part in (
                service_name,
                service_description,
            )
            if part
        )

        if not searchable_text:
            return False

        # ---------------------------------------------------------
        # 1. Exact / phrase matching
        # ---------------------------------------------------------
        if requested_text in searchable_text:
            return True

        # ---------------------------------------------------------
        # 2. Expand the customer's search words using the SAME
        #    synonym system used by the normal service search.
        #
        #    This includes:
        #      - WordNet synonyms
        #      - admin-managed SearchSynonym pairs
        # ---------------------------------------------------------
        requested_words = requested_text.split()

        expanded_words = expand_search_words(
            requested_words
        )

        normalized_expanded_words = {
            cls._normalize_search_text(word)
            for word in expanded_words
            if word
        }

        normalized_expanded_words.discard("")

        # ---------------------------------------------------------
        # 3. Direct word matching.
        #
        #    We intentionally require meaningful words rather than
        #    allowing a short generic token such as "ac" by itself
        #    to match every AC-related service.
        # ---------------------------------------------------------
        service_words = set(
            searchable_text.split()
        )

        meaningful_requested_words = {
            word
            for word in normalized_expanded_words
            if len(word) >= cls.MINIMUM_MATCHING_WORD_LENGTH
        }

        for word in meaningful_requested_words:
            if word in service_words:
                return True

        # ---------------------------------------------------------
        # 4. Fuzzy matching.
        #
        #    This handles spelling mistakes such as:
        #
        #        instalation -> installation
        #        maintanance -> maintenance
        #
        #    We compare every meaningful search term against the
        #    individual words in the provider's name/description.
        # ---------------------------------------------------------
        service_word_list = list(
            service_words
        )

        for search_word in meaningful_requested_words:
            for service_word in service_word_list:
                if fuzz.ratio(
                    search_word,
                    service_word,
                ) >= cls.FUZZY_MATCH_THRESHOLD:
                    return True

        # ---------------------------------------------------------
        # 5. Fuzzy phrase matching.
        #
        #    Useful when the customer enters a phrase and the
        #    provider uses a slightly different phrase/order.
        # ---------------------------------------------------------
        for search_term in {
            requested_text,
            *normalized_expanded_words,
        }:
            if not search_term:
                continue

            if fuzz.partial_ratio(
                search_term,
                searchable_text,
            ) >= cls.FUZZY_MATCH_THRESHOLD:
                return True

        return False

    @classmethod
    def get_quote(cls, booking):
        """
        Find providers in the nearest available distance band.

        The customer searches only by service name. Category and
        subcategory are taken internally from the matching provider
        service.
        """

        customer_latitude, customer_longitude = (
            extract_coordinates(
                booking.address.location
            )
        )

        requested_service_name = (
            booking.requested_service_name or ""
        ).strip()

        matching_services = (
            Service.objects.filter(
                is_active=True,
                business__is_active=True,
            )
            .select_related(
                "business",
                "business__owner",
                "category",
                "subcategory",
            )
            .prefetch_related(
                "employee_assignments__employee",
            )
        )

        matching_service_ids = []

        for service in matching_services:
            if cls._service_matches_search(
                requested_service_name=requested_service_name,
                service=service,
            ):
                matching_service_ids.append(
                    service.id
                )

        matching_services = matching_services.filter(
            id__in=matching_service_ids,
        )

        provider_found_within_distance = False
        candidates = []

        for service in matching_services:
            business = service.business

            # Provider business location is stored as a Google Maps
            # iframe string in BusinessProfile.location.
            try:
                provider_latitude, provider_longitude = (
                    extract_coordinates(
                        business.location
                    )
                )
            except ValueError:
                # Ignore providers with an invalid location.
                continue

            distance_km = calculate_distance_km(
                customer_latitude,
                customer_longitude,
                provider_latitude,
                provider_longitude,
            )

            # No provider beyond the 15 km maximum is accepted.
            pricing_rule = cls._get_pricing_rule(
                distance_km
            )

            if not pricing_rule:
                continue

            provider_found_within_distance = True

            travel_minutes = (
                cls._calculate_travel_minutes(
                    distance_km
                )
            )

            available_providers = (
                cls._get_available_providers(
                    service=service,
                    travel_minutes=travel_minutes,
                )
            )

            for employee in available_providers:
                candidates.append(
                    {
                        "service": service,
                        "business": business,
                        "employee": employee,
                        "distance_km": Decimal(
                            str(distance_km)
                        ),
                        "travel_minutes": travel_minutes,
                        "pricing_rule": pricing_rule,
                    }
                )

        if not candidates:
            if provider_found_within_distance:
                return {
                    "no_provider_reason": "UNAVAILABLE",
                    "candidates": [],
                }

            return None

        # If providers exist in 0–5 km, only that group is used.
        # Otherwise 5–10 km is used, then 10–15 km.
        nearest_band_maximum = min(
            candidate["pricing_rule"].maximum_distance_km
            for candidate in candidates
        )

        candidates = [
            candidate
            for candidate in candidates
            if candidate["pricing_rule"].maximum_distance_km
            == nearest_band_maximum
        ]

        pricing_rule = candidates[0]["pricing_rule"]

        # The customer receives the average service price of the
        # eligible providers in the selected distance band.
        average_service_price = (
            sum(
                candidate["service"].price
                for candidate in candidates
            )
            / len(candidates)
        )

        average_distance = (
            sum(
                candidate["distance_km"]
                for candidate in candidates
            )
            / len(candidates)
        )

        # Only distance above the first free 5 km is chargeable.
        chargeable_distance = max(
            Decimal("0.00"),
            average_distance
            - cls.FREE_TRAVEL_DISTANCE_KM,
        )

                # Monetary values are rounded before the next calculation so the
        # displayed breakdown always equals the final quoted price.
        money = Decimal("0.01")

        average_service_price = average_service_price.quantize(
            money,
            rounding=ROUND_HALF_UP,
        )

        travel_charge = (
            chargeable_distance
            * pricing_rule.travel_fee_per_km
        ).quantize(
            money,
            rounding=ROUND_HALF_UP,
        )

        platform_fee = pricing_rule.platform_fee.quantize(
            money,
            rounding=ROUND_HALF_UP,
        )

        subtotal = (
            average_service_price
            + travel_charge
            + platform_fee
        )

        gst_amount = (
            subtotal
            * pricing_rule.gst_percentage
            / Decimal("100")
        ).quantize(
            money,
            rounding=ROUND_HALF_UP,
        )

        quoted_price = (
            subtotal + gst_amount
        ).quantize(
            money,
            rounding=ROUND_HALF_UP,
        )

        candidates.sort(
            key=lambda candidate: candidate["distance_km"]
        )

        first_service = candidates[0]["service"]

        return {
            # These are derived internally, not submitted by the
            # customer.
            "category": first_service.category,
            "subcategory": first_service.subcategory,

            "average_service_price": (
                average_service_price.quantize(
                    Decimal("0.01")
                )
            ),

            "travel_charge": travel_charge.quantize(
                Decimal("0.01")
            ),

            "platform_fee": platform_fee.quantize(
                Decimal("0.01")
            ),

            "gst_percentage": (
                pricing_rule.gst_percentage.quantize(
                    Decimal("0.01")
                )
            ),

            "gst_amount": gst_amount.quantize(
                Decimal("0.01")
            ),

            "quoted_price": quoted_price.quantize(
                Decimal("0.01")
            ),

            "search_distance_km": (
                nearest_band_maximum
            ),

            "candidates": candidates,
        }

    @staticmethod
    def _get_pricing_rule(distance_km):
        """
        Select a distance rule.

        The upper boundary is exclusive:
            0.00 <= distance < 5.00
            5.00 <= distance < 10.00
            10.00 <= distance < 15.00

        Therefore, exactly 15 km is rejected.

        TEMPORARY: pricing rules are disabled for now. Instead of
        looking up InstantBookingPricingRule from the DB, we return
        a hardcoded zero-fee fallback so instant bookings aren't
        blocked while pricing setup is pending. Distances beyond
        15 km are still rejected below.

        TODO: remove this bypass and restore the DB lookup once
        real InstantBookingPricingRule rows are configured.
        """
        distance = Decimal(str(distance_km))

        if distance >= Decimal("15.00"):
            return None

        return SimpleNamespace(
            minimum_distance_km=Decimal("0.00"),
            maximum_distance_km=Decimal("15.00"),
            platform_fee=Decimal("0.00"),
            travel_fee_per_km=Decimal("0.00"),
            gst_percentage=Decimal("0.00"),
        )

    @classmethod
    def _calculate_travel_minutes(cls, distance_km):
        """
        Estimate provider travel time using the configured
        initial provider speed.

        This does not affect customer price.
        """
        return max(
            60,
            math.ceil(
                float(distance_km)
                / cls.PROVIDER_SPEED_KMH
                * 60
            ),
        )

    @classmethod
    def _get_available_providers(
        cls,
        service,
        travel_minutes,
    ):
        """
        Return providers who:

        1. are marked AVAILABLE;
        2. are currently inside working hours;
        3. are qualified for the service;
        4. have enough time to travel and perform the service
           without conflicting with an existing booking.
        """
        business = service.business

        if business.business_type == BusinessType.INDIVIDUAL:
            owner = business.owner

            is_available = (
                ProviderAvailability.objects.filter(
                    business=business,
                    owner=owner,
                    employee__isnull=True,
                    status=(
                        EmployeeAvailabilityStatus.AVAILABLE
                    ),
                ).exists()
            )

            if not is_available:
                return []

            if not cls._is_inside_working_hours(
                business=business,
                owner=owner,
                employee=None,
                required_minutes=(
                    travel_minutes + service.duration
                ),
            ):
                return []

            if cls._has_scheduled_conflict(
                business=business,
                employee=None,
                owner=owner,
                required_minutes=(
                    travel_minutes + service.duration
                ),
            ):
                return []

            # None represents the individual business owner.
            return [None]

        assignments = (
            ServiceEmployee.objects.filter(
                service=service,
                employee__is_active=True,
            )
            .select_related("employee")
        )

        available_employees = []

        for assignment in assignments:
            employee = assignment.employee

            is_available = (
                ProviderAvailability.objects.filter(
                    business=business,
                    employee=employee,
                    owner__isnull=True,
                    status=(
                        EmployeeAvailabilityStatus.AVAILABLE
                    ),
                ).exists()
            )

            if not is_available:
                continue

            required_minutes = (
                travel_minutes + service.duration
            )

            if not cls._is_inside_working_hours(
                business=business,
                owner=None,
                employee=employee,
                required_minutes=required_minutes,
            ):
                continue

            if cls._has_scheduled_conflict(
                business=business,
                employee=employee,
                owner=None,
                required_minutes=required_minutes,
            ):
                continue

            available_employees.append(employee)

        return available_employees

    @staticmethod
    def _is_inside_working_hours(
        business,
        owner,
        employee,
        required_minutes,
    ):
        """
        Confirm that the provider is working now and has enough
        working time remaining for travel plus service duration.

        A provider's day can be split across several slots
        (MORNING, AFTERNOON, EVENING). If the slot containing
        "now" doesn't have enough time left on its own, but the
        next slot starts exactly where it ends (no gap), that
        slot is treated as a continuation of the same working
        window - e.g. MORNING 8-12 followed immediately by
        AFTERNOON 12-16 lets an instant booking that needs until
        1pm through, instead of being rejected just because it
        crosses the MORNING/AFTERNOON boundary.
        """
        now = timezone.localtime()
        current_day = now.strftime("%A").upper()
        current_time = now.time()

        schedule_filter = {
            "business": business,
            "day_of_week": current_day,
            "is_active": True,
        }

        if employee is not None:
            schedule_filter["employee"] = employee
        else:
            schedule_filter["owner"] = owner

        schedules = list(
            EmployeeWorkingSchedule.objects.filter(
                **schedule_filter
            ).order_by("start_time")
        )

        current_index = next(
            (
                index
                for index, item in enumerate(schedules)
                if item.start_time <= current_time < item.end_time
            ),
            None,
        )

        if current_index is None:
            return False

        # Extend the window through any immediately-following
        # slots (no gap between them).
        window_end = schedules[current_index].end_time

        for schedule in schedules[current_index + 1:]:
            if schedule.start_time != window_end:
                break
            window_end = schedule.end_time

        required_end = (
            datetime.combine(
                now.date(),
                current_time,
            )
            + timedelta(minutes=required_minutes)
        ).time()

        return required_end <= window_end

    @staticmethod
    def _has_scheduled_conflict(
        business,
        employee,
        owner,
        required_minutes,
    ):
        """
        Check today's scheduled bookings.

        A provider is rejected when an existing booking overlaps
        the time needed for travel plus the instant service.

        Future bookings are allowed only when the instant service
        can finish before their scheduled start time.
        """
        now = timezone.localtime()
        today = timezone.localdate()

        active_statuses = [
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
            BookingStatus.IN_PROGRESS,
        ]

        booking_filter = {
            "business": business,
            "scheduled_date": today,
            "status__in": active_statuses,
        }

        if employee is not None:
            booking_filter["employee"] = employee
            employee_bookings = Booking.objects.filter(
                **booking_filter
            )

            assigned_bookings = Booking.objects.filter(
                business=business,
                scheduled_date=today,
                status__in=active_statuses,
                booking_employees__employee=employee,
            )

            bookings = (
                employee_bookings
                | assigned_bookings
            ).distinct()

        else:
            bookings = Booking.objects.filter(
                business=business,
                scheduled_date=today,
                status__in=active_statuses,
                employee__isnull=True,
            )

        instant_start = now
        instant_end = (
            instant_start
            + timedelta(minutes=required_minutes)
        )

        for booking in bookings.select_related("service"):
            scheduled_start = datetime.combine(
                today,
                booking.scheduled_time,
            )

            scheduled_end = (
                scheduled_start
                + timedelta(
                    minutes=booking.service.duration
                )
            )

            # If the existing service is already in progress,
            # the provider cannot accept an instant service.
            if booking.status == BookingStatus.IN_PROGRESS:
                if instant_start < scheduled_end:
                    return True

            # Existing booking begins before the instant service
            # finishes, so the two services would overlap.
            if (
                scheduled_start < instant_end
                and scheduled_end > instant_start
            ):
                return True

        return False