from django.db import transaction
from django.utils import timezone

from PIL import Image, UnidentifiedImageError

from accounts.choices import UserRole

from django.core.exceptions import ValidationError

from .choices import BankVerificationStatus, BusinessApplicationStatus
from .models import (
    BusinessApplication,
    BusinessIdentity,
    BusinessPortfolio,
    BusinessPortfolioFAQ,
    BusinessPortfolioGalleryImage,
    BusinessProfile,
    BusinessUpgradeBankAccount,
    BusinessUpgradeIdentity,
    BusinessUpgradeRequest,
    DeletedBusinessIdentity,
    Employee,
    EmployeeWorkingSchedule,
)

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from accounts.models import EmailTemplate

def has_active_service_in_progress(
    business,
    employees=None,
    exclude_booking_uuid=None,
    exclude_instant_booking_uuid=None,
):
    """
    Return True if the provider(s) who would handle this booking are
    already tied up on another IN_PROGRESS service (scheduled or
    instant).

    - Company/investor business: pass the Employee(s) actually assigned
      to this booking. Only other in-progress work assigned to one of
      these SAME employees counts as a conflict — a different, free
      employee at the same business is not blocked.
    - Individual business (no employees to pass): the owner is the sole
      provider, so any other in-progress booking for the business
      counts as a conflict, matching the availability check already
      used in BookingService.create_booking().
    """
    from bookings.choices import BookingStatus
    from bookings.models import Booking, BookingEmployee
    from instant_bookings.models import InstantBooking, InstantBookingStatus

    employees = list(employees) if employees else []

    scheduled_qs = Booking.objects.filter(
        business=business,
        status=BookingStatus.IN_PROGRESS,
    )
    if exclude_booking_uuid:
        scheduled_qs = scheduled_qs.exclude(uuid=exclude_booking_uuid)

    instant_qs = InstantBooking.objects.filter(
        assigned_business=business,
        status=InstantBookingStatus.IN_PROGRESS,
    )
    if exclude_instant_booking_uuid:
        instant_qs = instant_qs.exclude(
            instant_booking_uuid=exclude_instant_booking_uuid
        )

    if not employees:
        # Individual business - owner is the sole provider.
        return scheduled_qs.exists() or instant_qs.exists()

    # Company / investor business - only THESE employees matter.
    if BookingEmployee.objects.filter(
        booking__in=scheduled_qs,
        employee__in=employees,
    ).exists():
        return True

    return instant_qs.filter(assigned_employee__in=employees).exists()


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

def send_business_email_raw(email, first_name, template_name, placeholders):
    """
    Fetches an EmailTemplate by name, fills in the placeholders,
    and emails the given raw email/first_name. Used when the
    recipient isn't a CustomUser (e.g. an Employee record, which
    has no login account of its own).
    """

    if not email:
        return

    try:
        template = EmailTemplate.objects.get(name=template_name)
    except EmailTemplate.DoesNotExist:
        return

    message = template.message

    for key, value in placeholders.items():
        message = message.replace(
            "{{ " + key + " }}",
            str(value),
        )

    html_message = render_to_string(
        "emails/base_email.html",
        {
            "subject": template.subject,
            "logo_url": settings.EMAIL_LOGO_URL,
            "first_name": first_name,
            "message": message,
            "otp": "",
            "additional_message": "",
        },
    )

    email_message = EmailMultiAlternatives(
        subject=template.subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.attach_alternative(
        html_message,
        "text/html",
    )

    email_message.send(
        fail_silently=True,
    )


def send_business_email(recipient, template_name, placeholders):
    """
    Fetches an EmailTemplate by name, fills in the placeholders,
    and emails the given CustomUser recipient. Same pattern used
    across bookings/services.py and instant_bookings/email_service.py.
    """

    send_business_email_raw(
        recipient.email,
        recipient.first_name,
        template_name,
        placeholders,
    )

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

        send_business_email(
            user,
            "BUSINESS_APPLICATION_RECEIVED",
            {
                "business_type": application.get_business_type_display(),
                "category_name": category.name,
                "location": location,
            },
        )

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

        send_business_email(
            user,
            "BUSINESS_APPLICATION_APPROVED",
            {},
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

        send_business_email(
            user,
            "BUSINESS_APPLICATION_REJECTED",
            {
                "rejection_reason": reason,
            },
        )

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

        send_business_email(
            business.owner,
            "BUSINESS_UPGRADE_SUBMITTED",
            {
                "business_name": business.name,
                "current_business_type": (
                    upgrade_request.get_current_business_type_display()
                ),
                "requested_business_type": (
                    upgrade_request.get_requested_business_type_display()
                ),
            },
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

        send_business_email(
            business.owner,
            "BUSINESS_UPGRADE_APPROVED",
            {
                "business_name": business.name,
                "requested_business_type": (
                    upgrade_request.get_requested_business_type_display()
                ),
            },
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

        send_business_email(
            upgrade_request.business.owner,
            "BUSINESS_UPGRADE_REJECTED",
            {
                "business_name": upgrade_request.business.name,
                "requested_business_type": (
                    upgrade_request.get_requested_business_type_display()
                ),
                "rejection_reason": reason,
            },
        )

        return upgrade_request

class BusinessPortfolioService:
    """
    Handles create/update of a BusinessPortfolio along with its
    nested gallery images and FAQs.
    """

    MAX_GALLERY_IMAGES = 10
    ALLOWED_GALLERY_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
    MAX_FAQ_QUESTION_LENGTH = 255
    MAX_FAQ_ANSWER_LENGTH = 2000

    @staticmethod
    def _validate_gallery_image(image_file):
        """
        Rejects empty uploads and anything whose actual content
        isn't a genuine JPEG/PNG/WEBP image (checked with Pillow,
        not just the filename or declared content-type).
        """
        file_name = getattr(image_file, "name", "file")

        if not image_file or image_file.size == 0:
            raise ValidationError(
                {"gallery_images": f"'{file_name}' is empty. Please upload a valid image."}
            )

        try:
            image_file.seek(0)
            with Image.open(image_file) as img:
                image_format = img.format
                img.verify()
        except Image.DecompressionBombError:
            raise ValidationError(
                {"gallery_images": f"'{file_name}' image dimensions are too large."}
            )
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError(
                {"gallery_images": f"'{file_name}' is not a valid image file."}
            )
        finally:
            image_file.seek(0)

        if image_format not in BusinessPortfolioService.ALLOWED_GALLERY_IMAGE_FORMATS:
            raise ValidationError(
                {
                    "gallery_images": (
                        f"'{file_name}' has an unsupported format ({image_format}). "
                        "Allowed formats: JPEG, PNG, WEBP."
                    )
                }
            )

        return image_file

    @staticmethod
    def _parse_faqs(raw_faqs):
        if not raw_faqs:
            return []

        import json

        try:
            data = json.loads(raw_faqs)
        except (TypeError, ValueError):
            raise ValidationError(
                {"faqs": "faqs must be valid JSON: a list of {question, answer}."}
            )

        if not isinstance(data, list):
            raise ValidationError(
                {"faqs": "faqs must be a JSON list."}
            )

        cleaned = []
        seen_questions = set()

        for index, item in enumerate(data):
            question = (item or {}).get("question", "").strip()
            answer = (item or {}).get("answer", "").strip()

            if not question or not answer:
                raise ValidationError(
                    {"faqs": f"Item {index} must have both question and answer."}
                )

            if len(question) > BusinessPortfolioService.MAX_FAQ_QUESTION_LENGTH:
                raise ValidationError(
                    {
                        "faqs": (
                            f"Item {index}: question must be at most "
                            f"{BusinessPortfolioService.MAX_FAQ_QUESTION_LENGTH} characters "
                            f"(got {len(question)})."
                        )
                    }
                )

            if len(answer) > BusinessPortfolioService.MAX_FAQ_ANSWER_LENGTH:
                raise ValidationError(
                    {
                        "faqs": (
                            f"Item {index}: answer must be at most "
                            f"{BusinessPortfolioService.MAX_FAQ_ANSWER_LENGTH} characters "
                            f"(got {len(answer)})."
                        )
                    }
                )

            normalized_question = question.lower()

            if normalized_question in seen_questions:
                raise ValidationError(
                    {"faqs": f"Duplicate question found: '{question}'."}
                )

            seen_questions.add(normalized_question)

            cleaned.append(
                {
                    "question": question,
                    "answer": answer,
                    "order": index,
                }
            )

        return cleaned

    @classmethod
    @transaction.atomic
    def create_portfolio(cls, business, validated_data, gallery_files, raw_faqs):
        faqs = cls._parse_faqs(raw_faqs)

        if len(gallery_files) > cls.MAX_GALLERY_IMAGES:
            raise ValidationError(
                {"gallery_images": f"Maximum {cls.MAX_GALLERY_IMAGES} images allowed."}
            )

        for image_file in gallery_files:
            cls._validate_gallery_image(image_file)

        portfolio = BusinessPortfolio.objects.create(
            business=business,
            **validated_data,
        )

        for image_file in gallery_files:
            BusinessPortfolioGalleryImage.objects.create(
                portfolio=portfolio,
                image=image_file,
            )

        for faq in faqs:
            BusinessPortfolioFAQ.objects.create(
                portfolio=portfolio,
                **faq,
            )

        return portfolio

    @classmethod
    @transaction.atomic
    def update_portfolio(cls, portfolio, validated_data, gallery_files, raw_faqs):
        existing_count = portfolio.gallery_images.count()

        if existing_count + len(gallery_files) > cls.MAX_GALLERY_IMAGES:
            raise ValidationError(
                {"gallery_images": f"Maximum {cls.MAX_GALLERY_IMAGES} images allowed in total."}
            )

        for image_file in gallery_files:
            cls._validate_gallery_image(image_file)

        for field, value in validated_data.items():
            setattr(portfolio, field, value)
        portfolio.save()

        for image_file in gallery_files:
            BusinessPortfolioGalleryImage.objects.create(
                portfolio=portfolio,
                image=image_file,
            )

        if raw_faqs:
            faqs = cls._parse_faqs(raw_faqs)
            portfolio.faqs.all().delete()
            for faq in faqs:
                BusinessPortfolioFAQ.objects.create(
                    portfolio=portfolio,
                    **faq,
                )

        return portfolio


class BusinessDeletionService:
    """
    Shared logic for tearing down a BusinessProfile, used by both:
      - full account deletion (a BUSINESS-role user deletes their
        whole account), via accounts.services.account_deletion
      - business switch-to-user (owner keeps their account, drops
        the business), via BusinessSwitchToUserService below

    Bookings/employees/provider working schedules are intentionally
    left untouched — they stay in the DB exactly as-is, and will
    display under the business's new "Deleted_Business" name since
    they're linked to it by foreign key.
    """

    RENAMED_BUSINESS_NAME = "Deleted_Business"

    @staticmethod
    def has_blocking_bookings(business):
        """
        True if the business has any scheduled OR instant booking
        that is still pending, confirmed/assigned, or in progress.
        """
        from bookings.choices import BookingStatus
        from bookings.models import Booking
        from instant_bookings.models import (
            InstantBooking,
            InstantBookingStatus,
        )

        scheduled_blocked = Booking.objects.filter(
            business=business,
            status__in=[
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
                BookingStatus.IN_PROGRESS,
            ],
        ).exists()

        if scheduled_blocked:
            return True

        instant_blocking_statuses = [
            InstantBookingStatus.ASSIGNED,
            InstantBookingStatus.IN_PROGRESS,
        ]

        return InstantBooking.objects.filter(
            assigned_business=business,
            status__in=instant_blocking_statuses,
        ).exists()
    @staticmethod
    def _snapshot_identity(identity):
        return {
            "pan_number": identity.pan_number,
            "pan_document_name": identity.pan_document_name,
            "pan_document_type": identity.pan_document_type,
            "aadhaar_number": identity.aadhaar_number,
            "aadhaar_document_name": identity.aadhaar_document_name,
            "aadhaar_document_type": identity.aadhaar_document_type,
            "gst_number": identity.gst_number,
            "udyam_number": identity.udyam_number,
            "labour_license_number": identity.labour_license_number,
            "bbmp_license_number": identity.bbmp_license_number,
            "food_license_number": identity.food_license_number,
            "internal_store_name": identity.internal_store_name,
            "internal_store_type": identity.internal_store_type,
            "external_store_name": identity.external_store_name,
            "external_store_type": identity.external_store_type,
            "cancelled_gst_bill_book_name": (
                identity.cancelled_gst_bill_book_name
            ),
            "cancelled_gst_bill_book_type": (
                identity.cancelled_gst_bill_book_type
            ),
            "logo_name": identity.logo_name,
            "logo_type": identity.logo_type,
            "website": identity.website,
        }

    @classmethod
    def archive_and_remove_identity(cls, business):
        """
        Copies the business's current BusinessIdentity into
        DeletedBusinessIdentity, then deletes the original row.
        No-op if the business has no identity on file.
        """
        identity = get_current_business_identity(business)

        if identity is None:
            return None

        deleted_identity = DeletedBusinessIdentity.objects.create(
            original_business_identity_uuid=(
                identity.business_identity_uuid
            ),
            original_business_application_id=identity.application_id,
            business_profile_uuid=business.business_profile_uuid,
            owner_user_uuid=business.owner.user_uuid,
            business_name=business.name,
            business_type=business.business_type,
            identity_data=cls._snapshot_identity(identity),
        )

        identity.delete()

        return deleted_identity

    @classmethod
    def deactivate_related(cls, business):
        """
        Renames the business, deactivates it, its portfolio, its
        reviews and its service cards. Employees, working
        schedules and bookings are left untouched.
        """
        business.name = cls.RENAMED_BUSINESS_NAME
        business.is_active = False
        business.save(
            update_fields=["name", "is_active", "updated_at"]
        )

        portfolio = getattr(business, "portfolio", None)

        if portfolio is not None:
            portfolio.is_active = False
            portfolio.save(
                update_fields=["is_active", "updated_at"]
            )

        from reviews.models import Review

        Review.objects.filter(business=business).update(
            is_active=False
        )

        from services.models import Service

        Service.objects.filter(business=business).update(
            is_active=False
        )

    @classmethod
    @transaction.atomic
    def delete_business(cls, business):
        cls.archive_and_remove_identity(business)
        cls.deactivate_related(business)

        return business


class BusinessSwitchToUserService:
    """
    Downgrades a BUSINESS-role owner to a plain USER, deleting
    their business profile the same way BusinessDeletionService
    does, without touching the CustomUser account itself.
    """

    @classmethod
    @transaction.atomic
    def switch_to_user(cls, business):
        user = business.owner

        BusinessDeletionService.delete_business(business)

        user.role = UserRole.USER
        user.has_business = False
        user.business_verified = False

        user.save(
            update_fields=[
                "role",
                "has_business",
                "business_verified",
                "updated_at",
            ]
        )

        return user



