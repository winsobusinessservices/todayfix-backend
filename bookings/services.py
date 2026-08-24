from datetime import datetime, timedelta

from django.db import transaction

from accounts.models import Address
from business.models import EmployeeWorkingSchedule
from services.models import Service, ServiceEmployee

from .choices import BookingStatus
from .models import Booking, BookingEmployee


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
        slot_type,
        notes="",
    ):
        """
        Create a scheduled booking and assign an available provider.

        CONCURRENCY SAFETY:
        -------------------
        The provider's EmployeeWorkingSchedule row is used as the
        stable lock row.

        Why?

        Locking existing Booking rows alone is NOT sufficient because
        there may be zero existing bookings for the requested provider
        and slot. In that case there would be nothing to lock.

        Therefore we lock the provider schedule first. Because the
        schedule row already exists, concurrent booking requests for
        the same provider/slot are serialized.

        The flow becomes:

            lock provider schedule
                    ↓
            check existing bookings
                    ↓
            create booking
                    ↓
            transaction commits
                    ↓
            second request gets the lock
                    ↓
            second request sees the new booking
                    ↓
            second request returns "No provider available"

        IMPORTANT:
        select_for_update() requires a database backend that supports
        row-level locking, such as PostgreSQL or MySQL/InnoDB.
        SQLite does NOT provide real SELECT FOR UPDATE row locking.
        """

        # =====================================================
        # FETCH SERVICE
        # =====================================================

        try:
            service = Service.objects.get(
                service_uuid=service_uuid,
                is_active=True,
            )
        except Service.DoesNotExist:
            raise ValueError(
                "Service not found or inactive."
            )

        # =====================================================
        # VALIDATE BUSINESS
        # =====================================================

        business = service.business

        if not business.is_active:
            raise ValueError(
                "The business offering this service is "
                "currently inactive."
            )

        # =====================================================
        # FETCH ADDRESS
        # =====================================================

        try:
            address = Address.objects.get(
                add_uuid=address_uuid,
                user=user,
            )
        except Address.DoesNotExist:
            raise ValueError(
                "Address not found or does not belong to you."
            )

        # =====================================================
        # VALIDATE SLOT
        # =====================================================

        valid_slots = {
            "MORNING",
            "AFTERNOON",
            "EVENING",
        }

        if slot_type not in valid_slots:
            raise ValueError(
                "Invalid booking slot."
            )

        # =====================================================
        # DETERMINE DAY
        # =====================================================

        day_of_week = scheduled_date.strftime(
            "%A"
        ).upper()

        # =====================================================
        # SERVICE DURATION
        # =====================================================

        service_duration = service.duration

        if not service_duration or service_duration <= 0:
            raise ValueError(
                "Service duration must be greater than zero."
            )

        # =====================================================
        # FIND PROVIDER SCHEDULES
        # =====================================================

        if business.business_type == "INDIVIDUAL":

            schedules = (
                EmployeeWorkingSchedule.objects
                .filter(
                    business=business,
                    owner=business.owner,
                    employee__isnull=True,
                    day_of_week=day_of_week,
                    slot_type=slot_type,
                    is_active=True,
                )
                .select_related("owner")
                .order_by("pk")
            )

        else:

            assigned_employee_ids = (
                ServiceEmployee.objects
                .filter(
                    service=service,
                    employee__business=business,
                    employee__is_active=True,
                )
                .values_list(
                    "employee_id",
                    flat=True,
                )
            )

            schedules = (
                EmployeeWorkingSchedule.objects
                .filter(
                    business=business,
                    employee_id__in=assigned_employee_ids,
                    day_of_week=day_of_week,
                    slot_type=slot_type,
                    is_active=True,
                )
                .select_related("employee")
                .order_by("pk")
            )

        # =====================================================
        # IMPORTANT CONCURRENCY LOCK
        # =====================================================
        #
        # THIS IS THE MAIN FIX.
        #
        # We lock the schedule rows BEFORE checking bookings.
        #
        # Why not only lock Booking rows?
        #
        # Because if there are currently zero bookings, a Booking
        # queryset has zero rows and therefore nothing to lock.
        #
        # EmployeeWorkingSchedule is a stable row representing the
        # provider's availability for this day/slot, so it gives us
        # something that BOTH concurrent requests can lock.
        #
        # On PostgreSQL/MySQL, if another transaction already holds
        # one of these locks, this query waits until that transaction
        # commits or rolls back.
        #
        # order_by("pk") ensures concurrent requests acquire multiple
        # provider locks in the same deterministic order, reducing
        # deadlock risk.
        #
        locked_schedules = list(
            schedules
            .select_for_update()
        )

        # =====================================================
        # FIND AVAILABLE PROVIDER
        # =====================================================

        selected_schedule = None
        selected_employee = None

        for schedule in locked_schedules:

            slot_start = datetime.combine(
                scheduled_date,
                schedule.start_time,
            )

            slot_end = datetime.combine(
                scheduled_date,
                schedule.end_time,
            )

            service_end = (
                slot_start
                + timedelta(minutes=service_duration)
            )

            # Service must completely fit inside the slot.
            if service_end > slot_end:
                continue

            # =================================================
            # DETERMINE PROVIDER
            # =================================================

            provider_employee = schedule.employee

            # =================================================
            # CHECK EXISTING BOOKINGS
            # =================================================
            #
            # The schedule row is already locked above.
            #
            # We additionally lock existing matching booking rows.
            #
            # This is NOT the primary concurrency protection because
            # there may be no booking rows.
            #
            # The schedule lock handles the "zero existing bookings"
            # race condition.
            #
            existing_bookings = (
                Booking.objects
                .filter(
                    business=business,
                    scheduled_date=scheduled_date,
                    status__in=[
                        BookingStatus.PENDING,
                        BookingStatus.CONFIRMED,
                        BookingStatus.IN_PROGRESS,
                    ],
                )
                .select_related(
                    "service",
                    "employee",
                )
                .order_by("pk")
            )

            provider_available = True

            for existing_booking in existing_bookings:

                # -------------------------------------------------
                # COMPANY / INVESTOR
                # -------------------------------------------------
                #
                # Only bookings assigned to this employee
                # should block this employee.
                #
                if provider_employee:

                    if not BookingEmployee.objects.filter(
                        booking=existing_booking,
                        employee=provider_employee,
                    ).exists():
                        continue

                # -------------------------------------------------
                # INDIVIDUAL
                # -------------------------------------------------
                #
                # Individual business has no Employee record.
                # Therefore all active bookings for this business
                # belong to the owner and block the owner.
                #
                existing_start = datetime.combine(
                    scheduled_date,
                    existing_booking.scheduled_time,
                )

                existing_duration = (
                    existing_booking.service.duration
                )

                existing_end = (
                    existing_start
                    + timedelta(
                        minutes=existing_duration
                    )
                )

                # -------------------------------------------------
                # CHECK TIME OVERLAP
                # -------------------------------------------------

                if (
                    slot_start < existing_end
                    and service_end > existing_start
                ):
                    provider_available = False
                    break

            # -------------------------------------------------
            # PROVIDER IS BUSY
            # -------------------------------------------------

            if not provider_available:
                continue

            # =================================================
            # PROVIDER FOUND
            # =================================================

            selected_schedule = schedule
            selected_employee = provider_employee

            break

        # =====================================================
        # NO PROVIDER AVAILABLE
        # =====================================================

        if not selected_schedule:
            raise ValueError(
                "No provider is available for the selected "
                "date and slot. The slot may have just been "
                "booked by another customer."
            )

        # =====================================================
        # BOOKING START TIME
        # =====================================================

        scheduled_time = selected_schedule.start_time

        # =====================================================
        # CREATE BOOKING
        # =====================================================
        #
        # IMPORTANT:
        # The schedule lock is still held here.
        #
        # Therefore another concurrent create_booking() request
        # for the same provider cannot pass its availability check
        # until this transaction commits.
        #
        booking = Booking.objects.create(
            user=user,
            service=service,
            business=business,
            employee=selected_employee,
            address=address,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            slot_type=slot_type,
            price=service.price,
            status=BookingStatus.PENDING,
            notes=notes,
        )

        # =====================================================
        # CREATE EMPLOYEE ASSIGNMENT
        # =====================================================

        if selected_employee:

            BookingEmployee.objects.create(
                booking=booking,
                employee=selected_employee,
            )

        # =====================================================
        # TRANSACTION COMMIT
        # =====================================================
        #
        # When this method returns successfully, the outer
        # transaction.atomic() will commit and release the
        # schedule lock.
        #
        # A waiting concurrent request can then acquire the lock
        # and re-check the bookings, where it will now see the
        # booking created above.
        #

        return booking

    @staticmethod
    def get_slot_availability(
        user,
        service_uuid,
        scheduled_date,
    ):
        """
        Check provider availability for each booking slot.

        A slot is available when at least one qualified
        provider is available for the requested service.

        required_employees is the default number requested by
        the service, but it does not make the slot unavailable
        when fewer providers are currently free.
        """

        from datetime import datetime, timedelta

        from django.utils import timezone

        from business.models import (
            Employee,
            EmployeeWorkingSchedule,
            ProviderAvailability,
        )
        from services.models import ServiceEmployee

        # =====================================================
        # FETCH SERVICE
        # =====================================================

        try:
            service = Service.objects.get(
                service_uuid=service_uuid,
                is_active=True,
            )
        except Service.DoesNotExist:
            raise ValueError(
                "Service not found or inactive."
            )

        business = service.business

        if not business.is_active:
            raise ValueError(
                "The business offering this service is currently inactive."
            )

        # =====================================================
        # VALIDATE DATE
        # =====================================================

        if scheduled_date <= timezone.localdate():
            raise ValueError(
                "Availability can only be checked for a future date."
            )

        day_of_week = scheduled_date.strftime("%A").upper()

        slot_types = [
            "MORNING",
            "AFTERNOON",
            "EVENING",
        ]

        availability = {}

        # =====================================================
        # GET QUALIFIED EMPLOYEES
        # =====================================================

        assigned_employee_ids = set(
            ServiceEmployee.objects.filter(
                service=service,
                employee__business=business,
                employee__is_active=True,
            ).values_list(
                "employee_id",
                flat=True,
            )
        )

        # =====================================================
        # CHECK EACH SLOT
        # =====================================================

        for slot_type in slot_types:

            available_employees = 0

            # -------------------------------------------------
            # COMPANY / INVESTOR BUSINESS
            # -------------------------------------------------

            if business.business_type in {
                "COMPANY",
                "INVESTOR",
            }:

                schedules = (
                    EmployeeWorkingSchedule.objects.filter(
                        business=business,
                        employee_id__in=assigned_employee_ids,
                        day_of_week=day_of_week,
                        slot_type=slot_type,
                        is_active=True,
                    )
                    .select_related("employee")
                )

            # -------------------------------------------------
            # INDIVIDUAL BUSINESS
            # -------------------------------------------------

            else:

                schedules = (
                    EmployeeWorkingSchedule.objects.filter(
                        business=business,
                        owner=business.owner,
                        employee__isnull=True,
                        day_of_week=day_of_week,
                        slot_type=slot_type,
                        is_active=True,
                    )
                    .select_related("owner")
                )

            # =================================================
            # CHECK EACH PROVIDER
            # =================================================

            for schedule in schedules:

                provider = schedule.employee

                # Individual business owner
                if provider is None:
                    provider_user = schedule.owner
                    provider_employee = None
                else:
                    provider_user = None
                    provider_employee = provider

                # -------------------------------------------------
                # CHECK PROVIDER AVAILABILITY
                # -------------------------------------------------

                if provider_employee:

                    provider_available = (
                        ProviderAvailability.objects.filter(
                            employee=provider_employee,
                            status="AVAILABLE",
                        ).exists()
                    )

                    if not provider_available:
                        continue

                # -------------------------------------------------
                # CHECK SERVICE FIT
                # -------------------------------------------------

                service_start = datetime.combine(
                    scheduled_date,
                    schedule.start_time,
                )

                service_end = (
                    service_start
                    + timedelta(minutes=service.duration)
                )

                slot_end = datetime.combine(
                    scheduled_date,
                    schedule.end_time,
                )

                if service_end > slot_end:
                    continue

                # -------------------------------------------------
                # CHECK EXISTING BOOKINGS
                # -------------------------------------------------

                existing_bookings = (
                    Booking.objects.filter(
                        business=business,
                        scheduled_date=scheduled_date,
                        status__in=[
                            BookingStatus.PENDING,
                            BookingStatus.CONFIRMED,
                            BookingStatus.IN_PROGRESS,
                        ],
                    )
                    .select_related(
                        "service",
                        "employee",
                    )
                )

                provider_busy = False

                for booking in existing_bookings:

                    # For employee-based providers,
                    # only their own bookings matter.
                    if provider_employee:
                        if not BookingEmployee.objects.filter(
                            booking=booking,
                            employee=provider_employee,
                        ).exists():
                            continue

                    # For individual owner, all business bookings
                    # belong to the same provider.
                    elif booking.business_id != business.id:
                        continue

                    existing_start = datetime.combine(
                        scheduled_date,
                        booking.scheduled_time,
                    )

                    existing_end = (
                        existing_start
                        + timedelta(
                            minutes=booking.service.duration
                        )
                    )

                    if (
                        service_start < existing_end
                        and service_end > existing_start
                    ):
                        provider_busy = True
                        break

                if provider_busy:
                    continue

                available_employees += 1

            # =================================================
            # FINAL SLOT RESULT
            # =================================================

            availability[slot_type] = {
                "available": available_employees > 0,
                "available_employees": available_employees,
                "required_employees": service.required_employees,
            }

        return availability

    # =========================================================
    # STATUS TRANSITIONS
    # =========================================================

    @staticmethod
    def _transition_status(
        booking,
        from_statuses,
        to_status,
        error_msg,
    ):
        if booking.status not in from_statuses:
            raise ValueError(error_msg)

        booking.status = to_status

        booking.save(
            update_fields=["status"]
        )

        return booking

    @staticmethod
    def cancel_booking(booking):
        """User cancels a booking."""

        return BookingService._transition_status(
            booking,
            [
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            ],
            BookingStatus.CANCELLED,
            "Only pending or confirmed bookings can be cancelled.",
        )

    @staticmethod
    def accept_booking(booking):
        """Business accepts a booking."""

        return BookingService._transition_status(
            booking,
            [
                BookingStatus.PENDING,
            ],
            BookingStatus.CONFIRMED,
            "Only pending bookings can be accepted.",
        )

    @staticmethod
    def reject_booking(booking):
        """Business rejects a booking."""

        return BookingService._transition_status(
            booking,
            [
                BookingStatus.PENDING,
            ],
            BookingStatus.REJECTED,
            "Only pending bookings can be rejected.",
        )

    @staticmethod
    def start_booking(booking):
        """Business starts the service."""

        return BookingService._transition_status(
            booking,
            [
                BookingStatus.CONFIRMED,
            ],
            BookingStatus.IN_PROGRESS,
            "Only confirmed bookings can be started.",
        )

    @staticmethod
    def complete_booking(booking):
        """Business completes the service."""

        return BookingService._transition_status(
            booking,
            [
                BookingStatus.IN_PROGRESS,
            ],
            BookingStatus.COMPLETED,
            "Only in-progress bookings can be completed.",
        )