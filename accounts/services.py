import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from accounts.choices import UserRole
from accounts.models import (
    CustomUser,
    PasswordResetToken,
    PendingRegistration,
    OTPVerification,
    SignupOTPVerification,
)


class AuthService:

    # =========================================================
    # USER REGISTRATION
    # =========================================================

    @staticmethod
    def register_user(validated_data):

        validated_data["role"] = UserRole.USER
        validated_data["has_business"] = False
        validated_data["business_verified"] = False

        email = (
            validated_data.get("email")
            or None
        )

        if email:
            email = email.lower().strip()

        phone = (
            validated_data.get("phone")
            or None
        )

        if phone:
            phone = phone.strip()

        if phone:
            verification_method = "phone"
        else:
            verification_method = "email"

        # =====================================================
        # EMAIL OR PHONE IS REQUIRED
        # =====================================================

        if not email and not phone:
            raise ValidationError({
                "detail": (
                    "Either email or phone number "
                    "is required."
                )
            })

        # =====================================================
        # EMAIL DUPLICATE CHECK
        # =====================================================

        if email:

            if CustomUser.objects.filter(
                email__iexact=email
            ).exists():

                raise ValidationError({
                    "email": "Email already exists."
                })

        # =====================================================
        # PHONE DUPLICATE CHECK
        # =====================================================

        if phone:

            # Normalize phone
            if phone.startswith("+91"):
                phone = phone[3:]

            elif phone.startswith("91") and len(phone) == 12:
                phone = phone[2:]

            # Check normalized phone
            if CustomUser.objects.filter(
                phone=phone
            ).exists():

                raise ValidationError({
                    "phone": "Phone number already exists."
                })

            # Check legacy +91 stored value
            if CustomUser.objects.filter(
                phone=f"+91{phone}"
            ).exists():

                raise ValidationError({
                    "phone": "Phone number already exists."
                })

        # =====================================================
        # CREATE / UPDATE PENDING REGISTRATION
        # =====================================================

        token = secrets.token_urlsafe(48)

        pending_registration = (
            PendingRegistration.objects.filter(
                email__iexact=email
            ).first()
            if email
            else
            PendingRegistration.objects.filter(
                phone=phone
            ).first()
        )

        password_hash = make_password(
            validated_data["password"]
        )

        if pending_registration:

            pending_registration.first_name = (
                validated_data["first_name"]
            )

            pending_registration.last_name = (
                validated_data.get(
                    "last_name",
                    ""
                )
            )

            pending_registration.email = email

            pending_registration.phone = phone

            pending_registration.password = password_hash

            pending_registration.token = token

            pending_registration.verification_method = verification_method

            pending_registration.expires_at = (
                timezone.now()
                + timedelta(minutes=15)
            )

            pending_registration.save()

        else:

            pending_registration = (
                PendingRegistration.objects.create(
                    first_name=validated_data[
                        "first_name"
                    ],
                    last_name=validated_data.get(
                        "last_name",
                        ""
                    ),
                    email=email,
                    phone=phone,
                    password=password_hash,
                    token=token,
                    verification_method=verification_method,
                    expires_at=(
                        timezone.now()
                        + timedelta(minutes=15)
                    ),
                )
            )

        return pending_registration


    

    # =========================================================
    # EMAIL VERIFICATION
    # =========================================================

    @staticmethod
    def verify_email_registration(
        uuid_value,
        token,
    ):

        try:

            pending_registration = (
                PendingRegistration.objects.get(
                    uuid=uuid_value,
                    token=token,
                )
            )

            if pending_registration.verification_method != "email":
                raise ValidationError({
                    "detail": "This registration must be verified using phone OTP."
                })

        except PendingRegistration.DoesNotExist:

            raise ValidationError({
                "detail": "Invalid verification link."
            })

        # -----------------------------------------------------
        # Expiry
        # -----------------------------------------------------

        if timezone.now() > pending_registration.expires_at:

            pending_registration.delete()

            raise ValidationError({
                "detail": "Verification link has expired."
            })

        # -----------------------------------------------------
        # Email uniqueness
        # -----------------------------------------------------

        if (
            pending_registration.email
            and CustomUser.objects.filter(
                email__iexact=pending_registration.email
            ).exists()
        ):

            pending_registration.delete()

            raise ValidationError({
                "detail": (
                    "An account with this email "
                    "already exists."
                )
            })

        # -----------------------------------------------------
        # Phone uniqueness
        # -----------------------------------------------------

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
        # Create user
        # -----------------------------------------------------

        user = CustomUser(
            uuid=pending_registration.uuid,
            first_name=pending_registration.first_name,
            last_name=pending_registration.last_name,
            email=pending_registration.email,
            phone=pending_registration.phone or None,
            role=UserRole.USER,
            has_business=False,
            business_verified=False,
            is_verified=True,
            verified_at=timezone.now(),
            is_active=True,
        )

        # Password already hashed.
        user.password = pending_registration.password

        user.save()

        pending_registration.delete()

        return user

    # =========================================================
    # PHONE OTP REGISTRATION
    # =========================================================

    @staticmethod
    def verify_phone_registration(
        otp,
    ):

        otp_record = (
            SignupOTPVerification.objects
            .filter(
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp_record:
            raise ValidationError({
                "otp": "OTP not found. Please request a new OTP."
            })

        phone = otp_record.phone

        success, message = SignupOTPService.verify_otp(
            phone=phone,
            otp=otp,
        )

        if not success:
            raise ValidationError({
                "otp": message
            })

        try:

            pending_registration = (
                PendingRegistration.objects
                .filter(
                    phone=phone,
                    verification_method="phone",
                )
                .order_by("-created_at")
                .first()
            )
        except PendingRegistration.DoesNotExist:

            pending_registration = None

        if not pending_registration:

            raise ValidationError({
                "detail": (
                    "No pending registration found "
                    "for this phone number."
                )
            })

        # -----------------------------------------------------
        # Check phone uniqueness again
        # -----------------------------------------------------

        if CustomUser.objects.filter(
            phone=phone
        ).exists():

            pending_registration.delete()

            raise ValidationError({
                "phone": (
                    "An account with this phone number "
                    "already exists."
                )
            })

        # -----------------------------------------------------
        # Check email uniqueness if supplied
        # -----------------------------------------------------

        if (
            pending_registration.email
            and CustomUser.objects.filter(
                email__iexact=pending_registration.email
            ).exists()
        ):

            pending_registration.delete()

            raise ValidationError({
                "email": (
                    "An account with this email "
                    "already exists."
                )
            })

        # -----------------------------------------------------
        # Create actual user
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

        # Registration completed.
        pending_registration.delete()

        return user

    # =========================================================
    # BUSINESS REGISTRATION
    # =========================================================

    @staticmethod
    def register_business(validated_data):

        validated_data["role"] = UserRole.BUSINESS
        validated_data["has_business"] = True
        validated_data["business_verified"] = False

        return CustomUser.objects.create_user(
            **validated_data
        )

    # =========================================================
    # RESET PASSWORD
    # =========================================================

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

    # =========================================================
    # VERIFY CURRENT PASSWORD
    # =========================================================

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

    # =========================================================
    # PASSWORD RESET TOKEN
    # =========================================================

    @staticmethod
    def create_password_reset_token(user):

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
                timezone.now()
                + timedelta(minutes=15)
            ),
        )

        return reset_token

    # =========================================================
    # PASSWORD RESET LINK
    # =========================================================

    @staticmethod
    def get_password_reset_link(reset_token):

        return (
            f"{settings.FRONTEND_RESET_PASSWORD_URL}"
            f"?uuid={reset_token.user.uuid}"
            f"&token={reset_token.token}"
        )

    # =========================================================
    # VERIFY PASSWORD RESET USER
    # =========================================================

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


# =============================================================
# EXISTING USER OTP SERVICE
# =============================================================

class OTPService:

    OTP_EXPIRY_MINUTES = 5
    RESEND_COOLDOWN_SECONDS = 60
    MAX_ATTEMPTS = 5

    @staticmethod
    def normalize_phone(phone):

        phone = str(phone).strip()

        if phone.startswith("+91"):
            phone = phone[3:]

        if phone.startswith("91") and len(phone) == 12:
            phone = phone[2:]

        return phone

    @staticmethod
    def generate_otp():

        return f"{secrets.randbelow(1000000):06d}"

    @classmethod
    def can_send_otp(cls, phone):

        phone = cls.normalize_phone(phone)

        cooldown_time = (
            timezone.now()
            - timedelta(
                seconds=cls.RESEND_COOLDOWN_SECONDS
            )
        )

        return not OTPVerification.objects.filter(
            phone=phone,
            created_at__gte=cooldown_time,
            is_used=False,
        ).exists()

    @classmethod
    def create_otp(
        cls,
        user,
        phone,
    ):

        phone = cls.normalize_phone(phone)

        OTPVerification.objects.filter(
            user=user,
            is_used=False,
        ).update(
            is_used=True
        )

        otp = cls.generate_otp()

        otp_hash = make_password(otp)

        OTPVerification.objects.create(
            user=user,
            phone=phone,
            otp_hash=otp_hash,
            expires_at=(
                timezone.now()
                + timedelta(
                    minutes=cls.OTP_EXPIRY_MINUTES
                )
            ),
        )

        return otp

    @classmethod
    def verify_otp(
        cls,
        user,
        phone,
        otp,
    ):

        phone = cls.normalize_phone(phone)

        otp_record = (
            OTPVerification.objects
            .filter(
                user=user,
                phone=phone,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp_record:

            return False, (
                "OTP not found. "
                "Please request a new OTP."
            )

        if otp_record.attempts >= cls.MAX_ATTEMPTS:

            otp_record.is_used = True

            otp_record.save(
                update_fields=["is_used"]
            )

            return False, (
                "Too many incorrect attempts. "
                "Please request a new OTP."
            )

        if timezone.now() > otp_record.expires_at:

            otp_record.is_used = True

            otp_record.save(
                update_fields=["is_used"]
            )

            return False, (
                "OTP has expired. "
                "Please request a new OTP."
            )

        if not check_password(
            str(otp),
            otp_record.otp_hash,
        ):

            otp_record.attempts += 1

            otp_record.save(
                update_fields=["attempts"]
            )

            remaining = (
                cls.MAX_ATTEMPTS
                - otp_record.attempts
            )

            return False, (
                f"Invalid OTP. "
                f"{remaining} attempts remaining."
            )

        otp_record.is_used = True

        otp_record.save(
            update_fields=["is_used"]
        )

        return True, "OTP verified successfully."


# =============================================================
# SIGNUP OTP SERVICE
# =============================================================

class SignupOTPService:

    OTP_EXPIRY_MINUTES = 5
    RESEND_COOLDOWN_SECONDS = 60
    MAX_ATTEMPTS = 5

    @staticmethod
    def normalize_phone(phone):

        phone = str(phone).strip()

        if phone.startswith("+91"):
            phone = phone[3:]

        if phone.startswith("91") and len(phone) == 12:
            phone = phone[2:]

        return phone

    @staticmethod
    def generate_otp():

        return f"{secrets.randbelow(1000000):06d}"

    @classmethod
    def can_send_otp(cls, phone):

        phone = cls.normalize_phone(phone)

        cooldown_time = (
            timezone.now()
            - timedelta(
                seconds=cls.RESEND_COOLDOWN_SECONDS
            )
        )

        return not SignupOTPVerification.objects.filter(
            phone=phone,
            created_at__gte=cooldown_time,
            is_used=False,
        ).exists()

    @classmethod
    def create_otp(cls, phone):

        phone = cls.normalize_phone(phone)

        # -----------------------------------------------------
        # IMPORTANT:
        # Do NOT create another account here.
        # This only creates the OTP record.
        # -----------------------------------------------------

        SignupOTPVerification.objects.filter(
            phone=phone,
            is_used=False,
        ).update(
            is_used=True
        )

        otp = cls.generate_otp()

        otp_hash = make_password(otp)

        SignupOTPVerification.objects.create(
            phone=phone,
            otp_hash=otp_hash,
            expires_at=(
                timezone.now()
                + timedelta(
                    minutes=cls.OTP_EXPIRY_MINUTES
                )
            ),
        )

        return otp

    @classmethod
    def verify_otp(
        cls,
        phone,
        otp,
    ):

        phone = cls.normalize_phone(phone)

        otp_record = (
            SignupOTPVerification.objects
            .filter(
                phone=phone,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp_record:

            return False, (
                "OTP not found. "
                "Please request a new OTP."
            )

        if otp_record.attempts >= cls.MAX_ATTEMPTS:

            otp_record.is_used = True

            otp_record.save(
                update_fields=["is_used"]
            )

            return False, (
                "Too many incorrect attempts. "
                "Please request a new OTP."
            )

        if timezone.now() >= otp_record.expires_at:

            otp_record.is_used = True

            otp_record.save(
                update_fields=["is_used"]
            )

            return False, (
                "OTP has expired. "
                "Please request a new OTP."
            )

        if not check_password(
            str(otp),
            otp_record.otp_hash,
        ):

            otp_record.attempts += 1

            if otp_record.attempts >= cls.MAX_ATTEMPTS:
                otp_record.is_used = True

            otp_record.save(
                update_fields=[
                    "attempts",
                    "is_used",
                ]
            )

            remaining = (
                cls.MAX_ATTEMPTS
                - otp_record.attempts
            )

            if remaining > 0:

                return False, (
                    f"Invalid OTP. "
                    f"{remaining} attempts remaining."
                )

            return False, (
                "Too many incorrect attempts. "
                "Please request a new OTP."
            )

        otp_record.is_used = True

        # Only set this if your model has verified_at.
        # Your earlier model output showed:
        # id, phone, otp_hash, expires_at,
        # attempts, is_used, created_at
        #
        # Therefore DO NOT use verified_at here.

        otp_record.save(
            update_fields=["is_used"]
        )

        return True, (
            "OTP verified successfully."
        )
    
    


        