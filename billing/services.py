import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import BillingRecord, BillingItem
from .calculators import BillingCalculator
from .choices import BillingStatus, BookingType

logger = logging.getLogger(__name__)

class BillingService:
    @staticmethod
    def _validate_amounts(extended, material, travel, tip):
        if extended < 0 or material < 0 or travel < 0 or tip < 0:
            raise ValueError("Amounts cannot be negative.")

    @staticmethod
    def validate_billable_booking(booking=None, instant_booking=None):
        from bookings.choices import BookingStatus
        from instant_bookings.models import InstantBookingStatus
        
        if booking:
            if booking.status in [BookingStatus.CANCELLED, BookingStatus.REJECTED]:
                raise ValueError("Billing cannot be created for a cancelled booking.")
        elif instant_booking:
            if instant_booking.status in [InstantBookingStatus.CANCELLED, InstantBookingStatus.EXPIRED, InstantBookingStatus.NO_PROVIDER]:
                raise ValueError("Billing cannot be created for a cancelled booking.")

    @staticmethod
    def _create_billing_items(record: BillingRecord):
        from .choices import BillingItemType
        items_to_create = []
        
        components = [
            (BillingItemType.SERVICE, "Service Charge", record.service_amount, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.EXTENDED_SERVICE, "Extended Service", record.extended_service_amount, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.MATERIAL, "Material Charge", record.material_amount, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.TRAVEL, "Travel Charge", record.travel_amount, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.TIP, "Tip", record.tip_amount, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.PLATFORM_FEE, "Platform Fee", record.platform_fee, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.BOOKING_FEE, "Booking Fee", record.booking_fee, Decimal("0.00"), Decimal("0.00")),
            (BillingItemType.TAX, "Tax", record.tax_amount, record.tax_amount, record.calculation_snapshot.get("gst_percentage", Decimal("0.00"))),
        ]
        
        if record.fix_coin_discount > 0:
            components.append((BillingItemType.DISCOUNT, "Fix Coins Discount", -record.fix_coin_discount, Decimal("0.00"), Decimal("0.00")))
            
        for item_type, desc, amount, tax_amt, tax_rate in components:
            if amount != Decimal("0.00"):
                items_to_create.append(BillingItem(
                    billing=record,
                    item_type=item_type,
                    description=desc,
                    quantity=Decimal("1.00"),
                    unit_price=amount,
                    tax_rate=tax_rate,
                    tax_amount=tax_amt,
                    line_amount=amount
                ))
                
        if items_to_create:
            BillingItem.objects.bulk_create(items_to_create)

    @staticmethod
    def calculate_from_booking(booking, **kwargs) -> dict:
        """
        Calculates billing components based on a standard Booking.
        kwargs can contain dynamic items like extended_service, material, tip.
        """
        service_amount = booking.price
        
        # Determine defaults or passed in kwargs
        extended_service = kwargs.get("extended_service_amount", Decimal("0.00"))
        material = kwargs.get("material_amount", Decimal("0.00"))
        travel = kwargs.get("travel_amount", Decimal("0.00"))
        tip = kwargs.get("tip_amount", Decimal("0.00"))
        gst_percentage = kwargs.get("gst_percentage", Decimal("18.00")) # Default 18% if not passed
        
        BillingService._validate_amounts(extended_service, material, travel, tip)
        
        # fix_coin_discount will be handled in Phase 4 integration, but we can accept it for preview
        fix_coin_discount = kwargs.get("fix_coin_discount", Decimal("0.00"))
        
        calculator = BillingCalculator(
            service_amount=service_amount,
            extended_service_amount=extended_service,
            material_amount=material,
            travel_amount=travel,
            tip_amount=tip,
            fix_coin_discount=fix_coin_discount,
            gst_percentage=gst_percentage,
            booking_type=BookingType.SCHEDULED,
        )
        return calculator.calculate()
        
    @staticmethod
    def calculate_from_instant_booking(instant_booking, **kwargs) -> dict:
        """
        Calculates billing components based on an InstantBooking.
        """
        service_amount = instant_booking.quoted_price
        travel = instant_booking.travel_charge
        tip = instant_booking.tip_amount
        gst_percentage = instant_booking.gst_percentage
        
        extended_service = kwargs.get("extended_service_amount", Decimal("0.00"))
        material = kwargs.get("material_amount", Decimal("0.00"))
        
        # Override tip if provided dynamically
        tip = kwargs.get("tip_amount", tip)
        
        BillingService._validate_amounts(extended_service, material, travel, tip)
        
        fix_coin_discount = kwargs.get("fix_coin_discount", Decimal("0.00"))
        
        calculator = BillingCalculator(
            service_amount=service_amount,
            extended_service_amount=extended_service,
            material_amount=material,
            travel_amount=travel,
            tip_amount=tip,
            fix_coin_discount=fix_coin_discount,
            gst_percentage=gst_percentage,
            booking_type=BookingType.INSTANT,
        )
        return calculator.calculate()

    @staticmethod
    @transaction.atomic
    def create_billing_record(booking=None, instant_booking=None, **kwargs) -> BillingRecord:
        if bool(booking) == bool(instant_booking):
            raise ValueError("Provide exactly one of booking or instant_booking.")
            
        BillingService.validate_billable_booking(booking, instant_booking)
            
        if booking:
            existing_draft = BillingRecord.objects.filter(booking=booking, status=BillingStatus.DRAFT).first()
            if existing_draft:
                return existing_draft
            calc_result = BillingService.calculate_from_booking(booking, **kwargs)
        else:
            existing_draft = BillingRecord.objects.filter(instant_booking=instant_booking, status=BillingStatus.DRAFT).first()
            if existing_draft:
                return existing_draft
            calc_result = BillingService.calculate_from_instant_booking(instant_booking, **kwargs)
            
        record = BillingRecord.objects.create(
            booking=booking,
            instant_booking=instant_booking,
            service_amount=calc_result["service_amount"],
            extended_service_amount=calc_result["extended_service_amount"],
            material_amount=calc_result["material_amount"],
            travel_amount=calc_result["travel_amount"],
            tip_amount=calc_result["tip_amount"],
            platform_fee=calc_result["platform_fee"],
            booking_fee=calc_result["booking_fee"],
            subtotal=calc_result["subtotal"],
            taxable_amount=calc_result["taxable_amount"],
            tax_amount=calc_result["tax_amount"],
            fix_coin_discount=calc_result["fix_coin_discount"],
            discount_total=calc_result["discount_total"],
            gross_amount=calc_result["gross_amount"],
            payable_amount=calc_result["payable_amount"],
            business_gross_amount=calc_result["business_gross_amount"],
            business_deduction=calc_result["business_deduction"],
            business_net_amount=calc_result["business_net_amount"],
            status=BillingStatus.DRAFT,
            calculation_snapshot=calc_result,
        )
        
        BillingService._create_billing_items(record)
        
        return record

    @staticmethod
    @transaction.atomic
    def finalize_billing(billing_record: BillingRecord) -> BillingRecord:
        """
        Locks the billing record snapshot.
        Once finalized, the core amounts should not change. Any further additions need an adjustment version.
        """
        if billing_record.status == BillingStatus.FINALIZED:
            return billing_record # Idempotent
            
        if billing_record.status not in [BillingStatus.DRAFT, BillingStatus.CALCULATED]:
            raise ValueError(f"Cannot finalize billing in state {billing_record.status}")
            
        billing_record.status = BillingStatus.FINALIZED
        billing_record.finalized_at = timezone.now()
        billing_record.save(update_fields=["status", "finalized_at", "updated_at"])
        
        return billing_record

    @staticmethod
    @transaction.atomic
    def adjust_billing(billing_record: BillingRecord, **kwargs) -> BillingRecord:
        """
        Creates a new billing version (adjustment) if final amount changes after booking.
        """
        if billing_record.status != BillingStatus.FINALIZED:
            raise ValueError("Only finalized billing records can be adjusted.")
            
        # Update current record status to adjusted
        billing_record.status = BillingStatus.ADJUSTED
        billing_record.save(update_fields=["status", "updated_at"])
        
        # Create a new version
        new_version = billing_record.version + 1
        
        booking = billing_record.booking
        instant_booking = billing_record.instant_booking
        
        BillingService.validate_billable_booking(booking, instant_booking)
        
        if booking:
            calc_result = BillingService.calculate_from_booking(booking, **kwargs)
        else:
            calc_result = BillingService.calculate_from_instant_booking(instant_booking, **kwargs)
            
        adjusted_record = BillingRecord.objects.create(
            booking=booking,
            instant_booking=instant_booking,
            version=new_version,
            service_amount=calc_result["service_amount"],
            extended_service_amount=calc_result["extended_service_amount"],
            material_amount=calc_result["material_amount"],
            travel_amount=calc_result["travel_amount"],
            tip_amount=calc_result["tip_amount"],
            platform_fee=calc_result["platform_fee"],
            booking_fee=calc_result["booking_fee"],
            subtotal=calc_result["subtotal"],
            taxable_amount=calc_result["taxable_amount"],
            tax_amount=calc_result["tax_amount"],
            fix_coin_discount=calc_result["fix_coin_discount"],
            discount_total=calc_result["discount_total"],
            gross_amount=calc_result["gross_amount"],
            payable_amount=calc_result["payable_amount"],
            business_gross_amount=calc_result["business_gross_amount"],
            business_deduction=calc_result["business_deduction"],
            business_net_amount=calc_result["business_net_amount"],
            status=BillingStatus.DRAFT,
            calculation_snapshot=calc_result,
        )
        
        BillingService._create_billing_items(adjusted_record)
        
        return adjusted_record
