import re

from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts.models import (
    CustomUser,
    PasswordResetToken,
    Address,
)

from accounts.choices import UserRole


from rest_framework import serializers


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

## =========================================================
# USER REGISTRATION
# =========================================================

class RegisterUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=6,
        max_length=20,
    )

    confirm_password = serializers.CharField(
        write_only=True,
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=15,
    )

    class Meta:

        model = CustomUser

        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "password",
            "confirm_password",
        )

    # =====================================================
    # EMAIL VALIDATION
    # =====================================================

    def validate_email(self, value):

        if not value:
            return ""

        value = value.lower().strip()

        if CustomUser.objects.filter(
            email__iexact=value
        ).exists():

            raise serializers.ValidationError(
                "Email already exists."
            )

        return value

    # =====================================================
    # PHONE VALIDATION
    # =====================================================

    def validate_phone(self, value):

        if not value:
            return ""

        value = str(value).strip()

        # +919876543210
        if value.startswith("+91"):

            value = value[3:]

        # 919876543210
        elif (
            value.startswith("91")
            and len(value) == 12
        ):

            value = value[2:]

        # Validate Indian mobile number
        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):

            raise serializers.ValidationError(
                "Phone number must be exactly "
                "10 digits and start with 6, 7, 8, or 9."
            )

        # Check existing normalized phone
        if CustomUser.objects.filter(
            phone=value
        ).exists():

            raise serializers.ValidationError(
                "Phone number already exists."
            )

        # Protect against old +91 stored values
        if CustomUser.objects.filter(
            phone=f"+91{value}"
        ).exists():

            raise serializers.ValidationError(
                "Phone number already exists."
            )

        return value

    # =====================================================
    # OBJECT VALIDATION
    # =====================================================

    def validate(self, attrs):

        errors = {}

        email = (
            attrs.get("email")
            or ""
        ).strip()

        phone = (
            attrs.get("phone")
            or ""
        ).strip()

        password = attrs.get(
            "password"
        )

        confirm_password = attrs.get(
            "confirm_password"
        )

        # -------------------------------------------------
        # EMAIL OR PHONE
        # -------------------------------------------------

        if not email and not phone:

            errors["email"] = [
                "Either email or phone number is required."
            ]

            errors["phone"] = [
                "Either email or phone number is required."
            ]

        # -------------------------------------------------
        # PASSWORD MATCH
        # -------------------------------------------------

        if password != confirm_password:

            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        # -------------------------------------------------
        # PASSWORD VALIDATION
        # -------------------------------------------------

        password_errors = []

        if password:

            if (
                len(password) < 6
                or len(password) > 20
            ):

                password_errors.append(
                    "Password must be between "
                    "6 and 20 characters."
                )

            if not re.search(
                r"[A-Z]",
                password
            ):

                password_errors.append(
                    "Password must contain at "
                    "least one uppercase letter."
                )

            if not re.search(
                r"[a-z]",
                password
            ):

                password_errors.append(
                    "Password must contain at "
                    "least one lowercase letter."
                )

            if not re.search(
                r"\d",
                password
            ):

                password_errors.append(
                    "Password must contain at "
                    "least one number."
                )

            if not re.search(
                r'[!@#$%^&*(),.?":{}|<>]',
                password
            ):

                password_errors.append(
                    "Password must contain at "
                    "least one special character."
                )

        if password_errors:

            errors["password"] = password_errors

        # -------------------------------------------------
        # NORMALIZE VALUES
        # -------------------------------------------------

        attrs["email"] = email
        attrs["phone"] = phone

        if errors:

            raise serializers.ValidationError(
                errors
            )

        return attrs

    # =====================================================
    # CREATE
    # =====================================================

    def create(self, validated_data):

        validated_data.pop(
            "confirm_password"
        )

        from accounts.services import AuthService

        return AuthService.register_user(
            validated_data
        )




# =========================================================
# LOGIN
# =========================================================

class LoginSerializer(
    serializers.Serializer
):

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):

        email = attrs.get("email")

        password = attrs.get("password")

        user = authenticate(
            email=email,
            password=password
        )

        if not user:

            raise serializers.ValidationError(
                {
                    "detail":
                    "Invalid email or password."
                }
            )

        attrs["user"] = user

        return attrs


# =========================================================
# LOGOUT
# =========================================================

class LogoutSerializer(
    serializers.Serializer
):

    refresh = serializers.CharField()

    def validate(self, attrs):

        self.refresh = attrs["refresh"]

        return attrs

    def save(self, **kwargs):

        try:

            refresh_token = RefreshToken(
                self.refresh
            )

            user = self.context[
                "request"
            ].user

            refresh_token.blacklist()

            user.last_logout = timezone.now()

            user.save()

        except TokenError:

            raise serializers.ValidationError(
                {
                    "detail":
                    "Invalid refresh token."
                }
            )


# =========================================================
# UPDATE PROFILE
# =========================================================

class UpdateProfileSerializer(
    serializers.ModelSerializer
):

    firstName = serializers.CharField(
        source="first_name",
        required=False,
        allow_blank=True,
    )

    lastName = serializers.CharField(
        source="last_name",
        required=False,
        allow_blank=True,
    )

    phone = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    profileImage = serializers.CharField(
        required=False,
        allow_null=True,
        write_only=True,
        allow_blank=True,
    )

    class Meta:

        model = CustomUser

        fields = (
            "firstName",
            "lastName",
            "phone",
            "profileImage",
        )

    # =====================================================
    # PHONE VALIDATION
    # =====================================================

    def validate_phone(self, value):

        if value == "":
            return self.instance.phone

        value = str(value).strip()

        # -------------------------------------------------
        # NORMALIZE PHONE NUMBER
        # -------------------------------------------------

        # +919876543210 -> 9876543210
        if value.startswith("+91"):
            value = value[3:]

        # 919876543210 -> 9876543210
        elif (
            value.startswith("91")
            and len(value) == 12
        ):
            value = value[2:]

        # -------------------------------------------------
        # VALIDATE INDIAN MOBILE NUMBER
        # -------------------------------------------------

        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):
            raise serializers.ValidationError(
                "Phone number must be exactly "
                "10 digits and start with 6, 7, 8, or 9."
            )

        # -------------------------------------------------
        # CHECK DUPLICATE ONLY IN CustomUser
        # -------------------------------------------------

        if CustomUser.objects.filter(
            phone=value
        ).exclude(
            pk=self.instance.pk
        ).exists():

            raise serializers.ValidationError(
                "Phone number already exists."
            )

        # -------------------------------------------------
        # PROTECT AGAINST OLD +91 STORED VALUES
        # -------------------------------------------------

        if CustomUser.objects.filter(
            phone=f"+91{value}"
        ).exclude(
            pk=self.instance.pk
        ).exists():

            raise serializers.ValidationError(
                "Phone number already exists."
            )

        return value

    # =====================================================
    # UPDATE
    # =====================================================

    def update(
        self,
        instance,
        validated_data
    ):

        validated_data.pop(
            "profileImage",
            None
        )

        for attr, value in validated_data.items():

            if value != "":
                setattr(
                    instance,
                    attr,
                    value
                )

        instance.save()

        return instance

# =========================================================
# ADDRESS
# =========================================================

class AddressSerializer(
    serializers.ModelSerializer
):

    add_uuid = serializers.UUIDField(
        read_only=True,
    )

    user_uuid = serializers.UUIDField(
        source="user.user_uuid",
        read_only=True,
    )

    class Meta:

        model = Address

        fields = (
            "add_uuid",
            "user_uuid",
            "address_line",
            "locality",
            "city",
            "state",
            "pincode",
            "location",
            "address_type",
            "is_default",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "add_uuid",
            "user_uuid",
            "created_at",
            "updated_at",
        )

    def create(
        self,
        validated_data
    ):

        user = validated_data["user"]

        if validated_data.get(
            "is_default",
            False
        ):

            Address.objects.filter(
                user=user,
                is_default=True,
            ).update(
                is_default=False
            )

        return Address.objects.create(
            **validated_data
        )

    def update(
        self,
        instance,
        validated_data
    ):

        if validated_data.get(
            "is_default",
            False
        ):

            Address.objects.filter(
                user=instance.user,
                is_default=True,
            ).exclude(
                id=instance.id
            ).update(
                is_default=False
            )

        return super().update(
            instance,
            validated_data
        )

    def validate_address_line(
        self,
        value
    ):

        if value.strip().isdigit():

            raise serializers.ValidationError(
                "Address line cannot contain only numbers."
            )

        return value.strip()

    def validate_locality(
        self,
        value
    ):

        if value.strip().isdigit():

            raise serializers.ValidationError(
                "Locality cannot contain only numbers."
            )

        return value.strip()

    def validate_city(
        self,
        value
    ):

        if value.strip().isdigit():

            raise serializers.ValidationError(
                "City cannot contain only numbers."
            )

        return value.strip()

    def validate_state(
        self,
        value
    ):

        if value.strip().isdigit():

            raise serializers.ValidationError(
                "State cannot contain only numbers."
            )

        return value.strip()

    def validate_pincode(
        self,
        value
    ):

        if not re.fullmatch(
            r"\d{6}",
            value
        ):

            raise serializers.ValidationError(
                "Pincode must be exactly 6 digits."
            )

        return value


# =========================================================
# UNIFIED PASSWORD RESET
# =========================================================

class UnifiedPasswordResetSerializer(
    serializers.Serializer
):

    email = serializers.EmailField(
        required=False
    )

    user_uuid = serializers.UUIDField(
        required=False
    )

    token = serializers.CharField(
        required=False,
        write_only=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=False,
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
    )

    def validate(self, attrs):

        request = self.context.get(
            "request"
        )

        # -------------------------------------------------
        # LOGGED-IN USER
        # -------------------------------------------------

        if (
            request
            and request.user.is_authenticated
        ):

            if not attrs.get(
                "new_password"
            ):

                raise serializers.ValidationError({
                    "new_password":
                    "This field is required."
                })

            if not attrs.get(
                "confirm_password"
            ):

                raise serializers.ValidationError({
                    "confirm_password":
                    "This field is required."
                })

            self.user = request.user

            self._validate_password(
                attrs["new_password"],
                attrs["confirm_password"],
            )

            return attrs

        # -------------------------------------------------
        # RESET LINK REQUEST
        # -------------------------------------------------

        if (
            attrs.get("email")
            and not attrs.get("token")
        ):

            email = (
                attrs["email"]
                .lower()
                .strip()
            )

            try:

                user = CustomUser.objects.get(
                    email__iexact=email
                )

            except CustomUser.DoesNotExist:

                raise serializers.ValidationError({
                    "email":
                    "No account found with this email address."
                })

            if not user.is_active:

                raise serializers.ValidationError({
                    "email":
                    "This account is inactive."
                })

            self.user = user

            return attrs

        # -------------------------------------------------
        # RESET USING LINK
        # -------------------------------------------------

        if not attrs.get("user_uuid"):
            raise serializers.ValidationError({
                "user_uuid": "This field is required."
            })

        if not attrs.get("token"):

            raise serializers.ValidationError({
                "token":
                "This field is required."
            })

        if not attrs.get(
            "new_password"
        ):

            raise serializers.ValidationError({
                "new_password":
                "This field is required."
            })

        if not attrs.get(
            "confirm_password"
        ):

            raise serializers.ValidationError({
                "confirm_password":
                "This field is required."
            })

        try:

            reset_token = PasswordResetToken.objects.get(
                token=attrs["token"],
                is_used=False,
            )

        except PasswordResetToken.DoesNotExist:

            raise serializers.ValidationError({
                "token":
                "Invalid or expired reset token."
            })

        if (
            reset_token.user.user_uuid
            != attrs["user_uuid"]
            ):

            raise serializers.ValidationError({
                "user_uuid":
                "UUID does not match the reset token."
            })

        if timezone.now() > reset_token.expires_at:

            raise serializers.ValidationError({
                "token":
                "Reset token has expired."
            })

        self.user = reset_token.user

        self.reset_token = reset_token

        self._validate_password(
            attrs["new_password"],
            attrs["confirm_password"],
        )

        return attrs

    def _validate_password(
        self,
        password,
        confirm_password
    ):

        errors = {}

        if password != confirm_password:

            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        password_errors = []

        if (
            len(password) < 6
            or len(password) > 20
        ):

            password_errors.append(
                "Password must be between "
                "6 and 20 characters."
            )

        if not re.search(
            r"[A-Z]",
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one uppercase letter."
            )

        if not re.search(
            r"[a-z]",
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one lowercase letter."
            )

        if not re.search(
            r"\d",
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one number."
            )

        if not re.search(
            r'[!@#$%^&*(),.?":{}|<>]',
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one special character."
            )

        if password_errors:

            errors["new_password"] = password_errors

        if errors:

            raise serializers.ValidationError(
                errors
            )


# =========================================================
# FORGOT PASSWORD
# =========================================================

class ForgotPasswordSerializer(
    serializers.Serializer
):

    email = serializers.EmailField()

    def validate_email(
        self,
        value
    ):

        value = value.lower().strip()

        try:

            user = CustomUser.objects.get(
                email__iexact=value
            )

        except CustomUser.DoesNotExist:

            raise serializers.ValidationError(
                "No account found with this email address."
            )

        if not user.is_active:

            raise serializers.ValidationError(
                "This account is inactive."
            )

        self.user = user

        return value


# =========================================================
# EMAIL VERIFICATION
# =========================================================

class VerifyEmailSerializer(
    serializers.Serializer
):

    pending_registration_uuid = serializers.UUIDField()

    token = serializers.CharField()


# =========================================================
# LOGIN OTP SEND
# =========================================================

class SendOTPSerializer(
    serializers.Serializer
):

    phone = serializers.CharField(
        max_length=15
    )

    def validate_phone(
        self,
        value
    ):

        value = str(value).strip()

        if value.startswith("+91"):

            value = value[3:]

        elif (
            value.startswith("91")
            and len(value) == 12
        ):

            value = value[2:]

        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):

            raise serializers.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        try:

            user = CustomUser.objects.get(
                phone=value
            )

        except CustomUser.DoesNotExist:

            try:

                user = CustomUser.objects.get(
                    phone=f"+91{value}"
                )

            except CustomUser.DoesNotExist:

                raise serializers.ValidationError(
                    "No account exists with this phone number."
                )

        if not user.is_active:

            raise serializers.ValidationError(
                "This account is inactive."
            )

        self.user = user

        self.normalized_phone = value

        return value


# =========================================================
# LOGIN OTP SEND
# =========================================================

class LoginSendOTPSerializer(serializers.Serializer):

    phone = serializers.CharField(
        max_length=15
    )

    def validate_phone(self, value):

        value = str(value).strip()

        # +919876543210
        if value.startswith("+91"):
            value = value[3:]

        # 919876543210
        elif (
            value.startswith("91")
            and len(value) == 12
        ):
            value = value[2:]

        # Validate Indian mobile number
        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):
            raise serializers.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        # Find user
        try:

            user = CustomUser.objects.get(
                phone=value
            )

        except CustomUser.DoesNotExist:

            try:

                user = CustomUser.objects.get(
                    phone=f"+91{value}"
                )

            except CustomUser.DoesNotExist:

                raise serializers.ValidationError(
                    "No account exists with this phone number."
                )

        # Check account status
        if not user.is_active:

            raise serializers.ValidationError(
                "This account is inactive."
            )

        # Store user for the view
        self.user = user

        # Store normalized phone
        self.normalized_phone = value

        return value

# =========================================================
# LOGIN OTP VERIFY
# =========================================================

class VerifyOTPSerializer(
    serializers.Serializer
):

    phone = serializers.CharField(
        max_length=15
    )

    otp = serializers.CharField(
        min_length=6,
        max_length=6
    )

    def validate_phone(
        self,
        value
    ):

        value = str(value).strip()

        if value.startswith("+91"):

            value = value[3:]

        elif (
            value.startswith("91")
            and len(value) == 12
        ):

            value = value[2:]

        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):

            raise serializers.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        return value

    def validate_otp(
        self,
        value
    ):

        value = str(value).strip()

        if not value.isdigit():

            raise serializers.ValidationError(
                "OTP must contain only numbers."
            )

        if len(value) != 6:

            raise serializers.ValidationError(
                "OTP must be exactly 6 digits."
            )

        return value


# =========================================================
# SIGNUP OTP SEND
# =========================================================

class SignupSendOTPSerializer(
    serializers.Serializer
):

    phone = serializers.CharField(
        max_length=15
    )

    def validate_phone(
        self,
        value
    ):

        value = str(value).strip()

        if value.startswith("+91"):

            value = value[3:]

        elif (
            value.startswith("91")
            and len(value) == 12
        ):

            value = value[2:]

        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):

            raise serializers.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        # -------------------------------------------------
        # IMPORTANT:
        # SIGNUP = PHONE MUST NOT ALREADY EXIST
        # -------------------------------------------------

        if CustomUser.objects.filter(
            phone=value
        ).exists():

            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        if CustomUser.objects.filter(
            phone=f"+91{value}"
        ).exists():

            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        return value


# =========================================================
# SIGNUP OTP VERIFY
# =========================================================

class SignupVerifyOTPSerializer(serializers.Serializer):

    # -----------------------------------------------------
    # PHONE
    # -----------------------------------------------------
    # The phone number is now required during OTP
    # verification so that the OTP can be matched against
    # the correct signup session/registration.
    # -----------------------------------------------------

    phone = serializers.CharField(
        max_length=15
    )

    # -----------------------------------------------------
    # OTP
    # -----------------------------------------------------

    otp = serializers.CharField(
        max_length=6,
        min_length=6
    )

    # -----------------------------------------------------
    # PHONE VALIDATION + NORMALIZATION
    # -----------------------------------------------------
    # Same normalization used by SignupSendOTPSerializer:
    #
    # +919876543210 -> 9876543210
    # 919876543210  -> 9876543210
    # 9876543210    -> 9876543210
    # -----------------------------------------------------

    def validate_phone(
        self,
        value
    ):

        value = str(value).strip()

        if value.startswith("+91"):

            value = value[3:]

        elif (
            value.startswith("91")
            and len(value) == 12
        ):

            value = value[2:]

        # Validate Indian mobile number
        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):

            raise serializers.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        return value

    # -----------------------------------------------------
    # OTP VALIDATION
    # -----------------------------------------------------

    def validate_otp(
        self,
        value
    ):

        value = str(value).strip()

        if not value.isdigit():

            raise serializers.ValidationError(
                "OTP must contain only numbers."
            )

        if len(value) != 6:

            raise serializers.ValidationError(
                "OTP must be exactly 6 digits."
            )

        return value


# =========================================================
# SIGNUP COMPLETION
#
# KEEP ONLY IF YOUR CURRENT VIEWS USE THIS API.
# =========================================================

class SignupCompleteSerializer(
    serializers.Serializer
):

    phone = serializers.CharField(
        max_length=15
    )

    first_name = serializers.CharField(
        max_length=150
    )

    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    password = serializers.CharField(
        write_only=True,
        min_length=6,
        max_length=20,
    )

    confirm_password = serializers.CharField(
        write_only=True,
    )

    def validate_phone(
        self,
        value
    ):

        value = str(value).strip()

        if value.startswith("+91"):

            value = value[3:]

        elif (
            value.startswith("91")
            and len(value) == 12
        ):

            value = value[2:]

        if not re.fullmatch(
            r"[6-9]\d{9}",
            value
        ):

            raise serializers.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        if CustomUser.objects.filter(
            phone=value
        ).exists():

            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        if CustomUser.objects.filter(
            phone=f"+91{value}"
        ).exists():

            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        return value

    def validate_email(
        self,
        value
    ):

        if not value:
            return ""

        value = value.lower().strip()

        if CustomUser.objects.filter(
            email__iexact=value
        ).exists():

            raise serializers.ValidationError(
                "Email already exists."
            )

        return value

    def validate(
        self,
        attrs
    ):

        errors = {}

        if (
            attrs["password"]
            != attrs["confirm_password"]
        ):

            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        password = attrs["password"]

        password_errors = []

        if (
            len(password) < 6
            or len(password) > 20
        ):

            password_errors.append(
                "Password must be between "
                "6 and 20 characters."
            )

        if not re.search(
            r"[A-Z]",
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one uppercase letter."
            )

        if not re.search(
            r"[a-z]",
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one lowercase letter."
            )

        if not re.search(
            r"\d",
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one number."
            )

        if not re.search(
            r'[!@#$%^&*(),.?":{}|<>]',
            password
        ):

            password_errors.append(
                "Password must contain at "
                "least one special character."
            )

        if password_errors:

            errors["password"] = password_errors

        if errors:

            raise serializers.ValidationError(
                errors
            )

        return attrs


