from django.db import transaction
from django.utils import timezone

from accounts.choices import UserRole

from .choices import (
    BusinessApplicationStatus,
)
from .models import (
    BusinessApplication,
    BusinessProfile,
)


class BusinessApplicationService:

    @staticmethod
    def submit(user, business_type):

        # =================================================
        # USER ROLE CHECK
        # =================================================

        if getattr(user, "role", None) != UserRole.USER:
            raise ValueError(
                "Only USER accounts can submit "
                "a business application."
            )

        # =================================================
        # PENDING APPLICATION CHECK
        # =================================================

        if BusinessApplication.objects.filter(
            user=user,
            status=BusinessApplicationStatus.PENDING,
        ).exists():

            raise ValueError(
                "You already have a pending "
                "business application."
            )

        # =================================================
        # CREATE APPLICATION
        # =================================================

        application = BusinessApplication(
            user=user,
            business_type=business_type,
            status=BusinessApplicationStatus.PENDING,
        )

        application.full_clean()
        application.save()

        return application

    # =====================================================
    # APPROVE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def approve(
        application,
        admin_user,
    ):

        # -------------------------------------------------
        # STATUS CHECK
        # -------------------------------------------------

        if (
            application.status
            != BusinessApplicationStatus.PENDING
        ):
            raise ValueError(
                "Only pending applications "
                "can be approved."
            )

        # -------------------------------------------------
        # REQUIRED DATA CHECK
        # -------------------------------------------------

        identity = getattr(
            application,
            "identity",
            None,
        )

        bank_account = getattr(
            application,
            "bank_account",
            None,
        )

        if identity is None:
            raise ValueError(
                "Business identity information "
                "is missing."
            )

        if bank_account is None:
            raise ValueError(
                "Bank account information "
                "is missing."
            )

        # -------------------------------------------------
        # FINAL MODEL VALIDATION
        # -------------------------------------------------

        identity.full_clean()
        bank_account.full_clean()

        # -------------------------------------------------
        # USER ROLE
        # -------------------------------------------------

        user = application.user

        if user.role != UserRole.USER:
            raise ValueError(
                "Only USER accounts can be "
                "converted to BUSINESS."
            )

        # -------------------------------------------------
        # CHANGE USER ROLE
        # -------------------------------------------------

        user.role = UserRole.BUSINESS

        user.save(
            update_fields=["role"]
        )

        # -------------------------------------------------
        # APPROVE APPLICATION
        # -------------------------------------------------

        application.status = (
            BusinessApplicationStatus.APPROVED
        )

        application.reviewed_by = admin_user

        application.reviewed_at = (
            timezone.now()
        )

        application.rejection_reason = ""

        application.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        # -------------------------------------------------
        # CREATE BUSINESS PROFILE
        # -------------------------------------------------

        profile, created = (
            BusinessProfile.objects.get_or_create(
                owner=user,
                business_type=(
                    application.business_type
                ),
                defaults={
                    "name": (
                        getattr(
                            user,
                            "name",
                            None,
                        )
                        or user.email
                    ),
                    "email": getattr(
                        user,
                        "email",
                        "",
                    ),
                    "phone": getattr(
                        user,
                        "phone",
                        "",
                    ),
                    "website": (
                        identity.website
                    ),
                },
            )
        )

        return application, profile

    # =====================================================
    # REJECT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def reject(
        application,
        admin_user,
        reason,
    ):

        # -------------------------------------------------
        # STATUS CHECK
        # -------------------------------------------------

        if (
            application.status
            != BusinessApplicationStatus.PENDING
        ):
            raise ValueError(
                "Only pending applications "
                "can be rejected."
            )

        # -------------------------------------------------
        # REASON CHECK
        # -------------------------------------------------

        reason = (
            reason or ""
        ).strip()

        if not reason:
            raise ValueError(
                "A rejection reason is required "
                "when rejecting an application."
            )

        # -------------------------------------------------
        # UPDATE APPLICATION
        # -------------------------------------------------

        application.status = (
            BusinessApplicationStatus.REJECTED
        )

        application.reviewed_by = admin_user

        application.reviewed_at = (
            timezone.now()
        )

        application.rejection_reason = reason

        application.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        return application

        