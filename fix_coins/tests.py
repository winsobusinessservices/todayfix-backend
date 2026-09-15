import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.choices import UserRole
from accounts.models import GoogleIdentity, PendingRegistration, SignupOTPVerification
from accounts.services import AuthService
from fix_coins.choices import FixCoinReferenceType, FixCoinTransactionType
from fix_coins.models import FixCoinSettings, FixCoinTransaction, FixCoinWallet
from fix_coins.services import (
    calculate_booking_reward,
    calculate_coin_value_rupees,
    calculate_rupee_value,
    credit_coins,
    debit_coins,
    get_balance,
    get_fix_coin_settings,
    get_or_create_wallet,
    grant_signup_bonus,
    reverse_transaction,
    validate_redemption,
)

User = get_user_model()


class FixCoinModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="StrongPassword123!",
            first_name="Test",
            last_name="User",
        )

    def test_wallet_uuid_uniqueness(self):
        w1 = FixCoinWallet.objects.create(user=self.user)
        self.assertIsNotNone(w1.wallet_uuid)
        self.assertEqual(w1.available_coins, 0)

    def test_transaction_uuid_uniqueness(self):
        wallet = FixCoinWallet.objects.create(user=self.user)
        t1 = FixCoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=FixCoinTransactionType.SIGNUP_BONUS,
            coins=500,
            balance_before=0,
            balance_after=500,
        )
        t2 = FixCoinTransaction.objects.create(
            wallet=wallet,
            transaction_type=FixCoinTransactionType.BOOKING_REWARD,
            coins=50,
            balance_before=500,
            balance_after=550,
        )
        self.assertNotEqual(t1.transaction_uuid, t2.transaction_uuid)

    def test_settings_defaults(self):
        s = FixCoinSettings.objects.create()
        self.assertEqual(s.coins_per_rupee, 10)
        self.assertEqual(s.signup_bonus_coins, 500)
        self.assertEqual(s.reward_coins_per_100_rupees, 10)
        self.assertEqual(s.minimum_redemption_coins, 100)
        self.assertEqual(s.maximum_redemption_percentage, Decimal("15.00"))
        self.assertEqual(s.expiry_days, 180)
        self.assertTrue(s.is_active)

    def test_validation_of_negative_settings(self):
        s = FixCoinSettings(
            coins_per_rupee=0,  # Invalid: < 1
            maximum_redemption_percentage=Decimal("150.00"),  # Invalid: > 100
        )
        with self.assertRaises(ValidationError):
            s.clean()

    def test_wallet_cannot_logically_become_negative(self):
        wallet = FixCoinWallet.objects.create(user=self.user, available_coins=100)
        with self.assertRaises(ValidationError):
            debit_coins(self.user, 150, FixCoinTransactionType.REDEMPTION)


class FixCoinServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="serviceuser@example.com",
            password="StrongPassword123!",
            first_name="Service",
            last_name="User",
        )

    def test_create_and_get_wallet(self):
        wallet = get_or_create_wallet(self.user)
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.user, self.user)
        # Fetching existing returns same wallet
        wallet2 = get_or_create_wallet(self.user)
        self.assertEqual(wallet.pk, wallet2.pk)

    def test_signup_bonus_equals_500_coins(self):
        granted = grant_signup_bonus(self.user)
        self.assertTrue(granted)
        self.assertEqual(get_balance(self.user), 500)
        tx = FixCoinTransaction.objects.filter(wallet__user=self.user).first()
        self.assertEqual(tx.coins, 500)
        self.assertEqual(tx.transaction_type, FixCoinTransactionType.SIGNUP_BONUS)
        self.assertEqual(tx.balance_before, 0)
        self.assertEqual(tx.balance_after, 500)

    def test_signup_bonus_idempotency_and_duplicate_attempt(self):
        first_attempt = grant_signup_bonus(self.user)
        self.assertTrue(first_attempt)
        second_attempt = grant_signup_bonus(self.user)
        self.assertFalse(second_attempt)
        self.assertEqual(get_balance(self.user), 500)
        self.assertEqual(
            FixCoinTransaction.objects.filter(
                wallet__user=self.user,
                transaction_type=FixCoinTransactionType.SIGNUP_BONUS,
            ).count(),
            1,
        )

    def test_credit_and_debit_coins(self):
        credit_coins(self.user, 300, FixCoinTransactionType.PROMOTIONAL_BONUS, "Promo")
        self.assertEqual(get_balance(self.user), 300)

        debit_coins(self.user, 100, FixCoinTransactionType.REDEMPTION, "Used coins")
        self.assertEqual(get_balance(self.user), 200)

        wallet = get_or_create_wallet(self.user)
        self.assertEqual(wallet.lifetime_earned_coins, 300)
        self.assertEqual(wallet.lifetime_redeemed_coins, 100)

    def test_insufficient_balance_debit_rejection(self):
        credit_coins(self.user, 50, FixCoinTransactionType.ADMIN_ADJUSTMENT)
        with self.assertRaises(ValidationError):
            debit_coins(self.user, 100, FixCoinTransactionType.REDEMPTION)

    def test_exact_balance_debit(self):
        credit_coins(self.user, 100, FixCoinTransactionType.ADMIN_ADJUSTMENT)
        debit_coins(self.user, 100, FixCoinTransactionType.REDEMPTION)
        self.assertEqual(get_balance(self.user), 0)

    def test_negative_debit_and_credit_rejection(self):
        with self.assertRaises(ValidationError):
            credit_coins(self.user, -50, FixCoinTransactionType.ADMIN_ADJUSTMENT)
        with self.assertRaises(ValidationError):
            debit_coins(self.user, -50, FixCoinTransactionType.REDEMPTION)

    def test_coin_to_rupee_calculation_and_rounding(self):
        # 10 coins = ₹1
        self.assertEqual(calculate_rupee_value(10), Decimal("1.00"))
        self.assertEqual(calculate_rupee_value(100), Decimal("10.00"))
        self.assertEqual(calculate_rupee_value(500), Decimal("50.00"))
        self.assertEqual(calculate_rupee_value(1000), Decimal("100.00"))
        self.assertEqual(calculate_coin_value_rupees(1250), Decimal("125.00"))

    def test_reward_calculation(self):
        # 10 coins per ₹100
        self.assertEqual(calculate_booking_reward(Decimal("100.00")), 10)
        self.assertEqual(calculate_booking_reward(Decimal("500.00")), 50)
        self.assertEqual(calculate_booking_reward(Decimal("1000.00")), 100)
        self.assertEqual(calculate_booking_reward(Decimal("99.99")), 0)
        self.assertEqual(calculate_booking_reward(Decimal("250.00")), 20)

    def test_redemption_validation(self):
        credit_coins(self.user, 1000, FixCoinTransactionType.SIGNUP_BONUS)
        # Booking ₹1000, 15% max = ₹150 = 1500 coins max. User requests 500 coins = ₹50
        res = validate_redemption(self.user, Decimal("1000.00"), 500)
        self.assertEqual(res["requested_coins"], 500)
        self.assertEqual(res["discount_amount"], "50.00")
        self.assertEqual(res["remaining_coins"], 500)
        self.assertEqual(res["maximum_redeemable_coins"], 1500)

    def test_minimum_redemption_validation(self):
        credit_coins(self.user, 500, FixCoinTransactionType.SIGNUP_BONUS)
        with self.assertRaises(ValidationError):
            validate_redemption(self.user, Decimal("1000.00"), 50)  # Below 100 min

    def test_maximum_redemption_validation(self):
        credit_coins(self.user, 2000, FixCoinTransactionType.ADMIN_ADJUSTMENT)
        # For ₹1000 eligible amount, 15% max is ₹150 (1500 coins). Requesting 1600 should fail.
        with self.assertRaises(ValidationError):
            validate_redemption(self.user, Decimal("1000.00"), 1600)

    def test_reverse_transaction(self):
        tx = credit_coins(self.user, 200, FixCoinTransactionType.PROMOTIONAL_BONUS)
        self.assertEqual(get_balance(self.user), 200)
        rev_tx = reverse_transaction(str(tx.transaction_uuid), "Cancelled campaign")
        self.assertEqual(rev_tx.transaction_type, FixCoinTransactionType.REFUND_REVERSAL)
        self.assertEqual(rev_tx.coins, -200)
        self.assertEqual(get_balance(self.user), 0)


class FixCoinAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="apiuser@example.com",
            password="StrongPassword123!",
            first_name="API",
            last_name="User",
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

    def test_balance_without_authentication(self):
        response = self.client.get(reverse("fix-coins-balance"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_balance_authenticated(self):
        credit_coins(self.user, 500, FixCoinTransactionType.SIGNUP_BONUS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get(reverse("fix-coins-balance"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["available_coins"], 500)
        self.assertEqual(response.data["data"]["coin_value_rupees"], "50.00")

    def test_history_without_authentication(self):
        response = self.client.get(reverse("fix-coins-history"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_history_authenticated(self):
        credit_coins(self.user, 500, FixCoinTransactionType.SIGNUP_BONUS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get(reverse("fix-coins-history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["transaction_type"], "SIGNUP_BONUS")
        self.assertEqual(results[0]["coins"], 500)

    def test_redemption_preview_without_authentication(self):
        response = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "1000.00", "coins_to_redeem": 500},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_redemption_preview_success(self):
        credit_coins(self.user, 500, FixCoinTransactionType.SIGNUP_BONUS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "1000.00", "coins_to_redeem": 500},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["discount_amount"], "50.00")
        self.assertEqual(response.data["data"]["remaining_coins"], 0)

    def test_redemption_preview_below_minimum(self):
        credit_coins(self.user, 500, FixCoinTransactionType.SIGNUP_BONUS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "1000.00", "coins_to_redeem": 50},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("coins_to_redeem", response.data["errors"])

    def test_redemption_preview_above_maximum(self):
        credit_coins(self.user, 2000, FixCoinTransactionType.ADMIN_ADJUSTMENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "1000.00", "coins_to_redeem": 1600},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("coins_to_redeem", response.data["errors"])

    def test_redemption_preview_insufficient_balance(self):
        credit_coins(self.user, 200, FixCoinTransactionType.SIGNUP_BONUS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "1000.00", "coins_to_redeem": 500},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("coins_to_redeem", response.data["errors"])

    def test_redemption_preview_zero_and_negative_amount(self):
        credit_coins(self.user, 500, FixCoinTransactionType.SIGNUP_BONUS)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        res_zero = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "0.00", "coins_to_redeem": 100},
            format="json",
        )
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)

        res_neg = self.client.post(
            reverse("fix-coins-redeem-preview"),
            {"eligible_amount": "-500.00", "coins_to_redeem": 100},
            format="json",
        )
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)


class SignupBonusIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("accounts.services_legacy.send_welcome_email")
    def test_phone_signup_receives_exactly_500_coins(self, mock_welcome):
        from django.contrib.auth.hashers import make_password
        from django.utils import timezone
        from datetime import timedelta

        phone = "9876543210"
        otp = "123456"
        SignupOTPVerification.objects.create(
            phone=phone,
            otp_hash=make_password(otp),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        PendingRegistration.objects.create(
            pending_registration_uuid=uuid.uuid4(),
            first_name="Phone",
            last_name="User",
            phone=phone,
            verification_method="phone",
            password="hashedpassword123",
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        user = AuthService.verify_phone_registration(phone=phone, otp=otp)
        self.assertEqual(get_balance(user), 500)

        # Repeating bonus call does not award duplicate
        grant_signup_bonus(user)
        self.assertEqual(get_balance(user), 500)

    @patch("accounts.services_legacy.send_welcome_email")
    def test_email_signup_receives_exactly_500_coins(self, mock_welcome):
        from django.utils import timezone
        from datetime import timedelta

        reg_uuid = uuid.uuid4()
        token = "testtoken123"
        PendingRegistration.objects.create(
            pending_registration_uuid=reg_uuid,
            first_name="Email",
            last_name="User",
            email="emailuser@example.com",
            verification_method="email",
            token=token,
            expires_at=timezone.now() + timedelta(minutes=15),
            password="hashedpassword123",
        )

        user = AuthService.verify_email_registration(
            pending_registration_uuid=reg_uuid,
            token=token,
        )
        self.assertEqual(get_balance(user), 500)

        # Repeating bonus call does not award duplicate
        grant_signup_bonus(user)
        self.assertEqual(get_balance(user), 500)

    @patch("accounts.api.views.id_token.verify_oauth2_token")
    def test_google_signup_new_user_gets_coins_and_existing_does_not(self, mock_verify):
        google_email = "newgoogleuser@example.com"
        google_sub = "google_sub_123456"

        mock_verify.return_value = {
            "sub": google_sub,
            "email": google_email,
            "email_verified": "true",
            "given_name": "Google",
            "family_name": "User",
            "picture": "http://example.com/pic.jpg",
        }

        # 1. First login -> Genuine new user created -> Receives 500 Fix-Coins
        res1 = self.client.post(
            "/api/auth/google/",
            {"credential": "mock_credential_token"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        user = User.objects.get(email=google_email)
        self.assertEqual(get_balance(user), 500)

        # 2. Second login -> Existing user -> DOES NOT receive extra coins
        res2 = self.client.post(
            "/api/auth/google/",
            {"credential": "mock_credential_token"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(get_balance(user), 500)
        self.assertEqual(
            FixCoinTransaction.objects.filter(
                wallet__user=user,
                transaction_type=FixCoinTransactionType.SIGNUP_BONUS,
            ).count(),
            1,
        )
