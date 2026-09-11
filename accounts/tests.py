from django.test import TestCase
from unittest.mock import patch
from django.conf import settings
import requests

from accounts.services.sms import SMSProvider
from accounts.models import OTPVerification, SignupOTPVerification
from accounts.services.otp_service import OTPService, SignupOTPService

# Ensure we have a user model for OTP tests
from django.contrib.auth import get_user_model
User = get_user_model()


class SMSProviderTests(TestCase):

    def setUp(self):
        self.provider = SMSProvider()
        # Mock settings
        self.provider.api_url = "https://api.amazesms.com/api/sms"
        self.provider.api_key = "test_key"
        self.provider.sender_id = "test_sender"
        self.provider.template_id = "test_template"
        self.provider.entity_id = "test_entity"
        self.provider.timeout = 10

    def test_missing_api_key(self):
        self.provider.api_key = ""
        result = self.provider.send_otp("9999999999", "123456")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "SMS service is not configured.")

    def test_missing_api_url(self):
        self.provider.api_url = ""
        result = self.provider.send_otp("9999999999", "123456")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "SMS service is not configured.")

    def test_missing_sender_id(self):
        self.provider.sender_id = ""
        result = self.provider.send_otp("9999999999", "123456")
        self.assertFalse(result.success)

    def test_missing_template_id(self):
        self.provider.template_id = ""
        result = self.provider.send_otp("9999999999", "123456")
        self.assertFalse(result.success)

    def test_missing_entity_id(self):
        self.provider.entity_id = ""
        result = self.provider.send_otp("9999999999", "123456")
        self.assertFalse(result.success)

    @patch("accounts.services.sms.requests.get")
    def test_successful_sms_request(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "success"}

        result = self.provider.send_otp("9999999999", "123456")
        
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        mock_get.assert_called_once()
        
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], self.provider.api_url)
        self.assertEqual(kwargs["params"]["key"], "test_key")
        self.assertEqual(kwargs["params"]["from"], "test_sender")
        self.assertEqual(kwargs["params"]["to"], "9999999999")
        self.assertIn("123456 is your OTP", kwargs["params"]["body"])
        self.assertEqual(kwargs["params"]["templateid"], "test_template")
        self.assertEqual(kwargs["params"]["entityid"], "test_entity")
        self.assertEqual(kwargs["timeout"], 10)

    @patch("accounts.services.sms.requests.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout

        result = self.provider.send_otp("9999999999", "123456")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Unable to send OTP. Please try again later.")

    @patch("accounts.services.sms.requests.get")
    def test_connection_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError

        result = self.provider.send_otp("9999999999", "123456")
        
        self.assertFalse(result.success)

    @patch("accounts.services.sms.requests.get")
    def test_http_error(self, mock_get):
        mock_get.return_value.status_code = 500
        
        result = self.provider.send_otp("9999999999", "123456")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 500)

    @patch("accounts.services.sms.requests.get")
    def test_unexpected_response(self, mock_get):
        mock_get.side_effect = Exception("Unexpected")
        
        result = self.provider.send_otp("9999999999", "123456")
        
        self.assertFalse(result.success)


class OTPServiceTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create(email="test@example.com", phone="9999999999")
        self.phone = "9999999999"

    @patch("accounts.services.sms.SMSProvider.send_otp")
    def test_login_otp_success(self, mock_send_otp):
        from accounts.services.sms_provider import SMSProviderResult
        mock_send_otp.return_value = SMSProviderResult(success=True)

        otp = OTPService.create_otp(self.user, self.phone)
        
        self.assertIsNotNone(otp)
        self.assertTrue(OTPVerification.objects.filter(user=self.user, phone=self.phone).exists())

    @patch("accounts.services.sms.SMSProvider.send_otp")
    def test_login_otp_sms_failure(self, mock_send_otp):
        from accounts.services.sms_provider import SMSProviderResult
        from rest_framework.exceptions import ValidationError
        
        mock_send_otp.return_value = SMSProviderResult(success=False, error_message="Failed")

        with self.assertRaises(ValidationError):
            OTPService.create_otp(self.user, self.phone)
            
        # Ensure no usable OTP record was created
        self.assertFalse(OTPVerification.objects.filter(user=self.user, phone=self.phone, is_used=False).exists())

    @patch("accounts.services.sms.SMSProvider.send_otp")
    def test_signup_otp_success(self, mock_send_otp):
        from accounts.services.sms_provider import SMSProviderResult
        mock_send_otp.return_value = SMSProviderResult(success=True)

        otp = SignupOTPService.create_otp("8888888888")
        
        self.assertIsNotNone(otp)
        self.assertTrue(SignupOTPVerification.objects.filter(phone="8888888888").exists())

    @patch("accounts.services.sms.SMSProvider.send_otp")
    def test_signup_otp_sms_failure(self, mock_send_otp):
        from accounts.services.sms_provider import SMSProviderResult
        from rest_framework.exceptions import ValidationError
        
        mock_send_otp.return_value = SMSProviderResult(success=False, error_message="Failed")

        with self.assertRaises(ValidationError):
            SignupOTPService.create_otp("8888888888")
            
        # Ensure no usable OTP record was created
        self.assertFalse(SignupOTPVerification.objects.filter(phone="8888888888", is_used=False).exists())
