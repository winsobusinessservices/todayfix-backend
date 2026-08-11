from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models.base import TimeStampedModel
from .choices import BusinessType, UpgradeRequestStatus


class BusinessUpgradeRequest(TimeStampedModel):
    """Application submitted by a USER who wants BUSINESS privileges."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_upgrade_requests",
    )
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=UpgradeRequestStatus.choices,
        default=UpgradeRequestStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_business_upgrade_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status=UpgradeRequestStatus.PENDING),
                name="unique_pending_business_upgrade_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.status}"


class BusinessProfile(TimeStampedModel):
    """A business entity owned by a BUSINESS user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profiles",
    )
    business_type = models.CharField(
        max_length=20,
        choices=BusinessType.choices,
        db_index=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "business_type"]),
            models.Index(fields=["name"]),
        ]

    def clean(self):
        if self.owner_id and self.owner.role != "BUSINESS":
            raise ValidationError("Only BUSINESS users can own a business profile.")

    def __str__(self):
        return f"{self.name} ({self.business_type})"


class ManagedBusiness(TimeStampedModel):
    """Junction table allowing COMPANY/INVESTOR profiles to manage child profiles."""

    manager_business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="managed_business_links",
    )
    linked_business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="manager_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["manager_business", "linked_business"],
                name="unique_managed_business_link",
            ),
        ]
        indexes = [
            models.Index(fields=["manager_business"]),
            models.Index(fields=["linked_business"]),
        ]

    def clean(self):
        if self.manager_business_id == self.linked_business_id:
            raise ValidationError("A business cannot manage itself.")

        if self.manager_business.business_type not in {
            BusinessType.COMPANY,
            BusinessType.INVESTOR,
        }:
            raise ValidationError(
                "Only COMPANY and INVESTOR profiles can manage other businesses."
            )

    def __str__(self):
        return f"{self.manager_business.name} -> {self.linked_business.name}"
    
