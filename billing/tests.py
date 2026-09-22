from django.test import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model
from bookings.models import Booking
from categories.models import Category, SubCategory
from services.models import Service, ServiceType, Unit
from business.models import BusinessProfile, BusinessApplication
from accounts.models import Address
from common.utils.money import quantize_money
from .models import PlatformFeeRule, BookingFeeRule, BillingRecord, BillingStatus
from .calculators import BillingCalculator
from .services import BillingService
from .choices import FeeType

User = get_user_model()

class BillingCalculatorTestCase(TestCase):
    def setUp(self):
        PlatformFeeRule.objects.create(minimum_amount=Decimal("0.00"), maximum_amount=Decimal("499.99"), percentage=Decimal("2.00"))
        PlatformFeeRule.objects.create(minimum_amount=Decimal("500.00"), maximum_amount=Decimal("999.99"), percentage=Decimal("3.00"))
        PlatformFeeRule.objects.create(minimum_amount=Decimal("1000.00"), maximum_amount=Decimal("1999.99"), percentage=Decimal("4.00"))
        PlatformFeeRule.objects.create(minimum_amount=Decimal("2000.00"), maximum_amount=None, percentage=Decimal("5.00"))
        
        BookingFeeRule.objects.create(minimum_amount=Decimal("0.00"), maximum_amount=Decimal("499.99"), fee_type=FeeType.FIXED_AMOUNT, fee_value=Decimal("0.00"))
        BookingFeeRule.objects.create(minimum_amount=Decimal("500.00"), maximum_amount=None, fee_type=FeeType.FIXED_AMOUNT, fee_value=Decimal("50.00"))

    def test_fee_under_500(self):
        calc = BillingCalculator(service_amount=Decimal("400.00"))
        res = calc.calculate()
        self.assertEqual(res["platform_fee"], Decimal("8.00")) # 2% of 400
        self.assertEqual(res["booking_fee"], Decimal("0.00"))

    def test_fee_exact_500(self):
        calc = BillingCalculator(service_amount=Decimal("500.00"))
        res = calc.calculate()
        self.assertEqual(res["platform_fee"], Decimal("15.00")) # 3% of 500
        self.assertEqual(res["booking_fee"], Decimal("50.00"))

    def test_fee_over_2000(self):
        calc = BillingCalculator(service_amount=Decimal("2500.00"), tip_amount=Decimal("100.00"))
        res = calc.calculate()
        self.assertEqual(res["platform_fee"], Decimal("125.00")) # 5% of 2500 (tip excluded from base)
        self.assertEqual(res["booking_fee"], Decimal("50.00"))
        # subtotal = 2500 + 125 + 50 = 2675
        self.assertEqual(res["subtotal"], Decimal("2675.00"))
        # gross = 2675
        self.assertEqual(res["gross_amount"], Decimal("2675.00"))
        # payable = 2675 + 100 = 2775
        self.assertEqual(res["payable_amount"], Decimal("2775.00"))
        # business gross = 2500 + 100 = 2600
        self.assertEqual(res["business_gross_amount"], Decimal("2600.00"))
        # business net = 2600 - 125 = 2475
        self.assertEqual(res["business_net_amount"], Decimal("2475.00"))


from rest_framework.test import APIClient
from django.urls import reverse
from bookings.models import Booking
from bookings.choices import BookingStatus
from instant_bookings.models import InstantBooking, InstantBookingStatus
from categories.models import Category
from business.models import BusinessProfile
from accounts.models import Address
from services.models import Service
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

class BillingIssuesTestCase(TestCase):
    def setUp(self):
        PlatformFeeRule.objects.all().delete()
        BookingFeeRule.objects.all().delete()
        
        self.customer = User.objects.create_user(username="cust", password="123", role="CUSTOMER")
        self.provider = User.objects.create_user(username="prov", password="123", role="BUSINESS")
        self.other_provider = User.objects.create_user(username="prov2", password="123", role="BUSINESS")
        self.admin = User.objects.create_user(username="admin", password="123", role="ADMIN")
        
        # We might not have all required fields for related models without full factories, 
        # but we mock what we can for unit testing the billing service and calculators.
        
        PlatformFeeRule.objects.create(minimum_amount=Decimal("0.00"), maximum_amount=Decimal("499.99"), percentage=Decimal("2.00"))
        PlatformFeeRule.objects.create(minimum_amount=Decimal("500.00"), maximum_amount=None, percentage=Decimal("5.00"))
        
        BookingFeeRule.objects.create(minimum_amount=Decimal("0.00"), maximum_amount=Decimal("499.99"), fee_type=FeeType.FIXED_AMOUNT, fee_value=Decimal("0.00"))
        BookingFeeRule.objects.create(minimum_amount=Decimal("500.00"), maximum_amount=None, fee_type=FeeType.FIXED_AMOUNT, fee_value=Decimal("50.00"))
        
    def test_fee_slabs(self):
        # D. Fee Slabs
        # Test open ended rule
        PlatformFeeRule.objects.filter(minimum_amount=Decimal("500.00")).update(is_active=False)
        with self.assertRaisesMessage(ValueError, "No applicable platform fee rule configured for this amount."):
            PlatformFeeCalculator.calculate_fee(Decimal("600.00"))
            
        with self.assertRaisesMessage(ValueError, "No applicable booking fee rule configured for this amount."):
            BookingFeeRule.objects.filter(minimum_amount=Decimal("500.00")).update(is_active=False)
            BookingFeeCalculator.calculate_fee(Decimal("600.00"))

    def test_instant_tip_override(self):
        # C. Instant Tip override
        # The logic is in calculate_from_instant_booking
        class MockInstantBooking:
            quoted_price = Decimal("1000.00")
            travel_charge = Decimal("0.00")
            tip_amount = Decimal("150.00")
            gst_percentage = Decimal("18.00")
        
        res1 = BillingService.calculate_from_instant_booking(MockInstantBooking())
        self.assertEqual(res1["tip_amount"], Decimal("150.00"))
        
        res2 = BillingService.calculate_from_instant_booking(MockInstantBooking(), tip_amount=Decimal("0.00"))
        self.assertEqual(res2["tip_amount"], Decimal("0.00"))
        
        res3 = BillingService.calculate_from_instant_booking(MockInstantBooking(), tip_amount=Decimal("200.00"))
        self.assertEqual(res3["tip_amount"], Decimal("200.00"))

    def test_amount_validation_negative(self):
        # A. Negative Amounts
        from billing.serializers import BillingPreviewRequestSerializer
        
        data = {
            "extended_service_amount": "-10.00"
        }
        serializer = BillingPreviewRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("extended_service_amount", serializer.errors)
        
        data2 = {
            "tip_amount": "-1.00"
        }
        serializer2 = BillingPreviewRequestSerializer(data=data2)
        self.assertFalse(serializer2.is_valid())
        self.assertIn("tip_amount", serializer2.errors)
