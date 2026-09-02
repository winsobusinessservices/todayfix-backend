import secrets
from datetime import timedelta
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
    SignupOTPVerification,
)
# Import from new location for backward compatibility
from accounts.services.otp_service import SignupOTPService  # noqa: F401
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
        pending_registration_uuid,
        token,
    ):
        existing_user = CustomUser.objects.filter(
            user_uuid=pending_registration_uuid,
            is_verified=True,
        ).first()
        if existing_user:
            raise ValidationError({
                "detail": "User already verified. Please login."
            })
        pending_registration = PendingRegistration.objects.filter(
            pending_registration_uuid=pending_registration_uuid,
            token=token,
        ).first()
        if not pending_registration:
            raise ValidationError({
                "detail": "Invalid verification link."
            })
        if pending_registration.verification_method != "email":
            raise ValidationError({
                "detail": "This registration must be verified using phone OTP."
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
            user_uuid=pending_registration.pending_registration_uuid,
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
    # =========================================================
    # PHONE OTP REGISTRATION
    # =========================================================
    @staticmethod
    def verify_phone_registration(
        phone,
        otp,
    ):
        # -----------------------------------------------------
        # IMPORTANT FIX:
        #
        # Previously the query looked for the latest unused OTP
        # across the ENTIRE SignupOTPVerification table.
        #
        # That meant:
        #
        # User A -> 111111
        # User B -> 222222
        #
        # If User A verified while User B's OTP was the newest,
        # User A could accidentally get User B's OTP record.
        #
        # Now we explicitly restrict the lookup to the phone
        # supplied by the verification request.
        # -----------------------------------------------------
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
            raise ValidationError({
                "otp": (
                    "OTP not found. "
                    "Please request a new OTP."
                )
            })
        # -----------------------------------------------------
        # The phone is now taken from the validated request,
        # rather than being discovered from whichever OTP happens
        # to be the newest in the database.
        # -----------------------------------------------------
        success, message = SignupOTPService.verify_otp(
            phone=phone,
            otp=otp,
        )
        if not success:
            raise ValidationError({
                "otp": message
            })
        # -----------------------------------------------------
        # Find the pending registration belonging to the SAME
        # phone number that was used for OTP verification.
        # -----------------------------------------------------
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
            user_uuid=pending_registration.pending_registration_uuid,
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
    # PROFILE PHONE UPDATE - SEND OTP
    # =========================================================
    @staticmethod
    def create_phone_update_otp(user, phone):
        from accounts.services.otp_service import OTPService
        if CustomUser.objects.filter(
            phone=phone
        ).exclude(
            pk=user.pk
        ).exists():
            raise ValidationError({
                "phone": "Phone number already exists."
            })
        if not OTPService.can_send_otp(phone):
            raise ValidationError({
                "phone": (
                    "Please wait 60 seconds "
                    "before requesting another OTP."
                )
            })
        otp = OTPService.create_otp(
            user=user,
            phone=phone,
        )
        print(
            f"\n{'=' * 50}\n"
            f"PHONE UPDATE OTP\n"
            f"User: {user.user_uuid}\n"
            f"Phone: {phone}\n"
            f"OTP: {otp}\n"
            f"Expires: 5 minutes\n"
            f"{'=' * 50}\n"
        )
        return otp
    # =========================================================
    # PROFILE PHONE UPDATE - VERIFY OTP
    # =========================================================
    @staticmethod
    def verify_phone_update_otp(
        user,
        phone,
        otp,
    ):
        from accounts.services.otp_service import OTPService
        success, message = OTPService.verify_otp(
            user=user,
            phone=phone,
            otp=otp,
        )
        if not success:
            raise ValidationError({
                "otp": message
            })
        if CustomUser.objects.filter(
            phone=phone
        ).exclude(
            pk=user.pk
        ).exists():
            raise ValidationError({
                "phone": "Phone number already exists."
            })
        user.phone = phone
        user.save(
            update_fields=[
                "phone",
                "updated_at",
            ]
        )
        return user
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
            f"?user_uuid={reset_token.user.user_uuid}"
            f"&token={reset_token.token}"
        )
    # =========================================================
    # VERIFY PASSWORD RESET USER
    # =========================================================
    @staticmethod
    def verify_password_reset_user(
        user_uuid,
        email,
    ):
        try:
            user = CustomUser.objects.get(
                user_uuid=user_uuid,
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
