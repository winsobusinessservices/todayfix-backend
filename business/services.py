from django.db import transaction
from django.utils import timezone

from accounts.choices import UserRole
from .choices import UpgradeRequestStatus
from .models import BusinessUpgradeRequest


class BusinessUpgradeService:
    @staticmethod
    @transaction.atomic
    def submit(user, reason=""):
        if user.role != UserRole.USER:
            raise ValueError("Only USER accounts can request a business upgrade.")

        pending = BusinessUpgradeRequest.objects.filter(
            user=user,
            status=UpgradeRequestStatus.PENDING,
        ).first()
        if pending:
            raise ValueError("A business upgrade request is already pending.")

        return BusinessUpgradeRequest.objects.create(
            user=user,
            reason=reason,
            status=UpgradeRequestStatus.PENDING,
        )

    @staticmethod
    @transaction.atomic
    def approve(request_obj, admin_user):
        if request_obj.status != UpgradeRequestStatus.PENDING:
            raise ValueError("Only pending requests can be approved.")

        user = request_obj.user
        user.role = UserRole.BUSINESS
        user.has_business = True
        user.business_verified = True
        user.save(update_fields=[
            "role",
            "has_business",
            "business_verified",
            "updated_at",
        ])

        request_obj.status = UpgradeRequestStatus.APPROVED
        request_obj.reviewed_by = admin_user
        request_obj.reviewed_at = timezone.now()
        request_obj.rejection_reason = ""
        request_obj.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ])
        return request_obj

    @staticmethod
    @transaction.atomic
    def reject(request_obj, admin_user, reason=""):
        if request_obj.status != UpgradeRequestStatus.PENDING:
            raise ValueError("Only pending requests can be rejected.")

        request_obj.status = UpgradeRequestStatus.REJECTED
        request_obj.reviewed_by = admin_user
        request_obj.reviewed_at = timezone.now()
        request_obj.rejection_reason = reason
        request_obj.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ])
        return request_obj
    
