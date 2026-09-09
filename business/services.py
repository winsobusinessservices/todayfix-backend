from django.db import transaction
from django.utils import timezone

from accounts.choices import UserRole

from .choices import BusinessApplicationStatus
from .models import BusinessApplication, BusinessIdentity, BusinessProfile


def get_current_business_identity(business):
    """
    Return the BusinessIdentity currently on file for an approved
    BusinessProfile, or None if somehow missing.

    BusinessIdentity is stored against the original BusinessApplication,
    not directly against BusinessProfile, so we trace back through the
    owner's most recent APPROVED application.
    """
    application = (
        BusinessApplication.objects
        .filter(
            user=business.owner,
            status=BusinessApplicationStatus.APPROVED,
        )
        .order_by("-reviewed_at", "-created_at")
        .first()
    )

    if application is None:
        return None

    try:
        return application.identity
    except BusinessIdentity.DoesNotExist:
        return None




class BusinessApplicationService:

    @staticmethod
    def submit(user, business_type, location, category):
        # USER ROLE CHECK
        if getattr(user, "role", None) != UserRole.USER:
            raise ValueError(
                "Only USER accounts can submit "
                "a business application."
            )

        # PENDING APPLICATION CHECK
        if BusinessApplication.objects.filter(
            user=user,
            status=BusinessApplicationStatus.PENDING,
        ).exists():
            raise ValueError(
                "You already have a pending "
                "business application."
            )

        # CREATE APPLICATION
        application = BusinessApplication(
            user=user,
            business_type=business_type,
            location=location,
            category=category,
            status=BusinessApplicationStatus.PENDING,
        )

        application.full_clean()
        application.save()

        user.has_business = True
        user.business_verified = False
        user.save(update_fields=["has_business", "business_verified"])

        return application

    # =====================================================
    # APPROVE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def approve(application, admin_user):

        if (
            application.status
            != BusinessApplicationStatus.PENDING
        ):
            raise ValueError(
                "Only pending applications "
                "can be approved."
            )

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

        identity.full_clean()
        bank_account.full_clean()

        user = application.user

        if user.role != UserRole.USER:
            raise ValueError(
                "Only USER accounts can be "
                "converted to BUSINESS."
            )

        user.role = UserRole.BUSINESS
        user.has_business = True
        user.business_verified = True
        user.save(update_fields=["role", "has_business", "business_verified"])

        application.status = (
            BusinessApplicationStatus.APPROVED
        )

        application.reviewed_by = admin_user
        application.reviewed_at = timezone.now()
        application.rejection_reason = ""

        application.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        profile, created = (
            BusinessProfile.objects.get_or_create(
                owner=user,
                business_type=application.business_type,
                defaults={
                    "category": application.category,
                    "location": application.location,
                    "name": (
                        f"{user.first_name} {user.last_name}".strip()
                        or user.email
                    ),
                    "email": user.email or "",
                    "phone": user.phone or "",
                    "website": identity.website,
                },
            )
        )

        if not created:
            profile.category = application.category
            profile.location = application.location
            profile.save(update_fields=["category", "location", "updated_at"])



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

        if (
            application.status
            != BusinessApplicationStatus.PENDING
        ):
            raise ValueError(
                "Only pending applications "
                "can be rejected."
            )

        reason = (reason or "").strip()

        if not reason:
            raise ValueError(
                "A rejection reason is required "
                "when rejecting an application."
            )

        application.status = (
            BusinessApplicationStatus.REJECTED
        )

        application.reviewed_by = admin_user
        application.reviewed_at = timezone.now()
        application.rejection_reason = reason

        application.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        user = application.user
        user.has_business = True
        user.business_verified = False
        user.save(update_fields=["has_business", "business_verified"])

        return application

class BusinessUpgradeService:
    """
    Handles submitting, approving, and rejecting requests to
    change a BusinessProfile's business_type.
    """

    # =====================================================
    # SUBMIT
    # =====================================================

    @staticmethod
    def submit(business, validated_data):

        # ONE PENDING REQUEST PER BUSINESS
        if BusinessUpgradeRequest.objects.filter(
            business=business,
            status=BusinessApplicationStatus.PENDING,
        ).exists():
            raise ValueError(
                "This business already has a pending "
                "upgrade request."
            )

        upgrade_request = BusinessUpgradeRequest(
            business=business,
            current_business_type=business.business_type,
            requested_business_type=validated_data[
                "requested_business_type"
            ],
            keep_employees_and_schedules=validated_data.get(
                "keep_employees_and_schedules"
            ),
            bank_details_changed=validated_data.get(
                "bank_details_changed", False
            ),
            status=BusinessApplicationStatus.PENDING,
        )

        upgrade_request.full_clean()
        upgrade_request.save()

        pan_document = validated_data.get("pan_document")
        aadhaar_document = validated_data.get("aadhaar_document")
        internal_store_photo = validated_data.get(
            "internal_store_photo"
        )
        external_store_photo = validated_data.get(
            "external_store_photo"
        )
        cancelled_gst_bill_book_photo = validated_data.get(
            "cancelled_gst_bill_book_photo"
        )

        BusinessUpgradeIdentity.objects.create(
            request=upgrade_request,
            pan_number=validated_data.get("pan_number", ""),
            pan_document=(
                pan_document if pan_document else None
            ),
            aadhaar_number=validated_data.get(
                "aadhaar_number", ""
            ),
            aadhaar_document=(
                aadhaar_document if aadhaar_document else None
            ),
            gst_number=validated_data.get("gst_number", ""),
            udyam_number=validated_data.get("udyam_number", ""),
            labour_license_number=validated_data.get(
                "labour_license_number", ""
            ),
            bbmp_license_number=validated_data.get(
                "bbmp_license_number", ""
            ),
            food_license_number=validated_data.get(
                "food_license_number", ""
            ),
            internal_store_photo=(
                internal_store_photo
                if internal_store_photo
                else None
            ),
            external_store_photo=(
                external_store_photo
                if external_store_photo
                else None
            ),
            cancelled_gst_bill_book_photo=(
                cancelled_gst_bill_book_photo
                if cancelled_gst_bill_book_photo
                else None
            ),
        )

        if validated_data.get("bank_details_changed"):
            BusinessUpgradeBankAccount.objects.create(
                request=upgrade_request,
                account_holder_name=validated_data[
                    "account_holder_name"
                ],
                account_number=validated_data[
                    "account_number"
                ],
                ifsc_code=validated_data["ifsc_code"],
                bank_name=validated_data["bank_name"],
                branch_name=validated_data.get(
                    "branch_name", ""
                ),
            )

        return upgrade_request

    # =====================================================
    # APPROVE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def approve(upgrade_request, admin_user):

        if (
            upgrade_request.status
            != BusinessApplicationStatus.PENDING
        ):
            raise ValueError(
                "Only pending upgrade requests "
                "can be approved."
            )

        business = upgrade_request.business

        if (
            business.business_type
            != upgrade_request.current_business_type
        ):
            raise ValueError(
                "This business's type has changed since "
                "this request was submitted. Please reject "
                "this request and ask the owner to resubmit."
            )

        current_identity = get_current_business_identity(
            business
        )

        if current_identity is None:
            raise ValueError(
                "Cannot approve: no existing identity "
                "record found for this business."
            )

        upgrade_identity = getattr(
            upgrade_request, "identity", None
        )

        # -------------------------------------------------
        # MERGE new identity fields into the existing record.
        # Only fields that were actually submitted are
        # overwritten; everything else stays as-is.
        # -------------------------------------------------

        if upgrade_identity:

            if upgrade_identity.pan_number:
                current_identity.pan_number = (
                    upgrade_identity.pan_number
                )
            if upgrade_identity.pan_document:
                current_identity.pan_document = (
                    upgrade_identity.pan_document
                )
            if upgrade_identity.aadhaar_number:
                current_identity.aadhaar_number = (
                    upgrade_identity.aadhaar_number
                )
            if upgrade_identity.aadhaar_document:
                current_identity.aadhaar_document = (
                    upgrade_identity.aadhaar_document
                )
            if upgrade_identity.gst_number:
                current_identity.gst_number = (
                    upgrade_identity.gst_number
                )
            if upgrade_identity.udyam_number:
                current_identity.udyam_number = (
                    upgrade_identity.udyam_number
                )
            if upgrade_identity.labour_license_number:
                current_identity.labour_license_number = (
                    upgrade_identity.labour_license_number
                )
            if upgrade_identity.bbmp_license_number:
                current_identity.bbmp_license_number = (
                    upgrade_identity.bbmp_license_number
                )
            if upgrade_identity.food_license_number:
                current_identity.food_license_number = (
                    upgrade_identity.food_license_number
                )
            if upgrade_identity.internal_store_photo:
                current_identity.internal_store_photo = (
                    upgrade_identity.internal_store_photo
                )
            if upgrade_identity.external_store_photo:
                current_identity.external_store_photo = (
                    upgrade_identity.external_store_photo
                )
            if upgrade_identity.cancelled_gst_bill_book_photo:
                current_identity.cancelled_gst_bill_book_photo = (
                    upgrade_identity.cancelled_gst_bill_book_photo
                )

            current_identity.full_clean()
            current_identity.save()

        # -------------------------------------------------
        # BANK DETAILS
        # -------------------------------------------------

        if upgrade_request.bank_details_changed:

            upgrade_bank = getattr(
                upgrade_request, "bank_account", None
            )

            if upgrade_bank is None:
                raise ValueError(
                    "bank_details_changed is set but no "
                    "new bank details were submitted with "
                    "this request."
                )

            application = (
                BusinessApplication.objects
                .filter(
                    user=business.owner,
                    status=BusinessApplicationStatus.APPROVED,
                )
                .order_by("-reviewed_at", "-created_at")
                .first()
            )

            current_bank = (
                getattr(application, "bank_account", None)
                if application
                else None
            )

            if current_bank is None:
                raise ValueError(
                    "Cannot approve: no existing bank "
                    "account record found for this business."
                )

            current_bank.account_holder_name = (
                upgrade_bank.account_holder_name
            )
            current_bank.account_number = (
                upgrade_bank.account_number
            )
            current_bank.ifsc_code = upgrade_bank.ifsc_code
            current_bank.bank_name = upgrade_bank.bank_name
            current_bank.branch_name = (
                upgrade_bank.branch_name
            )
            current_bank.verification_status = (
                BankVerificationStatus.PENDING
            )
            current_bank.verified_by = None
            current_bank.verified_at = None

            current_bank.full_clean()
            current_bank.save()

        # -------------------------------------------------
        # EMPLOYEES / SCHEDULES
        # -------------------------------------------------

        if (
            upgrade_request.keep_employees_and_schedules
            is False
        ):
            Employee.objects.filter(
                business=business,
                is_active=True,
            ).update(is_active=False)

            EmployeeWorkingSchedule.objects.filter(
                business=business,
                is_active=True,
            ).update(is_active=False)

        # -------------------------------------------------
        # APPLY THE TYPE CHANGE
        # -------------------------------------------------

        business.business_type = (
            upgrade_request.requested_business_type
        )
        business.full_clean()
        business.save(
            update_fields=["business_type", "updated_at"]
        )

        upgrade_request.status = (
            BusinessApplicationStatus.APPROVED
        )
        upgrade_request.reviewed_by = admin_user
        upgrade_request.reviewed_at = timezone.now()
        upgrade_request.rejection_reason = ""

        upgrade_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        return upgrade_request, business

    # =====================================================
    # REJECT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def reject(upgrade_request, admin_user, reason):

        if (
            upgrade_request.status
            != BusinessApplicationStatus.PENDING
        ):
            raise ValueError(
                "Only pending upgrade requests "
                "can be rejected."
            )

        reason = (reason or "").strip()

        if not reason:
            raise ValueError(
                "A rejection reason is required when "
                "rejecting an upgrade request."
            )

        upgrade_request.status = (
            BusinessApplicationStatus.REJECTED
        )
        upgrade_request.reviewed_by = admin_user
        upgrade_request.reviewed_at = timezone.now()
        upgrade_request.rejection_reason = reason

        upgrade_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            ]
        )

        return upgrade_request


