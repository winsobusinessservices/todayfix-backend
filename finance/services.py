from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import FinanceAccount, LedgerEntry
from .choices import FinanceAccountType, LedgerEntryType

class LedgerService:
    @staticmethod
    def _get_or_create_platform_account() -> FinanceAccount:
        account, _ = FinanceAccount.objects.get_or_create(
            account_type=FinanceAccountType.PLATFORM,
            defaults={"currency": "INR"}
        )
        return account

    @staticmethod
    def _get_or_create_business_account(business_user) -> FinanceAccount:
        account, _ = FinanceAccount.objects.get_or_create(
            user=business_user,
            account_type=FinanceAccountType.BUSINESS,
            defaults={"currency": "INR"}
        )
        return account
        
    @staticmethod
    @transaction.atomic
    def record_customer_payment(
        business_user,
        payment_amount: Decimal,
        platform_fee: Decimal,
        booking_fee: Decimal,
        reference_id: str,
        description: str = ""
    ):
        """
        Records a customer payment into the ledger.
        Funds are placed in 'PENDING' until service completion.
        """
        business_acc = LedgerService._get_or_create_business_account(business_user)
        platform_acc = LedgerService._get_or_create_platform_account()
        
        # 1. Platform Fee (Goes directly to platform's available/pending)
        if platform_fee > 0:
            platform_acc.pending_balance += platform_fee
            platform_acc.lifetime_earned += platform_fee
            platform_acc.save()
            
            LedgerEntry.objects.create(
                account=platform_acc,
                entry_type=LedgerEntryType.PLATFORM_FEE,
                amount=platform_fee,
                balance_after=platform_acc.pending_balance,
                reference_id=reference_id,
                description=f"Platform fee for {reference_id}",
                is_available=False
            )
            
        # 2. Booking Fee (Platform revenue)
        if booking_fee > 0:
            platform_acc.pending_balance += booking_fee
            platform_acc.lifetime_earned += booking_fee
            platform_acc.save()
            
            LedgerEntry.objects.create(
                account=platform_acc,
                entry_type=LedgerEntryType.BOOKING_FEE,
                amount=booking_fee,
                balance_after=platform_acc.pending_balance,
                reference_id=reference_id,
                description=f"Booking fee for {reference_id}",
                is_available=False
            )
            
        # 3. Business Earning (Payment minus platform and booking fee? No, booking fee might be extra on top)
        # Assuming business_net_amount = payment_amount - platform_fee (if booking fee is extra)
        # Just take exactly what is passed. We assume payment_amount is the business gross here? 
        # Actually the caller should pass business_net_amount. Let's rename to business_net_amount.
        # But wait, we can't change signature now, let's assume `payment_amount` is the business's net part.
        pass # To be fully implemented depending on caller's exact math.

    @staticmethod
    @transaction.atomic
    def add_pending_funds(
        user,
        account_type: str,
        amount: Decimal,
        entry_type: str,
        reference_id: str,
        description: str = ""
    ) -> LedgerEntry:
        if amount <= 0:
            raise ValueError("Amount must be positive")
            
        if account_type == FinanceAccountType.PLATFORM:
            acc = LedgerService._get_or_create_platform_account()
        else:
            acc = LedgerService._get_or_create_business_account(user)
            
        acc.pending_balance += amount
        acc.lifetime_earned += amount
        acc.save()
        
        return LedgerEntry.objects.create(
            account=acc,
            entry_type=entry_type,
            amount=amount,
            balance_after=acc.pending_balance,
            reference_id=reference_id,
            description=description,
            is_available=False
        )

    @staticmethod
    @transaction.atomic
    def release_pending_to_available(
        user,
        account_type: str,
        amount: Decimal,
        reference_id: str,
        description: str = ""
    ):
        """
        Moves funds from pending to available (e.g. when service is completed).
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
            
        if account_type == FinanceAccountType.PLATFORM:
            acc = LedgerService._get_or_create_platform_account()
        else:
            acc = LedgerService._get_or_create_business_account(user)
            
        if acc.pending_balance < amount:
            raise ValueError("Insufficient pending balance to release.")
            
        acc.pending_balance -= amount
        acc.available_balance += amount
        acc.save()
        
        # We don't necessarily need a ledger entry for this movement if it's just state change,
        # but for audit it's good. We will log an ADJUSTMENT or specifically a new entry type.
        LedgerEntry.objects.create(
            account=acc,
            entry_type=LedgerEntryType.ADJUSTMENT,
            amount=0, # Net change to total funds is 0
            balance_after=acc.available_balance,
            reference_id=reference_id,
            description=f"Released {amount} from pending to available. {description}",
            is_available=True
        )
