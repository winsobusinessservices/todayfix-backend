from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import CustomUser, PasswordResetToken
from accounts.choices import UserRole

import secrets
from datetime import timedelta

from django.utils import timezone

from accounts.models import (
    CustomUser,
    PasswordResetToken,
)

from django.conf import settings
class AuthService:

    @staticmethod
    def register_user(validated_data):

        validated_data["role"] = UserRole.USER
        validated_data["has_business"] = False
        validated_data["business_verified"] = False

        return CustomUser.objects.create_user(
            **validated_data
        )

    @staticmethod
    def register_business(validated_data):

        validated_data["role"] = UserRole.BUSINESS
        validated_data["has_business"] = True
        validated_data["business_verified"] = False

        return CustomUser.objects.create_user(
            **validated_data
        )

    @staticmethod
    def reset_password(
        user,
        new_password,
    ):
        user.set_password(new_password)
        user.last_logout = timezone.now()
        user.save(
            update_fields=[
                "password",
                "last_logout",
                "updated_at",
            ]
        )

        return user

    @staticmethod
    def verify_current_password(
        user,
        current_password,
    ):
        if not authenticate(
            email=user.email,
            password=current_password,
        ):
            raise ValidationError(
                {
                    "current_password": "Current password is incorrect."
                }
            )

        return True

    @staticmethod
    def create_password_reset_token(user):
        # Invalidate previous unused tokens
        PasswordResetToken.objects.filter(
            user=user,
            is_used=False,
        ).update(is_used=True)

        token = secrets.token_urlsafe(48)

        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        return reset_token
#------Password Reset Link Generation------
    @staticmethod
    def get_password_reset_link(reset_token):
        return (
            f"{settings.FRONTEND_RESET_PASSWORD_URL}"
            f"?uuid={reset_token.user.uuid}"
            f"&token={reset_token.token}"
        )

    @staticmethod
    def verify_password_reset_user(uuid_value, email):
        try:
            user = CustomUser.objects.get(
                uuid=uuid_value,
                email__iexact=email,
            )
        except CustomUser.DoesNotExist:
            raise ValidationError({
                "detail": "Invalid user details."
            })

        if not user.is_active:
            raise ValidationError({
                "detail": "This account is inactive."
            })

        return user
        

    