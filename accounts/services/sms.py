import logging
import requests

from django.conf import settings

from .sms_provider import BaseSMSProvider, SMSProviderResult


logger = logging.getLogger(__name__)


class SMSProvider(BaseSMSProvider):
    """
    Generic SMS service implementation.
    """

    def __init__(self):
        self.api_url = getattr(settings, "SMS_API_URL", "")
        self.api_key = getattr(settings, "SMS_API_KEY", "")
        self.sender_id = getattr(settings, "SMS_SENDER_ID", "")
        self.template_id = getattr(settings, "SMS_TEMPLATE_ID", "")
        self.entity_id = getattr(settings, "SMS_ENTITY_ID", "")
        self.timeout = getattr(settings, "SMS_TIMEOUT", 10)

    def send_otp(self, phone: str, otp: str) -> SMSProviderResult:
        """
        Send OTP using the configured SMS GET API.
        """

        if not all(
            [
                self.api_url,
                self.api_key,
                self.sender_id,
                self.template_id,
                self.entity_id,
            ]
        ):
            logger.warning(
                "SMS service is not fully configured. "
                "OTP not sent to phone ending %s.",
                phone[-4:],
            )

            return SMSProviderResult(
                success=False,
                error_message="SMS service is not configured.",
            )

        message = (
            f"{otp} is your OTP for verifying your mobile number and "
            f"completing registration with TodayFix a product of winso "
            f"business services private limited. It is valid for 5 minutes. "
            f"Please do not share this OTP with anyone"
        )

        params = {
            "key": self.api_key,
            "from": self.sender_id,
            "to": phone,
            "body": message,
            "templateid": self.template_id,
            "entityid": self.entity_id,
        }

        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=self.timeout,
            )

            print("\n========== SMS API DEBUG ==========")
            print("API URL:", self.api_url)
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            print("===================================\n")

            # Never log response.url because the API key is
            # included in the query string.

            logger.info(
                "SMS API request completed | status=%s | phone ending %s",
                response.status_code,
                phone[-4:],
            )

            if response.status_code != 200:
                logger.error(
                    "SMS API request failed | status=%s | phone ending %s",
                    response.status_code,
                    phone[-4:],
                )

                return SMSProviderResult(
                    success=False,
                    error_message=(
                        "Unable to send OTP. Please try again later."
                    ),
                    status_code=response.status_code,
                )

            # Temporary response logging while integration is being tested.
            # Remove or reduce this after the API response format is confirmed.
            logger.warning(
                "SMS API response | status=%s | body=%s",
                response.status_code,
                response.text[:1000],
            )

            return SMSProviderResult(
                success=True,
                external_request_id=None,
                status_code=response.status_code,
            )

        except requests.Timeout:
            logger.error(
                "SMS API request timed out for phone ending %s",
                phone[-4:],
            )

            return SMSProviderResult(
                success=False,
                error_message=(
                    "Unable to send OTP. Please try again later."
                ),
            )

        except requests.ConnectionError:
            logger.error(
                "SMS API connection error for phone ending %s",
                phone[-4:],
            )

            return SMSProviderResult(
                success=False,
                error_message=(
                    "Unable to send OTP. Please try again later."
                ),
            )

        except requests.RequestException:
            logger.error(
                "SMS API request failed for phone ending %s",
                phone[-4:],
            )

            return SMSProviderResult(
                success=False,
                error_message=(
                    "Unable to send OTP. Please try again later."
                ),
            )

        except Exception:
            logger.exception(
                "Unexpected error during SMS request "
                "for phone ending %s",
                phone[-4:],
            )

            return SMSProviderResult(
                success=False,
                error_message=(
                    "Unable to send OTP. Please try again later."
                ),
            )
