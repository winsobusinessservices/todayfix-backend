import uuid

from django.core.exceptions import ValidationError
from django.db import models

from core.models.base import TimeStampedModel


class Category(TimeStampedModel):
    """
    Top-level platform category.

    Example:
        Home Services
        Automotive
        Electronics
    """

    cat_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
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
                {
                    "name": "Category name is required."
                }
            )

    def __str__(self):
        return self.name


class SubCategory(TimeStampedModel):
    """
    Subcategory belonging to a top-level Category.

    Example:

        Category:
            Home Services

        SubCategory:
            Plumbing
    """

    subCat_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )

    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        max_length=180,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    image = models.ImageField(
        upload_to="subcategories/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_subcategory_per_category",
            ),
            models.UniqueConstraint(
                fields=["category", "slug"],
                name="unique_subcategory_slug_per_category",
            ),
        ]

    def clean(self):
        super().clean()

        self.name = self.name.strip()

        if not self.name:
            raise ValidationError(
                {
                    "name": "Subcategory name is required."
                }
            )

    def __str__(self):
        return f"{self.category.name} → {self.name}"

        