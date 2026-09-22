from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import (
    AccountDeletionRequest,
    DeletedUser,
)
from bookings.models import Booking
from bookings.choices import BookingStatus


class PaymentClearanceService:
    """
    Payment integration point for account deletion.

    Payment functionality is not implemented in the current
    project, so there are currently no payment records to block
    deletion.

    When payments are introduced, this method must check the
    actual payment models before returning True.
    """

    @staticmethod
    def are_all_payments_cleared(user):
        return True


class AccountDeletionService:

    # ------------------------------------------------------------
    # TEMPORARY TEST VALUES — REVERT BEFORE PRODUCTION / real QA
    # Original production values:
    #   GRACE_PERIOD_DAYS     = 30
    #   EXTENSION_PERIOD_DAYS = 5
    # ------------------------------------------------------------
    GRACE_PERIOD = timedelta(minutes=3)
    EXTENSION_PERIOD = timedelta(minutes=1)

    @classmethod
    def get_active_request(cls, user):
        return AccountDeletionRequest.objects.filter(
            user=user,
            status__in=[
                AccountDeletionRequest.STATUS_PENDING,
                AccountDeletionRequest.STATUS_ON_HOLD,
            ],
        ).first()

    @classmethod
    def has_incomplete_bookings(cls, user):
        if Booking.objects.filter(
            user=user,
        ).exclude(
            status=BookingStatus.COMPLETED,
        ).exists():
            return True

        if getattr(user, "role", None) == "BUSINESS":
            from business.models import BusinessProfile
            from business.services import BusinessDeletionService

            business = BusinessProfile.objects.filter(
                owner=user,
                is_active=True,
            ).first()

            if business and BusinessDeletionService.has_blocking_bookings(
                business
            ):
                return True

        return False

    @classmethod
    def are_conditions_clear(cls, user):
        return (
            not cls.has_incomplete_bookings(user)
            and PaymentClearanceService.are_all_payments_cleared(user)
        )

    @classmethod
    @transaction.atomic
    def create_request(cls, user):
        existing_request = cls.get_active_request(user)

        if existing_request:
            return existing_request

        now = timezone.now()

        # `AccountDeletionRequest.user` is a OneToOneField, so a
        # user can only ever have a single row. If they previously
        # cancelled (or otherwise ended) a request, that row still
        # exists - reset it instead of inserting a new one, or the
        # unique constraint on user_id raises an IntegrityError.
        previous_request = AccountDeletionRequest.objects.filter(
            user=user,
        ).first()

        if previous_request:
            previous_request.status = (
                AccountDeletionRequest.STATUS_PENDING
            )
            previous_request.scheduled_deletion_at = (
                now + cls.GRACE_PERIOD
            )
            previous_request.hold_started_at = None
            previous_request.extension_deadline = None
            previous_request.condition_cleared_at = None
            previous_request.completed_at = None
            previous_request.cancelled_at = None
            previous_request.cancellation_reason = ""

            previous_request.save(
                update_fields=[
                    "status",
                    "scheduled_deletion_at",
                    "hold_started_at",
                    "extension_deadline",
                    "condition_cleared_at",
                    "completed_at",
                    "cancelled_at",
                    "cancellation_reason",
                ]
            )

            return previous_request

        return AccountDeletionRequest.objects.create(
            user=user,
            status=AccountDeletionRequest.STATUS_PENDING,
            scheduled_deletion_at=(
                now + cls.GRACE_PERIOD
            ),
        )

    @classmethod
    @transaction.atomic
    def cancel_request(cls, user):
        deletion_request = cls.get_active_request(user)

        if not deletion_request:
            return None

        deletion_request.status = (
            AccountDeletionRequest.STATUS_CANCELLED
        )
        deletion_request.cancelled_at = timezone.now()
        deletion_request.cancellation_reason = (
            "Cancelled by user."
        )

        deletion_request.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancellation_reason",
            ]
        )

        return deletion_request

    @classmethod
    def put_on_hold(cls, deletion_request):
        now = timezone.now()

        deletion_request.status = (
            AccountDeletionRequest.STATUS_ON_HOLD
        )
        deletion_request.hold_started_at = now
        deletion_request.extension_deadline = (
            now + cls.EXTENSION_PERIOD
        )

        deletion_request.save(
            update_fields=[
                "status",
                "hold_started_at",
                "extension_deadline",
            ]
        )

        return deletion_request

    @classmethod
    def mark_conditions_cleared(cls, deletion_request):
        now = timezone.now()

        deletion_request.condition_cleared_at = now
        deletion_request.extension_deadline = (
            now + cls.EXTENSION_PERIOD
        )

        deletion_request.save(
            update_fields=[
                "condition_cleared_at",
                "extension_deadline",
            ]
        )

        return deletion_request

    @classmethod
    @transaction.atomic
    def finalize_deletion(cls, deletion_request):
        user = deletion_request.user

        if not cls.are_conditions_clear(user):
            return False

        is_business_account = (
            getattr(user, "role", None) == "BUSINESS"
        )

        if is_business_account:
            from business.models import BusinessProfile
            from business.services import BusinessDeletionService

            business = BusinessProfile.objects.filter(
                owner=user,
                is_active=True,
            ).first()

            if business:
                BusinessDeletionService.delete_business(business)

        DeletedUser.objects.create(
            original_user_uuid=user.user_uuid,
            original_user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            has_business=user.has_business,
            business_verified=user.business_verified,
            is_verified=user.is_verified,
            verified_at=user.verified_at,
            created_at=user.created_at,
            account_data={
                "user_uuid": str(user.user_uuid),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "has_business": user.has_business,
                "business_verified": user.business_verified,
                "is_verified": user.is_verified,
                "verified_at": (
                    user.verified_at.isoformat()
                    if user.verified_at
                    else None
                ),
                "created_at": (
                    user.created_at.isoformat()
                    if user.created_at
                    else None
                ),
            },
        )

        user.first_name = (
            "Deleted" if is_business_account else "Deleted"
        )
        user.last_name = (
            "Business" if is_business_account else "User"
        )
        user.email = None
        user.phone = None
        user.profile_picture = None
        user.is_active = False
        user.is_verified = False
        user.has_business = False
        user.business_verified = False
        user.verified_at = None
        user.last_logout = timezone.now()
        user.set_unusable_password()

        user.save(
            update_fields=[
                "first_name",
                "last_name",
                "email",
                "phone",
                "profile_picture",
                "is_active",
                "is_verified",
                "has_business",
                "business_verified",
                "verified_at",
                "last_logout",
                "password",
                "updated_at",
            ]
        )

        deletion_request.status = (
            AccountDeletionRequest.STATUS_COMPLETED
        )
        deletion_request.completed_at = timezone.now()

        deletion_request.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        return True