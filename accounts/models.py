import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager

from .choices import UserRole


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    full_name = models.CharField(
        max_length=150,
        verbose_name="Full Name"
    )

    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name="Email Address"
    )

    phone = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        verbose_name="Phone Number"
    )

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER
    )

    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    is_staff = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "full_name",
        "phone",
    ]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.email})"
    