import mimetypes

from django.db import IntegrityError, transaction
from django.db.models import Avg
from django.urls import reverse
from rest_framework import serializers

from ..choices import BusinessType, BusinessApplicationStatus, DayOfWeek, ResponseTime

from categories.models import Category, SubCategory
from urllib.parse import urlparse
from ..models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessPortfolio,
    BusinessPortfolioFAQ,
    BusinessPortfolioGalleryImage,
    BusinessProfile,
    BusinessUpgradeIdentity,
    BusinessUpgradeRequest,
    Employee,
    ProviderAvailability,
    EmployeeWorkingSchedule,
)
import mimetypes
from ..services import get_current_business_identity

from bookings.models import Booking
from bookings.choices import BookingStatus
from reviews.models import Review
from services.models import Service
from services.api.serializers import (
    ServiceCategorySerializer,
    ServiceReadSerializer,
    ServiceSubCategorySerializer,
)

from django.utils import timezone
class BusinessApplicationDetailsSerializer(serializers.Serializer):
    # =====================================================
    # BUSINESS TYPE
    # =====================================================

    business_type = serializers.ChoiceField(
        choices=BusinessType.choices,
        required=True,
    )

    location = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    category = serializers.ChoiceField(
        choices=[],
        required=True,
    )

    # =====================================================
    # PAN
    # =====================================================

    pan_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    # =====================================================
    # AADHAAR
    # =====================================================

    aadhaar_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    # =====================================================
    # BUSINESS REGISTRATION
    # =====================================================

    gst_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    udyam_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    labour_license_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    bbmp_license_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    food_license_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    # =====================================================
    # STORE PHOTOS
    # =====================================================

    internal_store_photo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    external_store_photo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    cancelled_gst_bill_book_photo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    # =====================================================
    # OPTIONAL
    # =====================================================

    logo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    # OPTIONAL
    # =====================================================

    website = serializers.URLField(
        required=False,
        allow_blank=True,
    )

    # =====================================================
    # BANK ACCOUNT
    # =====================================================

    account_holder_name = serializers.CharField(
        required=True,
    )

    account_number = serializers.CharField(
        required=True,
    )

    ifsc_code = serializers.CharField(
        required=True,
    )

    bank_name = serializers.CharField(
        required=True,
    )

    branch_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].choices = [
            (
                category.name,
                category.name,
            )
            for category in Category.objects.filter(
                is_active=True
            ).order_by("name")
        ]

    def validate_category(self, value):
        try:
            return Category.objects.get(
                name=value,
                is_active=True,
            )
        except Category.DoesNotExist:
            raise serializers.ValidationError(
                "Selected category does not exist or is inactive."
            )

    def validate_business_type(self, value):
        if value not in BusinessType.values:
            raise serializers.ValidationError(
                "Invalid business type."
            )

        return value


class BusinessApplicationSubmitSerializer(serializers.Serializer):
    """
    Complete one-request business application serializer.

    This serializer is used only for submitting an application.
    """

    # details = BusinessApplicationDetailsSerializer(
    #     required=True,
    #     allow_null=False
    # )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["details"] = BusinessApplicationDetailsSerializer(
            required=True,
            allow_null=False,
            context=self.context,
        )

    # =====================================================
    # DOCUMENTS & PHOTOS
    # =====================================================

    pan_document = serializers.FileField(
        required=False,
        allow_null=True,
    )

    aadhaar_document = serializers.FileField(
        required=False,
        allow_null=True,
    )

    internal_store_photo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    external_store_photo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    cancelled_gst_bill_book_photo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    logo = serializers.FileField(
        required=False,
        allow_null=True,
    )

    def to_internal_value(self, data):
        import json

        if hasattr(data, "getlist"):
            mutable_data = {
                key: data.get(key)
                for key in data.keys()
            }
        else:
            mutable_data = dict(data)

        details = mutable_data.get("details")
        if details is not None:
            if isinstance(details, list) and len(details) > 0:
                details = details[0]

            if isinstance(details, str):
                try:
                    mutable_data["details"] = json.loads(details)
                except json.JSONDecodeError:
                    pass

        return super().to_internal_value(mutable_data)

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(self, attrs):

        details = attrs.pop("details", {})
        for k, v in details.items():
            attrs[k] = v

        business_type = attrs.get(
            "business_type"
        )

        errors = {}

        # =================================================
        # NORMALIZE PAN
        # =================================================

        pan_number = (
            attrs.get("pan_number") or ""
        ).strip().upper()

        attrs["pan_number"] = pan_number

        # =================================================
        # NORMALIZE AADHAAR
        # =================================================

        aadhaar_number = (
            attrs.get("aadhaar_number") or ""
        ).strip().replace(" ", "")

        attrs["aadhaar_number"] = aadhaar_number

        # =================================================
        # NORMALIZE GST
        # =================================================

        gst_number = (
            attrs.get("gst_number") or ""
        ).strip().upper()

        attrs["gst_number"] = gst_number

        # =================================================
        # PAN FORMAT
        # =================================================

        if pan_number:

            if not (
                len(pan_number) == 10
                and pan_number[:5].isalpha()
                and pan_number[5:9].isdigit()
                and pan_number[9].isalpha()
            ):
                errors["pan_number"] = (
                    "Enter a valid PAN format."
                )

        # =================================================
        # AADHAAR FORMAT
        # =================================================

        if aadhaar_number:

            if (
                len(aadhaar_number) != 12
                or not aadhaar_number.isdigit()
            ):
                errors["aadhaar_number"] = (
                    "Aadhaar must contain exactly "
                    "12 digits."
                )

        # =================================================
        # GST FORMAT
        # =================================================

        if gst_number:

            if len(gst_number) != 15:
                errors["gst_number"] = (
                    "GST number must contain exactly "
                    "15 characters."
                )

        # =================================================
        # INDIVIDUAL
        # =================================================

        if business_type == BusinessType.INDIVIDUAL:

            has_pan = bool(
                pan_number
                and attrs.get("pan_document")
            )

            has_aadhaar = bool(
                aadhaar_number
                and attrs.get("aadhaar_document")
            )

            # Minimum one complete document
            if not has_pan and not has_aadhaar:

                errors["identity"] = (
                    "For Individual, at least one "
                    "complete identity document is "
                    "required: PAN or Aadhaar."
                )

        # =================================================
        # COMPANY / INVESTOR
        # =================================================

        elif business_type in {
            BusinessType.COMPANY,
            BusinessType.INVESTOR,
        }:

            # ---------------------------------------------
            # PAN
            # ---------------------------------------------

            if not pan_number:
                errors["pan_number"] = (
                    "PAN number is required."
                )

            if not attrs.get("pan_document"):
                errors["pan_document"] = (
                    "PAN document is required."
                )

            # ---------------------------------------------
            # AADHAAR
            # ---------------------------------------------

            if not aadhaar_number:
                errors["aadhaar_number"] = (
                    "Aadhaar number is required."
                )

            if not attrs.get("aadhaar_document"):
                errors["aadhaar_document"] = (
                    "Aadhaar document is required."
                )

            # ---------------------------------------------
            # REGISTRATION
            # ---------------------------------------------

            registration_fields = [
                "gst_number",
                "udyam_number",
                "labour_license_number",
                "bbmp_license_number",
                "food_license_number",
            ]

            has_registration = any(
                attrs.get(field)
                for field in registration_fields
            )

            if not has_registration:
                errors["business_registration"] = (
                    "At least one of GST, Udyam, "
                    "Labour License, BBMP License, "
                    "or Food License is required."
                )

            # ---------------------------------------------
            # STORE PHOTOS
            # ---------------------------------------------

            if not attrs.get(
                "internal_store_photo"
            ):
                errors["internal_store_photo"] = (
                    "Internal store photo is required."
                )

            if not attrs.get(
                "external_store_photo"
            ):
                errors["external_store_photo"] = (
                    "External store photo is required."
                )

            if not attrs.get(
                "cancelled_gst_bill_book_photo"
            ):
                errors[
                    "cancelled_gst_bill_book_photo"
                ] = (
                    "Cancelled GST bill/book photo "
                    "is required."
                )

        # =================================================
        # BANK ACCOUNT
        # Mandatory for ALL business types
        # =================================================

        account_holder_name = (
            attrs.get("account_holder_name") or ""
        ).strip()

        if not account_holder_name:
            errors["account_holder_name"] = (
                "Account holder name is required."
            )

        account_number = (
            attrs.get("account_number") or ""
        ).strip()

        if not account_number:
            errors["account_number"] = (
                "Account number is required."
            )
        elif (
            not account_number.isdigit()
        ):
            errors["account_number"] = (
                "Account number must contain "
                "only digits."
            )
        elif not (
            9 <= len(account_number) <= 18
        ):
            errors["account_number"] = (
                "Account number must contain "
                "between 9 and 18 digits."
            )

        attrs["account_number"] = account_number

        ifsc_code = (
            attrs.get("ifsc_code") or ""
        ).strip().upper()

        attrs["ifsc_code"] = ifsc_code

        if not ifsc_code:
            errors["ifsc_code"] = (
                "IFSC code is required."
            )
        elif (
            len(ifsc_code) != 11
            or ifsc_code[4] != "0"
        ):
            errors["ifsc_code"] = (
                "Enter a valid 11-character IFSC code."
            )

        bank_name = (
            attrs.get("bank_name") or ""
        ).strip()

        if not bank_name:
            errors["bank_name"] = (
                "Bank name is required."
            )

        attrs["bank_name"] = bank_name

        branch_name = (
            attrs.get("branch_name") or ""
        ).strip()

        attrs["branch_name"] = branch_name

        # =================================================
        # FINAL ERRORS
        # =================================================

        if errors:
            raise serializers.ValidationError(
                errors
            )

        return attrs


class BusinessApplicationFullSerializer(
    serializers.ModelSerializer
):
    """
    Serializer used when displaying an application.
    """

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    user_uuid = serializers.UUIDField(
        source="user.user_uuid",
        read_only=True,
    )

    identity = serializers.SerializerMethodField()

    bank_account = serializers.SerializerMethodField()

    class Meta:
        model = BusinessApplication

        fields = (
            "user_uuid",
            "business_application_uuid",
            "user_email",
            "business_type",
            "location",
            "status",
            "identity",
            "bank_account",
            "created_at",
            "reviewed_at",
            "rejection_reason",
        )

        read_only_fields = fields

    def get_identity(self, obj):
        try:
            identity = obj.identity
        except BusinessIdentity.DoesNotExist:
            return None

        request = self.context.get("request")

        def get_file_url(file_field):
            if not file_field or not file_field.name:
                return None

            url = f"/media/{file_field.name}"

            if request:
                url = request.build_absolute_uri(url)

            return url

        return {
            "business_identity_uuid": str(
                identity.business_identity_uuid
            ),

            "pan_number": identity.pan_number,
            "pan_document": get_file_url(
                identity.pan_document
            ),

            "aadhaar_number": identity.aadhaar_number,
            "aadhaar_document": get_file_url(
                identity.aadhaar_document
            ),

            "gst_number": identity.gst_number,
            "udyam_number": identity.udyam_number,
            "labour_license_number": identity.labour_license_number,
            "bbmp_license_number": identity.bbmp_license_number,
            "food_license_number": identity.food_license_number,

            "internal_store_photo": get_file_url(
                identity.internal_store_photo
            ),

            "external_store_photo": get_file_url(
                identity.external_store_photo
            ),

            "cancelled_gst_bill_book_photo": get_file_url(
                identity.cancelled_gst_bill_book_photo
            ),

            "logo": get_file_url(
                identity.logo
            ),

            "website": identity.website,
            "created_at": identity.created_at,
            "updated_at": identity.updated_at,
        }
    def get_bank_account(self, obj):

        try:
            bank = obj.bank_account
        except BusinessBankAccount.DoesNotExist:
            return None

        return {
            "business_bank_account_uuid": str(bank.business_bank_account_uuid),
            "account_holder_name": (
                bank.account_holder_name
            ),
            "account_number": (
                bank.account_number
            ),
            "ifsc_code": bank.ifsc_code,
            "bank_name": bank.bank_name,
            "branch_name": bank.branch_name,
            "verification_status": (
                bank.verification_status
            ),
            "verified_at": bank.verified_at,
            "rejection_reason": (
                bank.rejection_reason
            ),
            "created_at": bank.created_at,
            "updated_at": bank.updated_at,
        }


class RejectBusinessApplicationSerializer(
    serializers.Serializer
):
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_reason(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Rejection reason is required."
            )

        return value

class BusinessProfileRankUpdateSerializer(
    serializers.Serializer
):
    rank = serializers.IntegerField(
        required=True,
        min_value=1,
    )
    
class BusinessProfileSerializer(
    serializers.ModelSerializer
):
    business_name = serializers.CharField(
        source="name"
    )
    contact_phone = serializers.CharField(
        source="phone"
    )
    contact_email = serializers.EmailField(
        source="email"
    )
    address = serializers.CharField(
        source="location"
    )
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    category_uuid = serializers.UUIDField(
        source="category.cat_uuid",
        read_only=True,
    )

    class Meta:
        model = BusinessProfile

        fields = (
            "business_profile_uuid",
            "business_name",
            "description",
            "contact_phone",
            "contact_email",
            "address",
            "logo_url",
            "banner_url",
            "business_type",
            "website",
            "is_active",
            "created_at",
            "category_uuid",
        )

        read_only_fields = (
            "business_profile_uuid",
            "business_name",
            "contact_phone",
            "contact_email",
            "address",
            "logo_url",
            "banner_url",
            "business_type",
            "created_at",
            "category_uuid",
        )

    def get_logo_url(self, obj):
        identity = (
            BusinessIdentity.objects
            .filter(
                application__user=obj.owner,
                application__status=BusinessApplicationStatus.APPROVED,
            )
            .first()
        )

        if not identity or not identity.logo:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(
                identity.logo.url
            )

        return identity.logo.url

    def get_banner_url(self, obj):
        return None

class PublicBusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = (
            "business_profile_uuid",
            "name",
            "description",
            "phone",
            "email",
            "location",
            "business_type",
            "website",
            "is_active",
            "rank",
            "created_at",
        )
        read_only_fields = fields
#=============================================================================================================================
#                       Create Employee Seriaalizer
#=============================================================================================================================
class EmployeeCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields = (
            "employee_uuid",
            "name",
            "email",
            "phone",
            "is_active",
        )
        read_only_fields = (
            "employee_uuid",
        )

    def validate_phone(self, value):
        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "Phone number must contain only digits."
            )

        if len(value) != 10:
            raise serializers.ValidationError(
                "Phone number must contain exactly 10 digits."
            )

        request = self.context.get("request")

        if request and request.user.is_authenticated:

            business = BusinessProfile.objects.filter(
                owner=request.user,
                is_active=True,
            ).first()

            if business and Employee.objects.filter(
                business=business,
                phone=value,
            ).exists():
                raise serializers.ValidationError(
                    "An employee with this phone number "
                    "already exists in your business."
                )

        return value

#========================================================
#         Employee List Serializer
#========================================================
class EmployeeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "employee_uuid",
            "name",
            "email",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        )

#===========================================================
#                 Employee Update Serializer
#===========================================================
class EmployeeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "name",
            "email",
            "phone",
            "is_active",
        )
        extra_kwargs = {
            "name": {"required": False},
            "email": {"required": False},
            "phone": {"required": False},
            "is_active": {"required": False},
        }

    def validate_phone(self, value):
        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "Phone number must contain only digits."
            )

        if len(value) != 10:
            raise serializers.ValidationError(
                "Phone number must contain exactly 10 digits."
            )

        return value

#========================================================================================================
#                               Provider Availability
#========================================================================================================
class ProviderAvailabilitySerializer(serializers.ModelSerializer):
    provider_availability_uuid = serializers.UUIDField(
        read_only=True
    )

    employee_uuid = serializers.UUIDField(
        source="employee.employee_uuid",
        required=False,
        read_only=True,
        allow_null=True,
    )
    employee_name = serializers.CharField(
        source="employee.name",
        read_only=True,
        allow_null=True,
    )

    business_uuid = serializers.UUIDField(
        source="business.business_profile_uuid",
        read_only=True
    )

    owner_uuid = serializers.UUIDField(
        source="owner.user_uuid",
        read_only=True,
        allow_null=True,
    )



    class Meta:
        model = ProviderAvailability
        fields = (
            "provider_availability_uuid",
            "business_uuid",
            "owner_uuid",
            "employee_uuid",
            "employee_name",
            "status",
            "created_at",
            "updated_at",
        )

# =================================================================================================================
#                           PROVIDER WORKING SCHEDULE
# =================================================================================================================

class EmployeeWorkingScheduleSerializer(serializers.ModelSerializer):

    employee_uuid = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
    )



    employee_working_schedule_uuid = serializers.UUIDField(
        read_only=True,
    )

    business_uuid = serializers.UUIDField(
        source="business.business_profile_uuid",
        read_only=True,
    )

    owner_uuid = serializers.UUIDField(
        source="owner.user_uuid",
        read_only=True,
        allow_null=True,
    )

    employee = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeWorkingSchedule

        fields = (
            "employee_working_schedule_uuid",
            "business_uuid",
            "owner_uuid",
            "employee_uuid",
            "employee",
            "day_of_week",
            "slot_type",
            "start_time",
            "end_time",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "employee_working_schedule_uuid",
            "business_uuid",
            "owner_uuid",
            "employee",
            "created_at",
            "updated_at",
        )

    def get_employee(self, obj):
        if not obj.employee:
            return None

        return {
            "employee_uuid": str(
                obj.employee.employee_uuid
            ),
            "name": obj.employee.name,
            "is_active": obj.employee.is_active, 
        }


    def validate(self, attrs):

        start_time = attrs.get(
            "start_time",
            getattr(self.instance, "start_time", None)
        )

        end_time = attrs.get(
            "end_time",
            getattr(self.instance, "end_time", None)
        )

        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError({
                    "end_time": (
                        "End time must be later than start time."
                    )
                })

        day_of_week = attrs.get(
            "day_of_week",
            getattr(self.instance, "day_of_week", None)
        )

        slot_type = attrs.get(
            "slot_type",
            getattr(self.instance, "slot_type", None)
        )

        # Check duplicate schedule
        if self.instance:
            duplicate_filter = {
                "business": self.instance.business,
                "day_of_week": day_of_week,
                "slot_type": slot_type,
            }

            # Scope the check to the SAME provider only.
            # Individual businesses (owner-based, employee is None)
            # must not be compared against every other individual
            # owner on the platform — only this owner's own schedules.
            if self.instance.employee_id:
                duplicate_filter["employee"] = self.instance.employee
            else:
                duplicate_filter["owner"] = self.instance.owner

            duplicate = EmployeeWorkingSchedule.objects.filter(
                **duplicate_filter
            ).exclude(
                pk=self.instance.pk
            ).exists()

            if duplicate:
                raise serializers.ValidationError({
                    "day_of_week": (
                        f"{day_of_week} {slot_type} schedule "
                        "already exists for this provider."
                    )
                })

        return attrs

    def create(self, validated_data):
        employee_uuid = validated_data.pop("employee_uuid", None)

        if employee_uuid:
            try:
                employee = Employee.objects.get(
                    employee_uuid=employee_uuid,
                    business=validated_data["business"],
                    is_active=True,
                )
            except Employee.DoesNotExist:
                raise serializers.ValidationError({
                    "employee_uuid": (
                        "Employee not found or does not belong "
                        "to this business."
                    )
                })

            validated_data["employee"] = employee

        business = validated_data["business"]
        day_of_week = validated_data["day_of_week"]
        slot_type = validated_data["slot_type"]
        owner = validated_data.get("owner")
        employee = validated_data.get("employee")

        duplicate_filter = {
            "business": business,
            "day_of_week": day_of_week,
            "slot_type": slot_type,
        }

        if employee:
            duplicate_filter["employee"] = employee
        else:
            duplicate_filter["owner"] = owner

        if EmployeeWorkingSchedule.objects.filter(
            **duplicate_filter
        ).exists():
            raise serializers.ValidationError({
                "day_of_week": (
                    f"{day_of_week} {slot_type} schedule "
                    "already exists for this provider."
                )
            })

        try:
            with transaction.atomic():
                return EmployeeWorkingSchedule.objects.create(
                    **validated_data
                )
        except IntegrityError as exc:
            error_message = str(exc)

            if (
                "unique_owner_schedule_slot" in error_message
                or "unique_employee_schedule_slot" in error_message
            ):
                raise serializers.ValidationError({
                    "day_of_week": (
                        f"{day_of_week} {slot_type} schedule "
                        "already exists for this provider."
                    )
                })

            raise

class WorkingScheduleApplyToDaysSerializer(serializers.Serializer):
    """
    Copies an already-configured day's working-schedule slots
    (e.g. MONDAY's MORNING/AFTERNOON/EVENING) onto other days.
    """

    employee_uuid = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    source_day_of_week = serializers.ChoiceField(
        choices=DayOfWeek.choices,
    )

    apply_to_all_days = serializers.BooleanField(
        required=False,
        default=False,
    )

    target_days = serializers.ListField(
        child=serializers.ChoiceField(choices=DayOfWeek.choices),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        apply_to_all_days = attrs.get("apply_to_all_days", False)
        target_days = attrs.get("target_days") or []
        source_day = attrs["source_day_of_week"]

        if not apply_to_all_days and not target_days:
            raise serializers.ValidationError(
                "Provide target_days, or set "
                "apply_to_all_days to true."
            )

        if source_day in target_days:
            raise serializers.ValidationError({
                "target_days": (
                    "target_days cannot include "
                    "source_day_of_week."
                )
            })

        return attrs
class BusinessApplicationDocumentsSerializer(
    serializers.Serializer
):
    pan_document = serializers.SerializerMethodField()
    aadhaar_document = serializers.SerializerMethodField()
    internal_store_photo = serializers.SerializerMethodField()
    external_store_photo = serializers.SerializerMethodField()
    cancelled_gst_bill_book_photo = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    def _get_document_data(
        self,
        obj,
        file_field,
        document_name,
        document_type,
        document_key,
    ):
        if not file_field or not document_name:
            return None

        request = self.context.get("request")

        # Use the original filename stored separately in DB.
        file_name = document_name.strip()

        # Points to the protected, auth-checked streaming view -
        # NOT a public /media/ path. Every hit re-validates that
        # the caller owns this application or is an Admin.
        url = reverse(
            "business-application-document-view",
            kwargs={
                "business_application_uuid": (
                    obj.application.business_application_uuid
                ),
                "document_key": document_key,
            },
        )

        if request:
            url = request.build_absolute_uri(url)

        return {
            "url": url,
            "name": file_name,
            "type": document_type or "",
        }

    def get_pan_document(self, obj):
        return self._get_document_data(
            obj,
            obj.pan_document,
            obj.pan_document_name,
            obj.pan_document_type,
            "pan",
        )

    def get_aadhaar_document(self, obj):
        return self._get_document_data(
            obj,
            obj.aadhaar_document,
            obj.aadhaar_document_name,
            obj.aadhaar_document_type,
            "aadhaar",
        )

    def get_internal_store_photo(self, obj):
        return self._get_document_data(
            obj,
            obj.internal_store_photo,
            obj.internal_store_name,
            obj.internal_store_type,
            "internal_store_photo",
        )

    def get_external_store_photo(self, obj):
        return self._get_document_data(
            obj,
            obj.external_store_photo,
            obj.external_store_name,
            obj.external_store_type,
            "external_store_photo",
        )

    def get_cancelled_gst_bill_book_photo(self, obj):
        return self._get_document_data(
            obj,
            obj.cancelled_gst_bill_book_photo,
            obj.cancelled_gst_bill_book_name,
            obj.cancelled_gst_bill_book_type,
            "gst_bill_book",
        )

    def get_logo(self, obj):
        return self._get_document_data(
            obj,
            obj.logo,
            obj.logo_name,
            obj.logo_type,
            "logo",
        )

#=============================================================================================================================
#                       Business Upgrade Request Serializers
#=============================================================================================================================

ALLOWED_UPGRADE_TRANSITIONS = {
    BusinessType.INDIVIDUAL: {BusinessType.COMPANY, BusinessType.INVESTOR},
    BusinessType.COMPANY: {BusinessType.INVESTOR, BusinessType.INDIVIDUAL},
    BusinessType.INVESTOR: {BusinessType.COMPANY, BusinessType.INDIVIDUAL},
}


class BusinessUpgradeRequestSubmitSerializer(serializers.Serializer):
    """
    Submitted by an approved BUSINESS owner to request a
    business_type change for their BusinessProfile.

    The view must pass context={
        "business": <BusinessProfile>,
        "current_identity": <BusinessIdentity or None>,
    }
    """

    requested_business_type = serializers.ChoiceField(
        choices=BusinessType.choices,
        required=True,
    )

    keep_employees_and_schedules = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=None,
    )

    bank_details_changed = serializers.BooleanField(
        required=False,
        default=False,
    )

    # ---- identity (only required if missing on file) ----
    pan_number = serializers.CharField(required=False, allow_blank=True)
    pan_document = serializers.FileField(required=False, allow_null=True)

    aadhaar_number = serializers.CharField(required=False, allow_blank=True)
    aadhaar_document = serializers.FileField(required=False, allow_null=True)

    gst_number = serializers.CharField(required=False, allow_blank=True)
    udyam_number = serializers.CharField(required=False, allow_blank=True)
    labour_license_number = serializers.CharField(required=False, allow_blank=True)
    bbmp_license_number = serializers.CharField(required=False, allow_blank=True)
    food_license_number = serializers.CharField(required=False, allow_blank=True)

    internal_store_photo = serializers.FileField(required=False, allow_null=True)
    external_store_photo = serializers.FileField(required=False, allow_null=True)
    cancelled_gst_bill_book_photo = serializers.FileField(required=False, allow_null=True)

    # ---- bank (only required if bank_details_changed=True) ----
    account_holder_name = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    ifsc_code = serializers.CharField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    branch_name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):

        business = self.context["business"]
        current_identity = self.context.get("current_identity")

        current_type = business.business_type
        requested_type = attrs["requested_business_type"]

        errors = {}

        # =================================================
        # TRANSITION CHECK
        # =================================================

        if requested_type == current_type:
            errors["requested_business_type"] = (
                "Requested business type must be different "
                "from the current business type."
            )
        elif requested_type not in ALLOWED_UPGRADE_TRANSITIONS.get(
            current_type, set()
        ):
            errors["requested_business_type"] = (
                f"Cannot change business type from {current_type} "
                f"to {requested_type}."
            )

        # =================================================
        # NORMALIZE PAN / AADHAAR / GST
        # (same format rules as the original application)
        # =================================================

        pan_number = (attrs.get("pan_number") or "").strip().upper()
        attrs["pan_number"] = pan_number

        if pan_number:
            if not (
                len(pan_number) == 10
                and pan_number[:5].isalpha()
                and pan_number[5:9].isdigit()
                and pan_number[9].isalpha()
            ):
                errors["pan_number"] = "Enter a valid PAN format."

        aadhaar_number = (
            attrs.get("aadhaar_number") or ""
        ).strip().replace(" ", "")
        attrs["aadhaar_number"] = aadhaar_number

        if aadhaar_number:
            if len(aadhaar_number) != 12 or not aadhaar_number.isdigit():
                errors["aadhaar_number"] = (
                    "Aadhaar must contain exactly 12 digits."
                )

        gst_number = (attrs.get("gst_number") or "").strip().upper()
        attrs["gst_number"] = gst_number

        if gst_number and len(gst_number) != 15:
            errors["gst_number"] = (
                "GST number must contain exactly 15 characters."
            )

        # =================================================
        # WHAT'S ALREADY ON FILE FOR THIS BUSINESS?
        # =================================================

        has_existing_pan = bool(
            current_identity
            and current_identity.pan_number
            and current_identity.pan_document
        )
        has_existing_aadhaar = bool(
            current_identity
            and current_identity.aadhaar_number
            and current_identity.aadhaar_document
        )
        has_existing_registration = bool(
            current_identity
            and any(
                [
                    current_identity.gst_number,
                    current_identity.udyam_number,
                    current_identity.labour_license_number,
                    current_identity.bbmp_license_number,
                    current_identity.food_license_number,
                ]
            )
        )
        has_existing_internal_photo = bool(
            current_identity and current_identity.internal_store_photo
        )
        has_existing_external_photo = bool(
            current_identity and current_identity.external_store_photo
        )
        has_existing_gst_bill_book = bool(
            current_identity
            and current_identity.cancelled_gst_bill_book_photo
        )

        submitted_pan = bool(pan_number and attrs.get("pan_document"))
        submitted_aadhaar = bool(
            aadhaar_number and attrs.get("aadhaar_document")
        )
        submitted_registration = any(
            [
                gst_number,
                attrs.get("udyam_number"),
                attrs.get("labour_license_number"),
                attrs.get("bbmp_license_number"),
                attrs.get("food_license_number"),
            ]
        )

        # =================================================
        # TARGET TYPE REQUIREMENTS
        # (only what's MISSING needs to be submitted)
        # =================================================

        if requested_type in {BusinessType.COMPANY, BusinessType.INVESTOR}:

            if not (has_existing_pan or submitted_pan):
                errors.setdefault(
                    "pan_number",
                    "PAN number and document are required.",
                )

            if not (has_existing_aadhaar or submitted_aadhaar):
                errors.setdefault(
                    "aadhaar_number",
                    "Aadhaar number and document are required.",
                )

            if not (has_existing_registration or submitted_registration):
                errors["business_registration"] = (
                    "At least one of GST, Udyam, Labour License, "
                    "BBMP License, or Food License is required."
                )

            if not (
                has_existing_internal_photo
                or attrs.get("internal_store_photo")
            ):
                errors["internal_store_photo"] = (
                    "Internal store photo is required."
                )

            if not (
                has_existing_external_photo
                or attrs.get("external_store_photo")
            ):
                errors["external_store_photo"] = (
                    "External store photo is required."
                )

            if not (
                has_existing_gst_bill_book
                or attrs.get("cancelled_gst_bill_book_photo")
            ):
                errors["cancelled_gst_bill_book_photo"] = (
                    "Cancelled GST bill/book photo is required."
                )

        # =================================================
        # EMPLOYEE / SCHEDULE CHOICE
        # Only meaningful for COMPANY <-> INVESTOR.
        # =================================================

        involves_individual = (
            current_type == BusinessType.INDIVIDUAL
            or requested_type == BusinessType.INDIVIDUAL
        )

        if involves_individual:
            attrs["keep_employees_and_schedules"] = None
        else:
            if attrs.get("keep_employees_and_schedules") is None:
                errors["keep_employees_and_schedules"] = (
                    "Specify whether to keep existing employees "
                    "and schedules when switching between "
                    "Company and Investor."
                )

        # =================================================
        # BANK DETAILS
        # Only required if bank_details_changed=True.
        # =================================================

        if attrs.get("bank_details_changed"):

            account_holder_name = (
                attrs.get("account_holder_name") or ""
            ).strip()
            account_number = (
                attrs.get("account_number") or ""
            ).strip()
            ifsc_code = (
                attrs.get("ifsc_code") or ""
            ).strip().upper()
            bank_name = (attrs.get("bank_name") or "").strip()

            if not account_holder_name:
                errors["account_holder_name"] = (
                    "Account holder name is required."
                )

            if not account_number:
                errors["account_number"] = (
                    "Account number is required."
                )
            elif not account_number.isdigit():
                errors["account_number"] = (
                    "Account number must contain only digits."
                )
            elif not (9 <= len(account_number) <= 18):
                errors["account_number"] = (
                    "Account number must contain between "
                    "9 and 18 digits."
                )

            if not ifsc_code:
                errors["ifsc_code"] = "IFSC code is required."
            elif len(ifsc_code) != 11 or ifsc_code[4] != "0":
                errors["ifsc_code"] = (
                    "Enter a valid 11-character IFSC code."
                )

            if not bank_name:
                errors["bank_name"] = "Bank name is required."

            attrs["account_holder_name"] = account_holder_name
            attrs["account_number"] = account_number
            attrs["ifsc_code"] = ifsc_code
            attrs["bank_name"] = bank_name
            attrs["branch_name"] = (
                attrs.get("branch_name") or ""
            ).strip()

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class BusinessUpgradeRequestFullSerializer(serializers.ModelSerializer):
    """
    Serializer used when displaying an upgrade request.
    """

    business_uuid = serializers.UUIDField(
        source="business.business_profile_uuid",
        read_only=True,
    )

    business_name = serializers.CharField(
        source="business.name",
        read_only=True,
    )

    owner_uuid = serializers.UUIDField(
        source="business.owner.user_uuid",
        read_only=True,
    )

    class Meta:
        model = BusinessUpgradeRequest

        fields = (
            "business_upgrade_request_uuid",
            "business_uuid",
            "business_name",
            "owner_uuid",
            "current_business_type",
            "requested_business_type",
            "keep_employees_and_schedules",
            "bank_details_changed",
            "status",
            "created_at",
            "reviewed_at",
            "rejection_reason",
        )

        read_only_fields = fields


class BusinessUpgradeRequestDocumentsSerializer(
    serializers.Serializer
):
    """
    Metadata for documents submitted with an upgrade request.
    Unlike BusinessIdentity, BusinessUpgradeIdentity has no
    separate stored filename/type columns, so both are derived
    directly from the FieldFile itself.
    """

    pan_document = serializers.SerializerMethodField()
    aadhaar_document = serializers.SerializerMethodField()
    internal_store_photo = serializers.SerializerMethodField()
    external_store_photo = serializers.SerializerMethodField()
    cancelled_gst_bill_book_photo = serializers.SerializerMethodField()

    def _get_document_data(self, obj, file_field, document_key):
        if not file_field:
            return None

        request = self.context.get("request")

        file_name = file_field.name.split("/")[-1]

        content_type, _ = mimetypes.guess_type(file_name)

        url = reverse(
            "business-upgrade-request-document-view",
            kwargs={
                "business_upgrade_request_uuid": (
                    obj.request.business_upgrade_request_uuid
                ),
                "document_key": document_key,
            },
        )

        if request:
            url = request.build_absolute_uri(url)

        return {
            "url": url,
            "name": file_name,
            "type": content_type or "",
        }

    def get_pan_document(self, obj):
        return self._get_document_data(
            obj, obj.pan_document, "pan"
        )

    def get_aadhaar_document(self, obj):
        return self._get_document_data(
            obj, obj.aadhaar_document, "aadhaar"
        )

    def get_internal_store_photo(self, obj):
        return self._get_document_data(
            obj, obj.internal_store_photo, "internal_store_photo"
        )

    def get_external_store_photo(self, obj):
        return self._get_document_data(
            obj, obj.external_store_photo, "external_store_photo"
        )

    def get_cancelled_gst_bill_book_photo(self, obj):
        return self._get_document_data(
            obj,
            obj.cancelled_gst_bill_book_photo,
            "gst_bill_book",
        )

#=============================================================================================================================
#                       Business Portfolio Serializers
#=============================================================================================================================

class BusinessPortfolioGalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPortfolioGalleryImage
        fields = (
            "gallery_image_uuid",
            "image",
            "caption",
            "created_at",
        )
        read_only_fields = fields


class BusinessPortfolioFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPortfolioFAQ
        fields = (
            "faq_uuid",
            "question",
            "answer",
            "order",
            "created_at",
        )
        read_only_fields = fields

class BusinessPortfolioWorkingHourSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeWorkingSchedule
        fields = (
            "day_of_week",
            "slot_type",
            "start_time",
            "end_time",
            "employee_name",
        )
        read_only_fields = fields

    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee_id else None
class BusinessPortfolioReviewSerializer(serializers.ModelSerializer):
    """Lightweight review info for the public business portfolio."""

    class Meta:
        model = Review
        fields = (
            "review_uuid",
            "rating",
            "message",
        )
        read_only_fields = fields

class BusinessPortfolioWriteSerializer(serializers.ModelSerializer):
    """
    Used for both POST (create) and PATCH (update) of the base
    portfolio fields. Gallery images and FAQs are handled
    separately in the view/service layer, not through this
    serializer, since they arrive as files / a JSON string.
    """

    class Meta:
        model = BusinessPortfolio
        fields = (
            "established_year",
            "starting_price",
            "response_time",
            "facebook_url",
            "instagram_url",
            "twitter_url",
            "linkedin_url",
        )

    # Maps each field name to the single domain it must link to.
    SOCIAL_URL_DOMAINS = {
        "facebook_url": ("facebook.com", "Facebook"),
        "instagram_url": ("instagram.com", "Instagram"),
        "twitter_url": ("twitter.com", "Twitter"),
        "linkedin_url": ("linkedin.com", "LinkedIn"),
    }

    def _validate_social_url(self, value, field_name):
        expected_domain, platform_name = self.SOCIAL_URL_DOMAINS[field_name]

        value = value.strip()
        if not value:
            return value

        hostname = (urlparse(value).hostname or "").lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        if hostname != expected_domain:
            raise serializers.ValidationError(
                f"Please enter a valid {platform_name} URL "
                f"(must be a {expected_domain} link)."
            )

        return value

    def validate_facebook_url(self, value):
        return self._validate_social_url(value, "facebook_url")

    def validate_instagram_url(self, value):
        return self._validate_social_url(value, "instagram_url")

    def validate_twitter_url(self, value):
        return self._validate_social_url(value, "twitter_url")

    def validate_linkedin_url(self, value):
        return self._validate_social_url(value, "linkedin_url")

    def validate_established_year(self, value):
        if value is None:
            return value

        current_year = timezone.now().year

        if value < 1900 or value > current_year:
            raise serializers.ValidationError(
                f"established_year must be a real 4-digit year between 1900 and {current_year}."
            )

        return value

    def validate_starting_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "starting_price must be greater than 0."
            )

        return value

class BusinessPortfolioRequestDocSerializer(serializers.Serializer):
    """
    Documentation-only serializer, used purely so Swagger shows the
    full multipart payload (base fields + gallery image uploads +
    the FAQs JSON string). The view does NOT validate against this
    serializer — base fields are validated with
    BusinessPortfolioWriteSerializer, and gallery_images/faqs are
    parsed separately in the view/service.
    """

    established_year = serializers.IntegerField(required=False)
    starting_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
    )
    response_time = serializers.ChoiceField(
        choices=ResponseTime.choices,
        required=False,
    )
    facebook_url = serializers.URLField(required=False)
    instagram_url = serializers.URLField(required=False)
    twitter_url = serializers.URLField(required=False)
    linkedin_url = serializers.URLField(required=False)

    gallery_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        help_text="One or more image files to add to the gallery.",
    )

    faqs = serializers.CharField(
        required=False,
        help_text=(
            'JSON string list of FAQs to add, e.g. '
            '[{"question": "Do you work weekends?", "answer": "Yes"}]'
        ),
    )


class BusinessPortfolioPublicSerializer(serializers.ModelSerializer):
    """
    Full public "portfolio" view of a business. Aggregates the
    BusinessProfile itself with services, employees, completed
    booking count, ratings/reviews, verification badges, and the
    BusinessPortfolio extras (gallery, FAQs, social links, price,
    response time, established year).
    """

    category = ServiceCategorySerializer(read_only=True)
    subcategories = serializers.SerializerMethodField()
    def get_subcategories(self, obj):
        subcategories = SubCategory.objects.filter(
            services__business=obj,
            services__is_active=True,
        ).distinct()

        return ServiceSubCategorySerializer(
            subcategories,
            many=True,
        ).data

    services = serializers.SerializerMethodField()
    employees = serializers.SerializerMethodField()
    completed_bookings_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    verification_badges = serializers.SerializerMethodField()

    established_year = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()
    faqs = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()

    class Meta:
        model = BusinessProfile
        fields = (
            "business_profile_uuid",
            "name",
            "description",
            "phone",
            "email",
            "location",
            "website",
            "business_type",
            "category",
            "subcategories",
            "is_active",
            "created_at",
            "services",
            "employees",
            "completed_bookings_count",
            "average_rating",
            "review_count",
            "recent_reviews",
            "verification_badges",
            "established_year",
            "starting_price",
            "response_time",
            "social_links",
            "gallery_images",
            "faqs",
            "working_hours",
        )
        read_only_fields = fields

    def _get_portfolio(self, obj):
        return getattr(obj, "portfolio", None)

    def get_services(self, obj):
        services = Service.objects.filter(
            business=obj,
            is_active=True,
        )
        return ServiceReadSerializer(
            services,
            many=True,
            context=self.context,
        ).data

    def get_employees(self, obj):
        employees = obj.employees.filter(is_active=True)
        return EmployeeListSerializer(employees, many=True).data

    def get_completed_bookings_count(self, obj):
        return Booking.objects.filter(
            business=obj,
            status=BookingStatus.COMPLETED,
        ).count()

    def get_average_rating(self, obj):
        result = Review.objects.filter(business=obj).aggregate(avg=Avg("rating"))
        avg = result["avg"]
        return round(avg, 1) if avg is not None else None

    def get_review_count(self, obj):
        return Review.objects.filter(business=obj).count()

    def get_recent_reviews(self, obj):
        reviews = Review.objects.filter(business=obj).order_by("-created_at")[:5]
        return BusinessPortfolioReviewSerializer(reviews, many=True).data

    def get_verification_badges(self, obj):
        identity = get_current_business_identity(obj)

        if not identity:
            return {
                "gst_verified": False,
                "pan_verified": False,
                "aadhaar_verified": False,
            }

        return {
            "gst_verified": bool(identity.gst_number),
            "pan_verified": bool(identity.pan_number),
            "aadhaar_verified": bool(identity.aadhaar_number),
        }

    def get_established_year(self, obj):
        portfolio = self._get_portfolio(obj)
        return portfolio.established_year if portfolio else None

    def get_starting_price(self, obj):
        portfolio = self._get_portfolio(obj)
        return portfolio.starting_price if portfolio else None

    def get_response_time(self, obj):
        portfolio = self._get_portfolio(obj)
        return portfolio.response_time if portfolio else ""

    def get_social_links(self, obj):
        portfolio = self._get_portfolio(obj)

        if not portfolio:
            return {
                "facebook": "",
                "instagram": "",
                "twitter": "",
                "linkedin": "",
            }

        return {
            "facebook": portfolio.facebook_url,
            "instagram": portfolio.instagram_url,
            "twitter": portfolio.twitter_url,
            "linkedin": portfolio.linkedin_url,
        }

    def get_gallery_images(self, obj):
        portfolio = self._get_portfolio(obj)

        if not portfolio:
            return []

        return BusinessPortfolioGalleryImageSerializer(
            portfolio.gallery_images.all(),
            many=True,
            context=self.context,
        ).data

    def get_faqs(self, obj):
        portfolio = self._get_portfolio(obj)

        if not portfolio:
            return []

        return BusinessPortfolioFAQSerializer(
            portfolio.faqs.all(),
            many=True,
        ).data

    def get_working_hours(self, obj):
        schedules = EmployeeWorkingSchedule.objects.filter(
            business=obj,
            is_active=True,
        )

        return BusinessPortfolioWorkingHourSerializer(
            schedules,
            many=True,
        ).data
