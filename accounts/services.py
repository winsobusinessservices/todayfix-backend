from datetime import timedelta
import secrets

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from accounts.choices import UserRole
from accounts.models import (
    CustomUser,
    PasswordResetToken,
    PendingRegistration,
)


class AuthService:

    # ---------------------------------------------------------
    # User Registration
    # ---------------------------------------------------------

    @staticmethod
    def register_user(validated_data):

        validated_data["role"] = UserRole.USER
        validated_data["has_business"] = False
        validated_data["business_verified"] = False

        email = validated_data["email"].lower().strip()
        phone = validated_data.get("phone")

        # Check whether a real account already exists.
        if CustomUser.objects.filter(
            email__iexact=email
        ).exists():
            raise ValidationError({
                "email": "Email already exists."
            })

        # Phone is optional.
        # Only check uniqueness when a phone number is provided.
        if phone and CustomUser.objects.filter(
            phone=phone
        ).exists():
            raise ValidationError({
                "phone": "Phone number already exists."
            })

        # Generate a new verification token.
        token = secrets.token_urlsafe(48)

        # Check whether an unverified registration
        # already exists for this email.
        pending_registration = PendingRegistration.objects.filter(
            email__iexact=email
        ).first()

        if pending_registration:

            # Update existing pending registration.
            pending_registration.first_name = validated_data[
                "first_name"
            ]

            pending_registration.last_name = validated_data.get(
                "last_name",
                ""
            )

            pending_registration.email = email

            pending_registration.phone = phone

            # Hash password before storing it.
            pending_registration.password = make_password(
                validated_data["password"]
            )

            # Replace old verification token.
            pending_registration.token = token

            # Give the new verification link another 24 hours.
            pending_registration.expires_at = (
                timezone.now() + timedelta(hours=24)
            )

            pending_registration.save()

        else:

            # Create a new pending registration.
            pending_registration = PendingRegistration.objects.create(
                first_name=validated_data["first_name"],
                last_name=validated_data.get(
                    "last_name",
                    ""
                ),
                email=email,
                phone=phone,
                password=make_password(
                    validated_data["password"]
                ),
                token=token,
                expires_at=(
                    timezone.now() + timedelta(hours=24)
                ),
            )

        return pending_registration

    # ---------------------------------------------------------
    # Email Verification
    # ---------------------------------------------------------

    @staticmethod
    def verify_email_registration(uuid_value, token):

        try:
            pending_registration = PendingRegistration.objects.get(
                uuid=uuid_value,
                token=token,
            )

        except PendingRegistration.DoesNotExist:

            raise ValidationError({
                "detail": "Invalid verification link."
            })

        # Check whether the verification link has expired.
        if timezone.now() > pending_registration.expires_at:

            pending_registration.delete()

            raise ValidationError({
                "detail": "Verification link has expired."
            })

        # Make sure the email has not already been registered.
        if CustomUser.objects.filter(
            email__iexact=pending_registration.email
        ).exists():

            pending_registration.delete()

            raise ValidationError({
                "detail": "An account with this email already exists."
            })

        # Phone is optional.
        # Only check uniqueness when a phone number exists.
        if (
            pending_registration.phone
            and CustomUser.objects.filter(
                phone=pending_registration.phone
            ).exists()
        ):

            pending_registration.delete()

            raise ValidationError({
                "detail": (
                    "An account with this phone number "
                    "already exists."
                )
            })

        # -----------------------------------------------------
        # Create the actual user.
        #
        # The password stored in PendingRegistration is already
        # hashed, so DO NOT use CustomUser.objects.create_user()
        # here because it would hash the password again.
        # -----------------------------------------------------

        user = CustomUser(
            uuid=pending_registration.uuid,
            first_name=pending_registration.first_name,
            last_name=pending_registration.last_name,
            email=pending_registration.email,
            phone=pending_registration.phone,
            role=UserRole.USER,
            has_business=False,
            business_verified=False,
            is_verified=True,
            verified_at=timezone.now(),
            is_active=True,
        )

        # Password is already hashed.
        user.password = pending_registration.password

        user.save()

        # Registration is now complete.
        pending_registration.delete()

        return user

    # ---------------------------------------------------------
    # Business Registration
    # ---------------------------------------------------------

    @staticmethod
    def register_business(validated_data):

        validated_data["role"] = UserRole.BUSINESS
        validated_data["has_business"] = True
        validated_data["business_verified"] = False

        return CustomUser.objects.create_user(
            **validated_data
        )

    # ---------------------------------------------------------
    # Reset Password
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Verify Current Password
    # ---------------------------------------------------------

    @staticmethod
    def verify_current_password(
        user,
        current_password,
    ):

        if not authenticate(
            email=user.email,
            password=current_password,
        ):

            raise ValidationError({
                "current_password": (
                    "Current password is incorrect."
                )
            })

        return True

    # ---------------------------------------------------------
    # Create Password Reset Token
    # ---------------------------------------------------------

    @staticmethod
    def create_password_reset_token(user):

        # Invalidate previous unused tokens.
        PasswordResetToken.objects.filter(
            user=user,
            is_used=False,
        ).update(
            is_used=True
        )

        token = secrets.token_urlsafe(48)

        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=(
                timezone.now() + timedelta(minutes=15)
            ),
        )

        return reset_token

    # ---------------------------------------------------------
    # Password Reset Link Generation
    # ---------------------------------------------------------

    @staticmethod
    def get_password_reset_link(reset_token):

        return (
            f"{settings.FRONTEND_RESET_PASSWORD_URL}"
            f"?uuid={reset_token.user.uuid}"
            f"&token={reset_token.token}"
        )

    # ---------------------------------------------------------
    # Verify Password Reset User
    # ---------------------------------------------------------

    @staticmethod
    def verify_password_reset_user(
        uuid_value,
        email,
    ):

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