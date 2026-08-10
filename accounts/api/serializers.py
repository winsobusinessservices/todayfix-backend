from ast import pattern
import email
from xml.parsers.expat import errors
from django.utils import timezone   
from attr import attrs
from django.contrib.auth import authenticate
from rest_framework import serializers
import re

from accounts.models import CustomUser, PasswordResetOTP, PasswordResetToken
from accounts.choices import UserRole

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

import random
from datetime import timedelta

from django.utils import timezone


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

#-------------------------------------------------------Forget password serializer------------------------------------------------------------
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower().strip()

        try:
            user = CustomUser.objects.get(email__iexact=value)
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

    def create_otp(self):
        otp = str(random.randint(100000, 999999))

        # Invalidate previous unused OTPs
        PasswordResetOTP.objects.filter(
            user=self.user,
            is_used=False,
        ).update(is_used=True)

        # Create new OTP
        password_reset_otp = PasswordResetOTP.objects.create(
            user=self.user,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        return password_reset_otp

    def save(self, **kwargs):
        self.password_reset_otp = self.create_otp()
        return self.password_reset_otp
    
#-------------------------------------------------------Password Reset Link serializer------------------------------------------------------------
class PasswordResetLinkSerializer(serializers.Serializer):
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

class ResetPasswordLinkSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True
    )
    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        token = attrs["token"]
        password = attrs["password"]
        confirm_password = attrs["confirm_password"]

        errors = {}

        # Check passwords match
        if password != confirm_password:
            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        # Password validation
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
            password
        ):
            password_errors.append(
                "Password must contain at least one special character."
            )

        if password_errors:
            errors["password"] = password_errors

        if errors:
            raise serializers.ValidationError(errors)

        # Check reset token
        try:
            reset_token = PasswordResetToken.objects.get(
                token=token
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "token": "Invalid password reset token."
                }
            )

        # Check whether token was already used
        if reset_token.is_used:
            raise serializers.ValidationError(
                {
                    "token": "This password reset link has already been used."
                }
            )

        # Check expiry
        if reset_token.expires_at <= timezone.now():
            raise serializers.ValidationError(
                {
                    "token": "This password reset link has expired."
                }
            )

        attrs["reset_token"] = reset_token

        return attrs

#-------------------------------------------------------Verify OTP serializer------------------------------------------------------------
class VerifyPasswordResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(
        max_length=6,
        min_length=6,
    )

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        otp = attrs["otp"]

        try:
            user = CustomUser.objects.get(
                email__iexact=email
            )
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "email": "No account found with this email address."
                }
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {
                    "email": "This account is inactive."
                }
            )

        try:
            reset_otp = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False,
            ).latest("created_at")
        except PasswordResetOTP.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "otp": "Invalid OTP."
                }
            )

        if timezone.now() > reset_otp.expires_at:
            raise serializers.ValidationError(
                {
                    "otp": "OTP has expired."
                }
            )

        attrs["user"] = user
        attrs["reset_otp"] = reset_otp

        return attrs
#-------------------------------------------------------Reset Password serializer------------------------------------------------------------
class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(
        write_only=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    confirm_password = serializers.CharField(
        write_only=True,
    )

    def validate(self, attrs):
        token = attrs["token"]
        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        errors = {}

        # Validate reset token
        try:
            reset_token = PasswordResetToken.objects.get(
                token=token,
                is_used=False,
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                {
                    "token": "Invalid or expired reset token."
                }
            )

        if timezone.now() > reset_token.expires_at:
            raise serializers.ValidationError(
                {
                    "token": "Reset token has expired."
                }
            )

        # Validate password confirmation
        if new_password != confirm_password:
            errors["confirm_password"] = [
                "Passwords do not match."
            ]

        # Validate password rules
        password_errors = []

        if len(new_password) < 6 or len(new_password) > 20:
            password_errors.append(
                "Password must be between 6 and 20 characters."
            )

        if not re.search(r"[A-Z]", new_password):
            password_errors.append(
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", new_password):
            password_errors.append(
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"\d", new_password):
            password_errors.append(
                "Password must contain at least one number."
            )

        if not re.search(
            r'[!@#$%^&*(),.?":{}|<>]',
            new_password,
        ):
            password_errors.append(
                "Password must contain at least one special character."
            )

        if password_errors:
            errors["new_password"] = password_errors

        if errors:
            raise serializers.ValidationError(errors)

        attrs["reset_token"] = reset_token
        attrs["user"] = reset_token.user

        return attrs
    


        

