import re
import random
from datetime import timedelta

from django.utils import timezone

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts.models import (
    CustomUser,
    PasswordResetToken,
    Address,
)
from accounts.choices import UserRole
from django.contrib.auth import authenticate


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    confirm_password = serializers.CharField(
        write_only=True
    )
    def validate_email(self, value):
        email = value.lower()

        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )

        return email

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

    def validate(self, attrs):
        password = attrs["password"]
        confirm_password = attrs["confirm_password"]

        errors = {}

        if password != confirm_password:
            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        password_errors = []

        if len(password) < 6 or len(password) > 20:
            password_errors.append(
                "Password must be between 6 and 20 characters."
            )

        if not re.search(r"[A-Z]", password):
            password_errors.append(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", password):
            password_errors.append(
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"\d", password):
            password_errors.append(
                "Password must contain at least one number."
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            password_errors.append(
                "Password must contain at least one special character."
            )

        if password_errors:
            errors["password"] = password_errors

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


    def validate_phone(self, value):
        if not value:
            return value

        pattern = r'^[6-9]\d{9}$'

        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Phone number must be exactly 10 digits and start with 6, 7, 8, or 9."
            )

        return value

    def create(self, validated_data):

        validated_data.pop("confirm_password")

        from accounts.services import AuthService

        return AuthService.register_user(validated_data)

class RegisterBusinessSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    confirm_password = serializers.CharField(
        write_only=True
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

    def validate(self, attrs):

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "confirm_password": "Passwords do not match."
                }
            )

        return attrs

    def validate_phone(self, value):
        pattern = r'^\+[1-9]\d{7,14}$'

        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Phone number must be in E.164 format. Example: +919876543210"
            )

        return value
    def validate_email(self, value):

        value = value.lower()

        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )

        return value

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        return CustomUser.objects.create_business(
            **validated_data,
        )
    
class LoginSerializer(serializers.Serializer):

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
                    "detail": "Invalid email or password."
                }
            )

        attrs["user"] = user

        return attrs
    
class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField()

    def validate(self, attrs):
        self.refresh = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            refresh_token = RefreshToken(self.refresh)
            user = self.context["request"].user

            refresh_token.blacklist()

            user.last_logout = timezone.now()
            user.save()

        except TokenError:
            raise serializers.ValidationError(
                {
                    "detail": "Invalid refresh token."
                }
        )

class UpdateProfileSerializer(serializers.ModelSerializer):

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

    def validate_phone(self, value):
        if value == "":
            return self.instance.phone

        pattern = r'^[6-9]\d{9}$'

        if value and not re.match(pattern, value):
            raise serializers.ValidationError(
                "Phone number must be exactly 10 digits and start with 6, 7, 8, or 9."
            )

        return value

    def update(self, instance, validated_data):

        validated_data.pop("profileImage", None)

        for attr, value in validated_data.items():
            if value != "":
                setattr(instance, attr, value)

        instance.save()
        return instance

# --------------------------------------------------------
# Address serializer
# --------------------------------------------------------

class AddressSerializer(serializers.ModelSerializer):
    user_uuid = serializers.UUIDField(
        source="user.uuid",
        read_only=True,
    )

    class Meta:
        model = Address
        fields = (
            "id",
            "user_uuid",
            "address_line",
            "locality",
            "city",
            "state",
            "pincode",
            "latitude",
            "longitude",
            "address_type",
            "is_default",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "user_uuid",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        user = validated_data["user"]

        if validated_data.get("is_default", False):
            Address.objects.filter(
                user=user,
                is_default=True,
            ).update(is_default=False)

        return Address.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default", False):
            Address.objects.filter(
                user=instance.user,
                is_default=True,
            ).exclude(
                id=instance.id
            ).update(is_default=False)

        return super().update(instance, validated_data)

    def validate_address_line(self, value):
        if value.strip().isdigit():
            raise serializers.ValidationError(
                "Address line cannot contain only numbers."
            )
        return value.strip()


    def validate_locality(self, value):
        if value.strip().isdigit():
            raise serializers.ValidationError(
                "Locality cannot contain only numbers."
            )
        return value.strip()


    def validate_city(self, value):
        if value.strip().isdigit():
            raise serializers.ValidationError(
                "City cannot contain only numbers."
            )
        return value.strip()


    def validate_state(self, value):
        if value.strip().isdigit():
            raise serializers.ValidationError(
                "State cannot contain only numbers."
            )
        return value.strip()


    def validate_pincode(self, value):
        if not re.fullmatch(r"\d{6}", value):
            raise serializers.ValidationError(
                "Pincode must be exactly 6 digits."
            )
        return value

#--------------------------------------------------------Unified Password Reset serializer------------------------------------------------------------
class UnifiedPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    uuid = serializers.UUIDField(required=False)

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
        request = self.context.get("request")

        # --------------------------------------------------
        # FLOW 1: Logged-in user
        # --------------------------------------------------
        if request and request.user.is_authenticated:

            if not attrs.get("new_password"):
                raise serializers.ValidationError({
                    "new_password": "This field is required."
                })

            if not attrs.get("confirm_password"):
                raise serializers.ValidationError({
                    "confirm_password": "This field is required."
                })

            self.user = request.user

            self._validate_password(
                attrs["new_password"],
                attrs["confirm_password"],
            )

            return attrs

        # --------------------------------------------------
        # FLOW 2: Logged-out user requests reset link
        # --------------------------------------------------
        if attrs.get("email") and not attrs.get("token"):

            email = attrs["email"].lower().strip()

            try:
                user = CustomUser.objects.get(
                    email__iexact=email
                )
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({
                    "email": "No account found with this email address."
                })

            if not user.is_active:
                raise serializers.ValidationError({
                    "email": "This account is inactive."
                })

            self.user = user

            return attrs

        # --------------------------------------------------
        # FLOW 3: Logged-out user resets using link
        # --------------------------------------------------
        if not attrs.get("uuid"):
            raise serializers.ValidationError({
                "uuid": "This field is required."
            })

        if not attrs.get("token"):
            raise serializers.ValidationError({
                "token": "This field is required."
            })

        if not attrs.get("new_password"):
            raise serializers.ValidationError({
                "new_password": "This field is required."
            })

        if not attrs.get("confirm_password"):
            raise serializers.ValidationError({
                "confirm_password": "This field is required."
            })

        try:
            reset_token = PasswordResetToken.objects.get(
                token=attrs["token"],
                is_used=False,
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({
                "token": "Invalid or expired reset token."
            })

        # UUID + token double verification
        if reset_token.user.uuid != attrs["uuid"]:
            raise serializers.ValidationError({
                "uuid": "UUID does not match the reset token."
            })

        if timezone.now() > reset_token.expires_at:
            raise serializers.ValidationError({
                "token": "Reset token has expired."
            })

        self.user = reset_token.user
        self.reset_token = reset_token

        self._validate_password(
            attrs["new_password"],
            attrs["confirm_password"],
        )

        return attrs

    def _validate_password(self, password, confirm_password):

        errors = {}

        if password != confirm_password:
            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        password_errors = []

        if len(password) < 6 or len(password) > 20:
            password_errors.append(
                "Password must be between 6 and 20 characters."
            )

        if not re.search(r"[A-Z]", password):
            password_errors.append(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", password):
            password_errors.append(
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"\d", password):
            password_errors.append(
                "Password must contain at least one number."
            )

        if not re.search(
            r'[!@#$%^&*(),.?":{}|<>]',
            password,
        ):
            password_errors.append(
                "Password must contain at least one special character."
            )

        if password_errors:
            errors["new_password"] = password_errors

        if errors:
            raise serializers.ValidationError(errors)

#--------------------------------------------------------Forgot Password serializer------------------------------------------------------------
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
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

class VerifyEmailSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    token = serializers.CharField()
    

        

