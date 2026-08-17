"""
Fast2SMS provider implementation.

Architecture is ready for real integration.
The actual HTTP call is a placeholder until the
real Fast2SMS OTP-ID behavior is confirmed.
"""

import logging

from django.conf import settings

from .sms_provider import BaseSMSProvider, SMSProviderResult

logger = logging.getLogger(__name__)


class Fast2SMSProvider(BaseSMSProvider):
    """
    Fast2SMS OTP provider.

    Reads FAST2SMS_API_KEY from Django settings.

    NOTE: The actual HTTP call is intentionally NOT
    implemented yet. The provider_request_id format
    depends on the real Fast2SMS API response which
    is pending confirmation.
    """

    PROVIDER_NAME = "FAST2SMS"

    def __init__(self):
        self.api_key = getattr(
            settings,
            "FAST2SMS_API_KEY",
            "",
        )

    def send_otp(self, phone, otp):
        """
        Send OTP via Fast2SMS.

        Currently a placeholder — returns success=True
        with provider_request_id=None.

        When the real Fast2SMS OTP-ID behavior is
        confirmed, this method will:
        1. POST to Fast2SMS API
        2. Parse the response
        3. Return the provider's request/OTP ID
        """

        if not self.api_key:
            logger.warning(
                "FAST2SMS_API_KEY not configured. "
                "OTP not sent to %s.",
                phone,
            )
            return SMSProviderResult(
                success=False,
                error_message=(
                    "SMS provider not configured."
                ),
            )

        # =====================================================
        # PLACEHOLDER: Real Fast2SMS API integration
        # =====================================================
        #
        # When ready, implement:
        #
        # import requests
        #
        # response = requests.post(
        #     "https://www.fast2sms.com/dev/bulkV2",
        #     headers={
        #         "authorization": self.api_key,
        #     },
        #     data={
        #         "route": "otp",
        #         "variables_values": otp,
        #         "numbers": phone,
        #     },
        # )
        #
        # data = response.json()
        #
        # return SMSProviderResult(
        #     success=data.get("return"),
        #     provider_request_id=data.get("request_id"),
        # )
        #
        # =====================================================

        logger.info(
            "Fast2SMS OTP placeholder | "
            "Phone: %s | OTP generation completed.",
            phone,
        )

        return SMSProviderResult(
            success=True,
            provider_request_id=None,
        )
