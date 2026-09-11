"""
SMS Provider abstraction layer.

All SMS providers must implement BaseSMSProvider.
"""

import abc


class SMSProviderResult:
    """Result from an SMS provider send operation."""

    def __init__(
        self,
        success,
        external_request_id=None,
        error_message="",
        status_code=None,
    ):
        self.success = success
        self.external_request_id = external_request_id
        self.error_message = error_message
        self.status_code = status_code

    def __repr__(self):
        return (
            f"SMSProviderResult("
            f"success={self.success}, "
            f"external_request_id={self.external_request_id}, "
            f"status_code={self.status_code})"
        )


class BaseSMSProvider(abc.ABC):
    """
    Abstract base class for SMS providers.

    Implement send_otp() to integrate a new provider.
    """

    @abc.abstractmethod
    def send_otp(self, phone, otp):
        """
        Send an OTP to the given phone number.

        Args:
            phone: 10-digit Indian mobile number (normalized).
            otp: 6-digit OTP string.

        Returns:
            SMSProviderResult
        """
        raise NotImplementedError
