import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from instant_bookings.utils.geo import (
    calculate_distance_km,
    extract_coordinates,
    InvalidLocationError,
)
from fix_coins.services import validate_redemption
from common.utils.money import quantize_money
from .models import BillingRecord, BillingItem
from .calculators import BillingCalculator, TravelFeeCalculator
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
            # Billing may only be previewed/created once the job is
            # actually completed, not while it's still pending,
            # confirmed, in progress, cancelled, or rejected.
            if booking.status != BookingStatus.COMPLETED:
                raise ValueError(f"Billing cannot be created for a booking with status {booking.status}.")
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
    def _get_travel_amount_for_booking(booking) -> Decimal:
        """
        Computes distance between the customer's address and the
        business location, then derives the travel charge from the
        admin-configured TravelFeeRule.
        """
        try:
            customer_lat, customer_lng = extract_coordinates(booking.address.location)
            business_lat, business_lng = extract_coordinates(booking.business.location)
        except InvalidLocationError as e:
            raise ValueError(f"Could not calculate travel distance: {e}")

        distance_km = calculate_distance_km(customer_lat, customer_lng, business_lat, business_lng)
        return TravelFeeCalculator.calculate_fee(Decimal(str(distance_km)))

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
        travel = BillingService._get_travel_amount_for_booking(booking)
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
    def _apply_calc_result(record: BillingRecord, calc_result: dict) -> None:
        """
        Writes a calculator result onto a BillingRecord instance (new or
        existing) without saving it. Shared by create (new draft) and
        merge (existing draft update) so the field mapping only lives
        in one place.
        """
        calculation_snapshot = {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in calc_result.items()
        }
        record.service_amount = calc_result["service_amount"]
        record.extended_service_amount = calc_result["extended_service_amount"]
        record.material_amount = calc_result["material_amount"]
        record.travel_amount = calc_result["travel_amount"]
        record.tip_amount = calc_result["tip_amount"]
        record.platform_fee = calc_result["platform_fee"]
        record.booking_fee = calc_result["booking_fee"]
        record.subtotal = calc_result["subtotal"]
        record.taxable_amount = calc_result["taxable_amount"]
        record.tax_amount = calc_result["tax_amount"]
        record.fix_coin_discount = calc_result["fix_coin_discount"]
        record.discount_total = calc_result["discount_total"]
        record.gross_amount = calc_result["gross_amount"]
        record.payable_amount = calc_result["payable_amount"]
        record.business_gross_amount = calc_result["business_gross_amount"]
        record.business_deduction = calc_result["business_deduction"]
        record.business_net_amount = calc_result["business_net_amount"]
        record.calculation_snapshot = calculation_snapshot

    @staticmethod
    def _merge_with_existing_draft(existing_draft, explicit_fields, **kwargs):
        """
        Fills in extended_service_amount / material_amount that were NOT
        explicitly sent in this request with the value already stored on
        the existing DRAFT, so e.g. updating material_amount in a second
        call doesn't wipe out an extended_service_amount set earlier.
        create_draft is business-owner-only now, so tip/fix coins never
        pass through here at all - those only ever come in via adjust.
        """
        if not existing_draft:
            return kwargs
        merged = dict(kwargs)
        for field in ("extended_service_amount", "material_amount"):
            if field not in explicit_fields:
                merged[field] = getattr(existing_draft, field)
        return merged 

    @staticmethod
    @transaction.atomic
    def create_billing_record(booking=None, instant_booking=None, explicit_fields=None, **kwargs) -> BillingRecord:
        if bool(booking) == bool(instant_booking):
            raise ValueError("Provide exactly one of booking or instant_booking.")
            
        BillingService.validate_billable_booking(booking, instant_booking)
        explicit_fields = explicit_fields or set()

        if booking:
            existing_draft = BillingRecord.objects.select_for_update().filter(
                booking=booking, status=BillingStatus.DRAFT
            ).first()
        else:
            existing_draft = BillingRecord.objects.select_for_update().filter(
                instant_booking=instant_booking, status=BillingStatus.DRAFT
            ).first()

        if existing_draft:
            # A DRAFT already exists for this booking (e.g. the customer set
            # tip/coins earlier). Merge this caller's explicitly-sent,
            # role-gated fields into it rather than discarding them or
            # overwriting the other party's previously submitted amounts.
            merged_kwargs = BillingService._merge_with_existing_draft(existing_draft, explicit_fields, **kwargs)
            if booking:
                calc_result = BillingService.calculate_from_booking(booking, **merged_kwargs)
            else:
                calc_result = BillingService.calculate_from_instant_booking(instant_booking, **merged_kwargs)

            BillingService._apply_calc_result(existing_draft, calc_result)
            existing_draft.save()
            existing_draft.items.all().delete()
            BillingService._create_billing_items(existing_draft)
            return existing_draft

        # No live DRAFT. If this booking already has any billing record
        # at all, billing has already been finalized (or progressed
        # further - paid, adjusted, etc.) and a brand-new v1 draft must
        # not be created from scratch; the caller should use `adjust`
        # on the latest record instead.
        if booking:
            already_billed = BillingRecord.objects.filter(booking=booking).exists()
        else:
            already_billed = BillingRecord.objects.filter(instant_booking=instant_booking).exists()

        if already_billed:
            raise ValueError(
                "Billing has already been finalized for this booking. Use the adjust endpoint to make further changes."
            )

        if booking:
            calc_result = BillingService.calculate_from_booking(booking, **kwargs)
        else:
            calc_result = BillingService.calculate_from_instant_booking(instant_booking, **kwargs)

        record = BillingRecord(booking=booking, instant_booking=instant_booking, status=BillingStatus.DRAFT)
        BillingService._apply_calc_result(record, calc_result)
        record.save()
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
    def adjust_billing(billing_record: BillingRecord, user=None, **kwargs) -> BillingRecord:
        """
        Creates a new billing version on top of an already-FINALIZED
        record. This is the customer-only step: it adds tip_amount
        and/or redeems FixCoins (fix_coins_to_redeem).

        extended_service_amount / material_amount / tip_amount are
        carried forward from the record being adjusted unless
        explicitly overridden, so the business owner's already-
        finalized amounts are never wiped out by the customer's call.

        Per product decision, this new version is auto-finalized
        immediately (tip/coins is the last step before payment) rather
        than being left as a DRAFT requiring a separate confirm call.
        """
        if billing_record.status != BillingStatus.FINALIZED:
            raise ValueError("Only finalized billing records can be adjusted.")

        booking = billing_record.booking
        instant_booking = billing_record.instant_booking

        BillingService.validate_billable_booking(booking, instant_booking)

        merged_kwargs = {
            "extended_service_amount": billing_record.extended_service_amount,
            "material_amount": billing_record.material_amount,
            "tip_amount": billing_record.tip_amount,
            **kwargs,
        }
        coins_to_redeem = merged_kwargs.pop("fix_coins_to_redeem", 0) or 0

        if coins_to_redeem > 0:
            if booking:
                preview = BillingService.calculate_from_booking(booking, **merged_kwargs)
            else:
                preview = BillingService.calculate_from_instant_booking(instant_booking, **merged_kwargs)
            redemption_preview = validate_redemption(user, preview["gross_amount"], coins_to_redeem)
            merged_kwargs["fix_coin_discount"] = quantize_money(redemption_preview["discount_amount"])

        if booking:
            calc_result = BillingService.calculate_from_booking(booking, **merged_kwargs)
        else:
            calc_result = BillingService.calculate_from_instant_booking(instant_booking, **merged_kwargs)

        # Update current record status to adjusted
        billing_record.status = BillingStatus.ADJUSTED
        billing_record.save(update_fields=["status", "updated_at"])

        # Create a new version
        new_version = billing_record.version + 1

        adjusted_record = BillingRecord(
            booking=booking,
            instant_booking=instant_booking,
            version=new_version,
            status=BillingStatus.DRAFT,
        )
        BillingService._apply_calc_result(adjusted_record, calc_result)
        adjusted_record.save()
        BillingService._create_billing_items(adjusted_record)

        adjusted_record = BillingService.finalize_billing(adjusted_record)

        return adjusted_record
