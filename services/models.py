import uuid

from django.conf import settings
from django.db import models
from core.models.base import TimeStampedModel
from business.models import BusinessProfile
from categories.models import Category, SubCategory
from django.core.exceptions import ValidationError

#=========================================================================================================
#                                   Service Type & Unit (admin managed)
#=========================================================================================================
class ServiceType(TimeStampedModel):
    """
    Admin-managed service type.

    Example: Sell/Buy, Maintenance, Time Based, Rental,
    Documentation, Transport, Training/Education, Healthcare.
    """

    type_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()

        self.name = self.name.strip()

        if not self.name:
            raise ValidationError(
                {"name": "Service type name is required."}
            )

    def __str__(self):
        return self.name


class Unit(TimeStampedModel):
    """
    Unit belonging to a ServiceType.

    Example:
        ServiceType: Rental
        Unit: Per Day, Per Hour
    """

    unit_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name="units",
    )

    name = models.CharField(
        max_length=100,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_type", "name"],
                name="unique_unit_per_service_type",
            ),
        ]

    def clean(self):
        super().clean()

        self.name = self.name.strip()

        if not self.name:
            raise ValidationError(
                {"name": "Unit name is required."}
            )

    def __str__(self):
        return f"{self.service_type.name} → {self.name}"


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

    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name="services",
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="services",
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

#=========================================================================================================
#                                   Search Log (zero-result tracking)
#=========================================================================================================

class SearchLog(TimeStampedModel):
    """
    Records every service search, primarily so zero-result
    searches can be reviewed later. Helps identify real user
    phrases (e.g. local/casual terms) that automated matching
    (full-text + trigram + WordNet) didn't catch, without having
    to guess synonyms upfront for every possible phrase.
    """

    search_term = models.CharField(
        max_length=255,
        db_index=True,
    )

    result_count = models.PositiveIntegerField()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_logs",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["result_count", "created_at"]),
        ]

    def __str__(self):
        return f'"{self.search_term}" ({self.result_count} results)'
    

#=========================================================================================================
#                                   Search Synonym (manual, admin-editable)
#=========================================================================================================

class SearchSynonym(TimeStampedModel):
    """
    Manually added word pairs that should be treated as
    interchangeable in search. Meant to be added AFTER reviewing
    zero-result SearchLog entries — fill gaps that WordNet and
    trigram matching couldn't catch (local/casual phrases, etc).

    Matching works in BOTH directions: if term="putting" and
    synonym="installation", searching either word will also
    search for the other.
    """

    term = models.CharField(
        max_length=100,
        db_index=True,
        help_text="A word users might search for, e.g. 'putting'.",
    )

    synonym = models.CharField(
        max_length=100,
        db_index=True,
        help_text=(
            "The word it should also match, e.g. 'installation'. "
            "Matching works both ways."
        ),
    )

    class Meta:
        ordering = ["term"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "synonym"],
                name="unique_search_synonym_pair",
            ),
        ]

    def clean(self):
        super().clean()

        if self.term.strip().lower() == self.synonym.strip().lower():
            raise ValidationError(
                {
                    "synonym": (
                        "Term and synonym must be different words."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.term = self.term.strip().lower()
        self.synonym = self.synonym.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.term} <-> {self.synonym}"
