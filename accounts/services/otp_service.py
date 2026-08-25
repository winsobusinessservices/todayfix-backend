"""
OTP service layer.

Handles OTP generation, hashing, verification,
rate limiting, and SMS provider integration.
"""

import logging
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import (
    make_password,
    check_password,
)
from django.utils import timezone

from accounts.models import (
    OTPVerification,
    SignupOTPVerification,
)

from .fast2sms import Fast2SMSProvider

logger = logging.getLogger(__name__)


def _get_sms_provider():
    """
    Factory for SMS provider.

    Returns the configured SMS provider instance.
    Replace this to switch providers without changing
    any other code.
    """
    return Fast2SMSProvider()


# =============================================================
# EXISTING USER OTP SERVICE (LOGIN)
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

        # Send via SMS provider
        provider = _get_sms_provider()
        result = provider.send_otp(phone, otp)

        otp_record = OTPVerification.objects.create(
            user=user,
            phone=phone,
            otp_hash=otp_hash,
            purpose=OTPVerification.PURPOSE_LOGIN,
            provider=getattr(
                provider,
                "PROVIDER_NAME",
                "FAST2SMS",
            ),
            provider_request_id=(
                result.provider_request_id
                if result
                else None
            ),
            expires_at=(
                timezone.now()
                + timedelta(
                    minutes=cls.OTP_EXPIRY_MINUTES
                )
            ),
        )

        logger.debug(
            "OTP created | phone=%s | record=%s | "
            "provider_request_id=%s",
            phone,
            otp_record.id,
            otp_record.provider_request_id,
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
        otp_record.is_verified = True
        otp_record.verified_at = timezone.now()

        otp_record.save(
            update_fields=[
                "is_used",
                "is_verified",
                "verified_at",
            ]
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

        # Send via SMS provider
        provider = _get_sms_provider()
        provider.send_otp(phone, otp)

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

        otp_record.save(
            update_fields=["is_used"]
        )

        return True, (
            "OTP verified successfully."
        )

