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
