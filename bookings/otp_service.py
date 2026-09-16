"""
OTP service for confirming that a service is actually complete.

Used by both scheduled bookings (bookings app) and instant
bookings (instant_bookings app): the provider triggers an OTP
email to the customer, and the booking only moves to COMPLETED
once that OTP is verified. Mirrors the hashing/expiry/attempts
pattern used in accounts/services/otp_service.py, but is
email-based rather than SMS-based.
"""

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import BookingCompletionOTP

EMAIL_TEMPLATE_NAME = "SERVICE_COMPLETION_OTP"


class BookingCompletionOTPService:

    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 5

    @staticmethod
    def generate_otp():
        return f"{secrets.randbelow(1000000):06d}"

    @classmethod
    def _active_record(cls, booking=None, instant_booking=None):
        qs = BookingCompletionOTP.objects.filter(is_used=False)

        if booking is not None:
            qs = qs.filter(booking=booking)
        else:
            qs = qs.filter(instant_booking=instant_booking)

        return qs.order_by("-created_at").first()

    @classmethod
    def has_active_otp(cls, booking=None, instant_booking=None):
        """
        True if there's already an unexpired, unverified OTP
        pending for this booking.
        """
        record = cls._active_record(
            booking=booking,
            instant_booking=instant_booking,
        )

        return bool(record) and timezone.now() <= record.expires_at

    @classmethod
    def send_otp(cls, booking=None, instant_booking=None):
        """
        Creates a new completion OTP and emails it to the customer.

        Caller is responsible for checking has_active_otp() first
        so an unexpired OTP isn't silently replaced.
        """
        otp = cls.generate_otp()
        otp_hash = make_password(otp)

        record = BookingCompletionOTP.objects.create(
            booking=booking,
            instant_booking=instant_booking,
            otp_hash=otp_hash,
            expires_at=(
                timezone.now()
                + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
            ),
        )

        if booking is not None:
            from .services import BookingService

            BookingService._send_booking_email(
                booking,
                EMAIL_TEMPLATE_NAME,
                {
                    "business_name": booking.business.name,
                    "service_name": booking.service.name,
                },
                recipient=booking.user,
                otp=otp,
            )
        else:
            from instant_bookings.email_service import (
                send_instant_booking_email,
            )

            send_instant_booking_email(
                instant_booking,
                EMAIL_TEMPLATE_NAME,
                {
                    "business_name": (
                        instant_booking.assigned_business.name
                    ),
                    "service_name": (
                        instant_booking.requested_service_name
                    ),
                },
                recipient=instant_booking.customer,
                otp=otp,
            )

        return record

    @classmethod
    def verify_otp(cls, otp, booking=None, instant_booking=None):
        record = cls._active_record(
            booking=booking,
            instant_booking=instant_booking,
        )

        if not record:
            return False, (
                "OTP not found. Please click complete again to "
                "request one."
            )

        if record.attempts >= cls.MAX_ATTEMPTS:
            record.is_used = True
            record.save(update_fields=["is_used"])

            return False, (
                "Too many incorrect attempts. Please click complete "
                "again to request a new OTP."
            )

        if timezone.now() > record.expires_at:
            record.is_used = True
            record.save(update_fields=["is_used"])

            return False, (
                "OTP has expired. Please click complete again to "
                "request a new OTP."
            )

        if not check_password(str(otp), record.otp_hash):
            record.attempts += 1
            record.save(update_fields=["attempts"])

            remaining = cls.MAX_ATTEMPTS - record.attempts

            return False, (
                f"Invalid OTP. {remaining} attempts remaining."
            )

        record.is_used = True
        record.is_verified = True
        record.verified_at = timezone.now()
        record.save(
            update_fields=["is_used", "is_verified", "verified_at"]
        )

        return True, "OTP verified successfully."