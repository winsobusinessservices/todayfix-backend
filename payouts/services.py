from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as ApplicationError
from finance.models import FinanceAccount
from finance.choices import FinanceAccountType
from .models import Payout, PayoutType, PayoutStatus

class PayoutService:
    @staticmethod
    def get_eligible_payout_amount(user) -> Decimal:
        """
        Returns the maximum eligible payout amount based on the 70% rule.
        """
        account = FinanceAccount.objects.filter(user=user, account_type=FinanceAccountType.BUSINESS).first()
        if not account:
            return Decimal("0.00")
            
        available = account.available_balance
        if available <= 0:
            return Decimal("0.00")
            
        # 70% of available earnings
        eligible = (available * Decimal("0.70")).quantize(Decimal("0.01"))
        return eligible

    @staticmethod
    def check_emergency_eligibility(user) -> bool:
        """
        Check if user has exceeded 2 emergency payouts this calendar month.
        """
        now = timezone.now()
        count = Payout.objects.filter(
            user=user,
            payout_type=PayoutType.EMERGENCY,
            created_at__year=now.year,
            created_at__month=now.month
        ).exclude(status__in=[PayoutStatus.FAILED, PayoutStatus.REJECTED]).count()
        
        return count < 2

    @staticmethod
    @transaction.atomic
    def request_payout(user, payout_account, amount: Decimal, is_emergency: bool = False) -> Payout:
        if amount <= 0:
            raise ApplicationError("Payout amount must be greater than zero.")
            
        eligible_amount = PayoutService.get_eligible_payout_amount(user)
        if amount > eligible_amount:
            raise ApplicationError(f"Requested amount exceeds eligible amount of {eligible_amount}.")
            
        payout_type = PayoutType.EMERGENCY if is_emergency else PayoutType.WEEKLY
        
        if is_emergency and not PayoutService.check_emergency_eligibility(user):
            raise ApplicationError("Maximum of 2 emergency payouts per calendar month exceeded.")
            
        # Lock the finance account and deduct the amount immediately to prevent double spending
        account = FinanceAccount.objects.select_for_update().filter(user=user, account_type=FinanceAccountType.BUSINESS).first()
        account.available_balance -= amount
        account.lifetime_withdrawn += amount
        account.save()
        
        payout = Payout.objects.create(
            user=user,
            payout_account=payout_account,
            amount=amount,
            payout_type=payout_type,
            status=PayoutStatus.PENDING
        )
        
        # Log Ledger entry
        from finance.services import LedgerService
        from finance.choices import LedgerEntryType
        
        LedgerService.add_pending_funds(
            user=user,
            account_type=FinanceAccountType.BUSINESS,
            amount=-amount, # It's a debit
            entry_type=LedgerEntryType.PAYOUT,
            reference_id=str(payout.payout_uuid),
            description=f"Payout request {payout.payout_uuid}"
        )
        
        return payout
