from rest_framework import serializers

from ..choices import BusinessType
from ..models import (
    BusinessApplication,
    BusinessBankAccount,
    BusinessIdentity,
    BusinessProfile,
)
from categories.models import Category


class BusinessApplicationSubmitSerializer(serializers.Serializer):
    """
    Complete one-request business application serializer.

    This serializer is used only for submitting an application.
    """

    # =====================================================
    # BUSINESS TYPE
    # =====================================================

    business_type = serializers.ChoiceField(
        choices=BusinessType.choices,
        required=True,
    )

    category = serializers.ChoiceField(
        choices=[],
        required=True,
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

    # =====================================================
    # PAN
    # =====================================================

    pan_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    pan_document = serializers.FileField(
        required=False,
        allow_null=True,
    )

    # =====================================================
    # AADHAAR
    # =====================================================

    aadhaar_number = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    aadhaar_document = serializers.FileField(
        required=False,
        allow_null=True,
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

    internal_store_photo = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    external_store_photo = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    cancelled_gst_bill_book_photo = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    # =====================================================
    # OPTIONAL
    # =====================================================

    logo = serializers.ImageField(
        required=False,
        allow_null=True,
    )

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

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_business_type(self, value):
        if value not in BusinessType.values:
            raise serializers.ValidationError(
                "Invalid business type."
            )

        return value

    def validate(self, attrs):

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

    identity = serializers.SerializerMethodField()

    bank_account = serializers.SerializerMethodField()

    class Meta:
        model = BusinessApplication

        fields = (
            "uuid",
            "user_email",
            "business_type",
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
            "uuid": str(identity.uuid),
            "pan_number": identity.pan_number,
            "pan_document": (
                identity.pan_document.url
                if identity.pan_document
                else None
            ),
            "aadhaar_number": identity.aadhaar_number,
            "aadhaar_document": (
                identity.aadhaar_document.url
                if identity.aadhaar_document
                else None
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
                identity.internal_store_photo.url
                if identity.internal_store_photo
                else None
            ),
            "external_store_photo": (
                identity.external_store_photo.url
                if identity.external_store_photo
                else None
            ),
            "cancelled_gst_bill_book_photo": (
                identity.cancelled_gst_bill_book_photo.url
                if identity.cancelled_gst_bill_book_photo
                else None
            ),
            "logo": (
                identity.logo.url
                if identity.logo
                else None
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
            "uuid": str(bank.uuid),
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
            "uuid",
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
            "uuid",
            "owner",
            "business_type",
            "created_at",
        )

        