from ast import pattern
from xml.parsers.expat import errors

from attr import attrs
from django.contrib.auth import authenticate
from rest_framework import serializers
import re

from accounts.models import CustomUser
from accounts.choices import UserRole

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class RegisterUserSerializer(serializers.ModelSerializer):
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
            "full_name",
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
    pattern = r'^\+[1-9]\d{7,14}$'

    if not re.match(pattern, value):
        raise serializers.ValidationError(
            "Phone number must be in E.164 format. Example: +919876543210"
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
            "full_name",
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
            token = RefreshToken(self.refresh)
            token.blacklist()

        except TokenError:
            raise serializers.ValidationError(
                {
                    "detail": "Invalid refresh token."
                }
            )
    