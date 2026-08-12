import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from .managers import CustomUserManager
from .choices import UserRole


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Core account used by every person on TodayFix."""

    last_logout = models.DateTimeField(null=True, blank=True)

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)

    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name="Email Address",
    )

    phone_validator = RegexValidator(
        regex=r"^[6-9]\d{9}$",
        message="Phone number must be exactly 10 digits and start with 6, 7, 8, or 9.",
    )
    phone = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        verbose_name="Phone Number",
        validators=[phone_validator],
    )

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

    # These flags are retained for compatibility with the existing frontend.
    # The authoritative business state is also represented by BusinessUpgradeRequest
    # and BusinessProfile in the business app.
    has_business = models.BooleanField(default=False)
    business_verified = models.BooleanField(default=False)

    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
    )

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Address(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(max_length=20)
    street = models.CharField(max_length=255)
    area = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.label} - {self.user.email}"

#---------------------------------------------------Password reset token model---------------------------------------------------#
class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )

    token = models.CharField(
        max_length=128,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Password reset token - {self.user.email}"


#---------------------------------------------------Email template model---------------------------------------------------#
class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()

    def __str__(self):
        return self.name
    

