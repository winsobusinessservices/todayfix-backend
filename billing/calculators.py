from decimal import Decimal
from django.utils import timezone
from common.utils.money import quantize_money, calculate_percentage, add_money
from .models import PlatformFeeRule, BookingFeeRule, TravelFeeRule
from .choices import FeeType

class PlatformFeeCalculator:
    """
    Calculates the platform fee based on configured slabs.
    """
    @staticmethod
    def calculate_fee(base_amount: Decimal, booking_type: str = "BOTH") -> Decimal:
        base_amount = quantize_money(base_amount)
        if base_amount <= 0:
            return Decimal("0.00")
            
        now = timezone.now()
        # Find applicable rule
        # minimum_amount <= base_amount < maximum_amount (or maximum_amount is null)
        rules = PlatformFeeRule.objects.filter(is_active=True, effective_from__lte=now).exclude(effective_to__lt=now)

        # Filter by booking type, same convention as BookingFeeCalculator
        rules = rules.filter(booking_type__in=[booking_type, "BOTH"])
        
        applicable_rule = None
        for rule in rules.order_by("-minimum_amount"):
            if base_amount >= rule.minimum_amount:
                if rule.maximum_amount is None or base_amount <= rule.maximum_amount:
                    applicable_rule = rule
                    break
                    
        if not applicable_rule:
            raise ValueError("No applicable platform fee rule configured for this amount.")
            
        return calculate_percentage(base_amount, applicable_rule.percentage)


class BookingFeeCalculator:
    """
    Calculates the booking fee if conditions are met.
    """
    @staticmethod
    def calculate_fee(base_amount: Decimal, booking_type: str = "BOTH") -> Decimal:
        base_amount = quantize_money(base_amount)
        if base_amount <= 0:
            return Decimal("0.00")
            
        now = timezone.now()
        rules = BookingFeeRule.objects.filter(is_active=True, effective_from__lte=now).exclude(effective_to__lt=now)
        
        # Filter by booking type
        rules = rules.filter(booking_type__in=[booking_type, "BOTH"])
        
        applicable_rule = None
        for rule in rules.order_by("-minimum_amount"):
            if base_amount >= rule.minimum_amount:
                if rule.maximum_amount is None or base_amount <= rule.maximum_amount:
                    applicable_rule = rule
                    break
                    
        if not applicable_rule:
            raise ValueError("No applicable booking fee rule configured for this amount.")
            
        if applicable_rule.fee_type == FeeType.PERCENTAGE:
            return calculate_percentage(base_amount, applicable_rule.fee_value)
        else:
            return quantize_money(applicable_rule.fee_value)

class TravelFeeCalculator:
    """
    Calculates the travel charge from a distance using the single
    active global TravelFeeRule.
    """
    @staticmethod
    def calculate_fee(distance_km: Decimal) -> Decimal:
        from .models import TravelFeeRule

        distance_km = Decimal(str(distance_km))
        if distance_km <= 0:
            return Decimal("0.00")

        now = timezone.now()
        rule = (
            TravelFeeRule.objects.filter(is_active=True, effective_from__lte=now)
            .exclude(effective_to__lt=now)
            .order_by("-effective_from")
            .first()
        )

        if not rule:
            raise ValueError("No applicable travel fee rule configured.")

        chargeable_distance = max(Decimal("0.00"), distance_km - rule.free_distance_km)
        return quantize_money(chargeable_distance * rule.rate_per_km)

class BillingCalculator:
    """
    Core calculator for billing logic.
    Computes all totals, taxes, and fees.
    """
    
    def __init__(
        self,
        service_amount: Decimal = Decimal("0.00"),
        extended_service_amount: Decimal = Decimal("0.00"),
        material_amount: Decimal = Decimal("0.00"),
        travel_amount: Decimal = Decimal("0.00"),
        tip_amount: Decimal = Decimal("0.00"),
        fix_coin_discount: Decimal = Decimal("0.00"),
        gst_percentage: Decimal = Decimal("0.00"),
        booking_type: str = "BOTH",
    ):
        self.service_amount = quantize_money(service_amount)
        self.extended_service_amount = quantize_money(extended_service_amount)
        self.material_amount = quantize_money(material_amount)
        self.travel_amount = quantize_money(travel_amount)
        self.tip_amount = quantize_money(tip_amount)
        self.fix_coin_discount = quantize_money(fix_coin_discount)
        self.gst_percentage = quantize_money(gst_percentage)
        self.booking_type = booking_type
        
    def calculate(self) -> dict:
        # Base amount for platform fee and booking fee
        platform_fee_base = add_money(
            self.service_amount, 
            self.extended_service_amount, 
            self.material_amount, 
            self.travel_amount
        )
        
        # 1. Platform Fee
        platform_fee = PlatformFeeCalculator.calculate_fee(platform_fee_base, self.booking_type)
        
        # 2. Booking Fee
        booking_fee = BookingFeeCalculator.calculate_fee(platform_fee_base, self.booking_type)
        
        # 3. Subtotal (excluding tip)
        subtotal = add_money(platform_fee_base, platform_fee, booking_fee)
        
        # 4. Tax
        tax_amount = calculate_percentage(subtotal, self.gst_percentage)
        
        # 5. Gross Amount (Subtotal + Tax)
        gross_amount = add_money(subtotal, tax_amount)
        
        # 6. Payable Amount (Gross - Discounts + Tip)
        payable_amount = add_money(gross_amount, self.tip_amount) - self.fix_coin_discount
        if payable_amount < Decimal("0.00"):
            payable_amount = Decimal("0.00")
            
        # 7. Business Settlement
        # The business earns the service + extended + material + travel + tip
        # But the platform deducts its platform fee. 
        # (Assuming booking fee goes to platform)
        business_gross = add_money(platform_fee_base, self.tip_amount)
        business_net = business_gross - platform_fee
        if business_net < Decimal("0.00"):
            business_net = Decimal("0.00")
            
        return {
            "service_amount": self.service_amount,
            "extended_service_amount": self.extended_service_amount,
            "material_amount": self.material_amount,
            "travel_amount": self.travel_amount,
            "tip_amount": self.tip_amount,
            "platform_fee": platform_fee,
            "booking_fee": booking_fee,
            "subtotal": subtotal,
            "taxable_amount": subtotal,
            "tax_amount": tax_amount,
            "fix_coin_discount": self.fix_coin_discount,
            "discount_total": self.fix_coin_discount, # Can be expanded with promo codes later
            "gross_amount": gross_amount,
            "payable_amount": quantize_money(payable_amount),
            "business_gross_amount": business_gross,
            "business_deduction": platform_fee,
            "business_net_amount": business_net,
            "gst_percentage": self.gst_percentage,
            "booking_type": self.booking_type,
        }
