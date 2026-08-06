import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager
from django.core.validators import RegexValidator
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

    phone_validator = RegexValidator(
        regex=r'^\+[1-9]\d{7,14}$',
        message=(
            "Phone number must be in E.164 format. "
            "Example: +919876543210"
            )
        )

    phone = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        verbose_name="Phone Number",
        validators=[phone_validator]
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

    
    