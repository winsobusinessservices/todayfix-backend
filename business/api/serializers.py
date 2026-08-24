

from rest_framework import serializers

from ..choices import BusinessType
from ..models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessProfile,
    Employee,
    ProviderAvailability,
    EmployeeWorkingSchedule,
)
from categories.models import Category


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

    details = BusinessApplicationDetailsSerializer(required=True)

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
            mutable_data = data.copy()
        else:
            mutable_data = dict(data)

        details = mutable_data.get("details")
        if details:
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

        return {
            "business_identity_uuid": str(identity.business_identity_uuid),
            "pan_number": identity.pan_number,
            "pan_document": (
                True
                if identity.pan_document
                else False
            ),
            "aadhaar_number": identity.aadhaar_number,
            "aadhaar_document": (
                True
                if identity.aadhaar_document
                else False
            ),
            "gst_number": identity.gst_number,
            "udyam_number": identity.udyam_number,
            "labour_license_number": (
                identity.labour_license_number
            ),
            "bbmp_license_number": (
                identity.bbmp_license_number
            ),
            "food_license_number": (
                identity.food_license_number
            ),
            "internal_store_photo": (
                True
                if identity.internal_store_photo
                else False
            ),
            "external_store_photo": (
                True
                if identity.external_store_photo
                else False
            ),
            "cancelled_gst_bill_book_photo": (
                True
                if identity.cancelled_gst_bill_book_photo
                else False
            ),
            "logo": (
                True
                if identity.logo
                else False
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


class BusinessProfileSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = BusinessProfile

        fields = (
            "business_profile_uuid",
            "owner",
            "business_type",
            "name",
            "description",
            "email",
            "phone",
            "website",
            "is_active",
            "created_at",
        )

        read_only_fields = (
            "business_profile_uuid",
            "owner",
            "business_type",
            "created_at",
        )

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
            duplicate = EmployeeWorkingSchedule.objects.filter(
                employee=self.instance.employee,
                day_of_week=day_of_week,
                slot_type=slot_type,
            ).exclude(
                pk=self.instance.pk
            ).exists()

            if duplicate:
                raise serializers.ValidationError({
                    "day_of_week": (
                        f"{day_of_week} {slot_type} schedule "
                        "already exists for this employee."
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

        return EmployeeWorkingSchedule.objects.create(
            **validated_data
        )