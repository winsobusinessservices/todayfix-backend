import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models.base import TimeStampedModel

from .choices import (
    BankVerificationStatus,
    BusinessApplicationStatus,
    BusinessType,
    EmployeeAvailabilityStatus,
    DayOfWeek,
)
from categories.models import Category, SubCategory

class BusinessApplication(TimeStampedModel):
    """
    Application submitted by a USER to become BUSINESS.

    The application contains the complete business verification
    information and remains pending until an ADMIN approves it.
    """

    business_application_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_applications",
    )

    business_type = models.CharField(
        max_length=20,
        choices=BusinessType.choices,
        db_index=True,
    )

    location = models.CharField(
        max_length=255,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="business_applications",
        db_index=True,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=BusinessApplicationStatus.choices,
        default=BusinessApplicationStatus.PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_business_applications",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(
                    status=BusinessApplicationStatus.PENDING
                ),
                name="unique_pending_business_application",
            )
        ]

    def clean(self):
        super().clean()

        if self.user_id:
            user_role = getattr(self.user, "role", None)

            if user_role != "USER":
                raise ValidationError(
                    {
                        "user": (
                            "Only USER accounts can submit "
                            "a business application."
                        )
                    }
                )

        if self.business_type not in BusinessType.values:
            raise ValidationError(
                {
                    "business_type": (
                        "Invalid business type."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.business_application_uuid} - "
            f"{self.user.email} - "
            f"{self.business_type} - "
            f"{self.status}"
        )


class BusinessIdentity(TimeStampedModel):
    """
    Complete identity and business verification information.

    This information belongs to a BusinessApplication.
    """

    business_identity_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    application = models.OneToOneField(
        BusinessApplication,
        on_delete=models.CASCADE,
        related_name="identity",
    )

    # =====================================================
    # PAN
    # =====================================================

    pan_number = models.CharField(
        max_length=10,
        blank=True,
        default="",
    )

    pan_document = models.FileField(
        upload_to="business_applications/pan/",
        null=True,
        blank=True,
    )

    pan_document_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    pan_document_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # AADHAAR
    # =====================================================

    aadhaar_number = models.CharField(
        max_length=12,
        blank=True,
        default="",
    )

    aadhaar_document = models.FileField(
        upload_to="business_applications/aadhaar/",
        null=True,
        blank=True,
    )

    aadhaar_document_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    aadhaar_document_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # BUSINESS REGISTRATION
    # =====================================================

    gst_number = models.CharField(
        max_length=15,
        blank=True,
        default="",
    )

    udyam_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    labour_license_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    bbmp_license_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    food_license_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # STORE PHOTOS
    # =====================================================

    internal_store_photo  = models.FileField(
        upload_to="business_applications/store/internal/",
        null=True,
        blank=True,
    )

    internal_store_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    internal_store_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    external_store_photo = models.FileField(
        upload_to="business_applications/store/external/",
        null=True,
        blank=True,
    )

    external_store_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    external_store_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    cancelled_gst_bill_book_photo = models.FileField(
        upload_to="business_applications/gst_bill_book/",
        null=True,
        blank=True,
    )

    cancelled_gst_bill_book_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    cancelled_gst_bill_book_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # OPTIONAL
    # =====================================================

    logo = models.FileField(
        upload_to="business_applications/logo/",
        null=True,
        blank=True,
    )

    logo_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    logo_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    website = models.URLField(
        blank=True,
        default="",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["pan_number"]
            ),
            models.Index(
                fields=["gst_number"]
            ),
        ]

    def clean(self):
        super().clean()

        if not self.application_id:
            return

        business_type = self.application.business_type

        errors = {}

        # =================================================
        # INDIVIDUAL
        # =================================================

        if business_type == BusinessType.INDIVIDUAL:

            has_pan = bool(
                self.pan_number and self.pan_document
            )

            has_aadhaar = bool(
                self.aadhaar_number
                and self.aadhaar_document
            )

            if not has_pan and not has_aadhaar:
                errors["identity"] = (
                    "At least one complete identity "
                    "document is required: PAN or Aadhaar."
                )

        # =================================================
        # COMPANY / INVESTOR
        # =================================================

        elif business_type in {
            BusinessType.COMPANY,
            BusinessType.INVESTOR,
        }:

            # PAN
            if not self.pan_number:
                errors["pan_number"] = (
                    "PAN number is required."
                )

            if not self.pan_document:
                errors["pan_document"] = (
                    "PAN document is required."
                )

            # Aadhaar
            if not self.aadhaar_number:
                errors["aadhaar_number"] = (
                    "Aadhaar number is required."
                )

            if not self.aadhaar_document:
                errors["aadhaar_document"] = (
                    "Aadhaar document is required."
                )

            # At least one registration number
            has_registration = any(
                [
                    self.gst_number,
                    self.udyam_number,
                    self.labour_license_number,
                    self.bbmp_license_number,
                    self.food_license_number,
                ]
            )

            if not has_registration:
                errors["business_registration"] = (
                    "At least one of GST, Udyam, "
                    "Labour License, BBMP License, "
                    "or Food License is required."
                )

            # Mandatory store documents
            if not self.internal_store_photo:
                errors["internal_store_photo"] = (
                    "Internal store photo is required."
                )

            if not self.external_store_photo:
                errors["external_store_photo"] = (
                    "External store photo is required."
                )

            if not self.cancelled_gst_bill_book_photo:
                errors[
                    "cancelled_gst_bill_book_photo"
                ] = (
                    "Cancelled GST bill/book photo "
                    "is required."
                )

        # =================================================
        # PAN FORMAT
        # =================================================

        if self.pan_number:

            pan = (
                self.pan_number
                .strip()
                .upper()
            )

            if not (
                len(pan) == 10
                and pan[:5].isalpha()
                and pan[5:9].isdigit()
                and pan[9].isalpha()
            ):
                errors["pan_number"] = (
                    "Enter a valid PAN format."
                )
            else:
                self.pan_number = pan

        # =================================================
        # AADHAAR FORMAT
        # =================================================

        if self.aadhaar_number:

            aadhaar = (
                self.aadhaar_number
                .strip()
                .replace(" ", "")
            )

            if (
                len(aadhaar) != 12
                or not aadhaar.isdigit()
            ):
                errors["aadhaar_number"] = (
                    "Aadhaar must contain exactly "
                    "12 digits."
                )
            else:
                self.aadhaar_number = aadhaar

        # =================================================
        # GST FORMAT
        # =================================================

        if self.gst_number:

            gst = (
                self.gst_number
                .strip()
                .upper()
            )

            if len(gst) != 15:
                errors["gst_number"] = (
                    "GST number must contain exactly "
                    "15 characters."
                )
            else:
                self.gst_number = gst

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"Identity - "
            f"{self.application.business_application_uuid}"
        )


class BusinessBankAccount(TimeStampedModel):
    """
    Bank account details.

    Bank details are mandatory for every business type.
    """

    business_bank_account_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    application = models.OneToOneField(
        BusinessApplication,
        on_delete=models.CASCADE,
        related_name="bank_account",
    )

    account_holder_name = models.CharField(
        max_length=150,
    )

    account_number = models.CharField(
        max_length=30,
    )

    ifsc_code = models.CharField(
        max_length=11,
    )

    bank_name = models.CharField(
        max_length=150,
    )

    branch_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    verification_status = models.CharField(
        max_length=20,
        choices=BankVerificationStatus.choices,
        default=BankVerificationStatus.PENDING,
        db_index=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_business_bank_accounts",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()

        errors = {}

        # Account holder
        self.account_holder_name = (
            self.account_holder_name.strip()
        )

        if not self.account_holder_name:
            errors["account_holder_name"] = (
                "Account holder name is required."
            )

        # Account number
        account_number = (
            self.account_number.strip()
        )

        if not account_number.isdigit():
            errors["account_number"] = (
                "Account number must contain "
                "only digits."
            )
        elif not 9 <= len(account_number) <= 18:
            errors["account_number"] = (
                "Account number must contain "
                "between 9 and 18 digits."
            )
        else:
            self.account_number = account_number

        # IFSC
        ifsc = (
            self.ifsc_code
            .strip()
            .upper()
        )

        if (
            len(ifsc) != 11
            or ifsc[4] != "0"
        ):
            errors["ifsc_code"] = (
                "Enter a valid 11-character IFSC code."
            )
        else:
            self.ifsc_code = ifsc

        # Bank
        if not self.bank_name.strip():
            errors["bank_name"] = (
                "Bank name is required."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.application.business_application_uuid} - "
            f"{self.bank_name}"
        )


class BusinessProfile(TimeStampedModel):
    """
    Active business profile.

    This is created only after the application
    has been approved.
    """

    business_profile_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profiles",
    )

    business_type = models.CharField(
        max_length=20,
        choices=BusinessType.choices,
        db_index=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="business_profiles",
        db_index=True,
    )

    location = models.CharField(
        max_length=2000,
        help_text="Google Maps iframe/embed location.",
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    subcategories = models.ManyToManyField(
        SubCategory,
        related_name="business_profiles",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["owner", "business_type"]
            ),
            models.Index(
                fields=["name"]
            ),
        ]

    def clean(self):
        super().clean()

        if self.owner_id:
            if getattr(self.owner, "role", None) != "BUSINESS":
                raise ValidationError(
                    "Only BUSINESS users can own "
                    "a business profile."
                )
    def __str__(self):
        return (
            f"{self.name} "
            f"({self.business_type})"
        )

#======================================================================================================
#                                       Employees Model
#======================================================================================================
class Employee(TimeStampedModel):
    """
    Employee working under a BusinessProfile.
    Employees do not have separate login accounts.
    """

    employee_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="employees",
    )

    name = models.CharField(
        max_length=150,
    )

    email = models.EmailField(
        max_length=254,
    )

    phone = models.CharField(
        max_length=10,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "phone"],
                name="unique_employee_phone_per_business",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.business.name}"

#==================================================================================================
#                               Provider Availability Model
#==================================================================================================
class ProviderAvailability(TimeStampedModel):
    """
    Stores the current availability status of a service provider.

    Individual business:
        owner is the provider.

    Company / Investor business:
        employee is the provider.
    """

    provider_availability_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="provider_availabilities",
    )

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider_availability",
    )

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="provider_availability",
    )

    status = models.CharField(
        max_length=20,
        choices=EmployeeAvailabilityStatus.choices,
        default=EmployeeAvailabilityStatus.AVAILABLE,
        db_index=True,
    )

    class Meta:
        verbose_name = "Provider Availability"
        verbose_name_plural = "Provider Availabilities"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        owner__isnull=False,
                        employee__isnull=True,
                    )
                    | Q(
                        owner__isnull=True,
                        employee__isnull=False,
                    )
                ),
                name="provider_availability_one_provider",
            ),
        ]

    def clean(self):
        super().clean()

        if bool(self.owner_id) == bool(self.employee_id):
            raise ValidationError(
                "Availability must belong to either "
                "an owner or an employee."
            )

        if self.owner_id and self.business_id:
            if not BusinessProfile.objects.filter(
                pk=self.business_id,
                owner_id=self.owner_id,
            ).exists():
                raise ValidationError(
                    "Owner must belong to the selected business."
                )

        if self.employee_id and self.business_id:
            if self.employee.business_id != self.business_id:
                raise ValidationError(
                    "Employee must belong to the selected business."
                )

    def __str__(self):
        if self.employee:
            provider_name = self.employee.name
        else:
            provider_name = self.owner.email

        return f"{provider_name} - {self.status}"
# =================================================================================================================
#                                   Provider Working Schedule Model
# =================================================================================================================

class EmployeeWorkingSchedule(TimeStampedModel):
    """
    Stores the working schedule of a service provider.

    Individual business:
        owner is the provider.

    Company / Investor business:
        employee is the provider.

    Each provider can configure:
        MORNING
        AFTERNOON
        EVENING

    with their own start and end times.
    """

    employee_working_schedule_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="working_schedules",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="working_schedules",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="working_schedules",
    )

    day_of_week = models.CharField(
        max_length=10,
        choices=DayOfWeek.choices,
    )

    slot_type = models.CharField(
        max_length=10,
        choices=[
            ("MORNING", "Morning"),
            ("AFTERNOON", "Afternoon"),
            ("EVENING", "Evening"),
        ],
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "day_of_week",
            "start_time",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "owner",
                    "day_of_week",
                    "slot_type",
                ],
                condition=Q(
                    owner__isnull=False,
                ),
                name="unique_owner_schedule_slot",
            ),

            models.UniqueConstraint(
                fields=[
                    "employee",
                    "day_of_week",
                    "slot_type",
                ],
                condition=Q(
                    employee__isnull=False,
                ),
                name="unique_employee_schedule_slot",
            ),
        ]

    def clean(self):
        super().clean()

        # -----------------------------------------------------
        # Provider must be either owner OR employee
        # -----------------------------------------------------

        if bool(self.owner_id) == bool(self.employee_id):
            raise ValidationError(
                "Schedule must belong to either an owner "
                "or an employee."
            )

        # -----------------------------------------------------
        # Business must match provider
        # -----------------------------------------------------

        if self.owner_id and self.business_id:
            if not BusinessProfile.objects.filter(
                pk=self.business_id,
                owner_id=self.owner_id,
            ).exists():
                raise ValidationError(
                    "Owner must belong to the selected business."
                )

        if self.employee_id and self.business_id:
            if self.employee.business_id != self.business_id:
                raise ValidationError(
                    "Employee must belong to the selected business."
                )

        # -----------------------------------------------------
        # Start time must be before end time
        # -----------------------------------------------------

        if self.start_time >= self.end_time:
            raise ValidationError(
                {
                    "end_time": (
                        "End time must be later than start time."
                    )
                }
            )

    def __str__(self):
        if self.employee:
            provider_name = self.employee.name
        else:
            provider_name = self.owner.email

        return (
            f"{provider_name} - "
            f"{self.day_of_week} - "
            f"{self.slot_type} - "
            f"{self.start_time}-{self.end_time}"
        )
