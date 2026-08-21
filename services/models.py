import uuid

from django.db import models
from core.models.base import TimeStampedModel
from business.models import BusinessProfile
from categories.models import Category, SubCategory


class Service(TimeStampedModel):
    """
    Service offered by an approved TodayFix business.

    Category → SubCategory → Service → BusinessProfile
    """

    service_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="services",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="services",
    )

    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.PROTECT,
        related_name="services",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    duration = models.PositiveIntegerField(
        help_text="Duration in minutes.",
    )

    required_employees = models.PositiveIntegerField(
        default=1,
        help_text="Number of employees required to perform this service.",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["business", "is_active"]
            ),
            models.Index(
                fields=["category", "is_active"]
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.business.name})"

#=========================================================================================================
#                                   Connection between Services and Employees
#=========================================================================================================
class ServiceEmployee(TimeStampedModel):
    """
    Maps employees to the services they are qualified to perform.
    """

    service_employee_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="employee_assignments",
    )

    employee = models.ForeignKey(
        "business.Employee",
        on_delete=models.CASCADE,
        related_name="service_assignments",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "employee"],
                name="unique_employee_per_service",
            ),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.service.name}"
