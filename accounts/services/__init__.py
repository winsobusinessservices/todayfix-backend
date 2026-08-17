"""
accounts.services package.

Re-exports all service classes for backward compatibility.
Existing imports like:
    from accounts.services import AuthService, OTPService
continue to work unchanged.
"""

from accounts.services_legacy import AuthService  # noqa: F401

from accounts.services.otp_service import (  # noqa: F401
    OTPService,
    SignupOTPService,
)
