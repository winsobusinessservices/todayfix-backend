import uuid


from django.conf import settings
from django.db import models

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from .managers import CustomUserManager
from .choices import UserRole


#====================================Custom user model=========================
class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Core account used by every person on TodayFix."""

    last_logout = models.DateTimeField(null=True, blank=True)

    user_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)

    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name="Email Address",
        null=True,
        blank=True,
    )

    phone_validator = RegexValidator(
        regex=r"^[6-9]\d{9}$",
        message="Phone number must be exactly 10 digits and start with 6, 7, 8, or 9.",
    )

    phone = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Phone Number",
        validators=[phone_validator],
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

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

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


#====================================OTP Verification model================================
class OTPVerification(models.Model):
    """
    Stores OTP verification attempts for signup/login.

    The plaintext OTP is NEVER stored.
    """

    PURPOSE_SIGNUP = "SIGNUP"
    PURPOSE_LOGIN = "LOGIN"

    PURPOSE_CHOICES = (
        (PURPOSE_SIGNUP, "Signup"),
        (PURPOSE_LOGIN, "Login"),
    )

    otp_verification_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="otp_verifications",
    )

    phone = models.CharField(
        max_length=10,
        db_index=True,
    )

    otp_hash = models.CharField(
        max_length=128,
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default=PURPOSE_SIGNUP,
        db_index=True,
    )

    provider = models.CharField(
        max_length=30,
        default="FAST2SMS",
        db_index=True,
    )

    provider_request_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Request/OTP ID returned by the SMS provider.",
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0
    )

    is_used = models.BooleanField(
        default=False
    )

    is_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=[
                    "phone",
                    "purpose",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return f"{self.phone} - {self.purpose}"

#===========================================Addresss model============================
class Address(models.Model):
    add_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    address_line = models.CharField(max_length=255)
    locality = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r"^\d{6}$",
                message="Pincode must be exactly 6 digits.",
            )   
        ],
    )

    location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    

    

    class AddressType(models.TextChoices):
        HOME = "HOME", "Home"
        WORK = "WORK", "Work"
        OTHER = "OTHER", "Other"

    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.OTHER,
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.address_line} - {self.user.email}"


#====================================Password reset token model======================
class PasswordResetToken(models.Model):

    password_reset_token_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
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


#========================Email template model===============================
class EmailTemplate(models.Model):

    email_template_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    subject = models.CharField(max_length=255)

    message = models.TextField()

    def __str__(self):
        return self.name

#=====================Pending Registeration model============================
class PendingRegistration(models.Model):
    pending_registration_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    email = models.EmailField(
        unique=True,
        db_index=True,
        blank=True,
        null=True,
    )

    phone = models.CharField(
        max_length=16,
        blank=True,
        null=True,
    )

    password = models.CharField(
        max_length=128
    )

    token = models.CharField(
        max_length=128,
        unique=True,
    )

    verification_method = models.CharField(
        max_length=10,
        choices=[
            ("email", "Email"),
            ("phone", "Phone"),
        ],
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    def __str__(self):
        return (
            f"Pending registration - "
            f"{self.email or self.phone}"
        )
    

#==================================Signup OTP model====================
class SignupOTPVerification(models.Model):

    signup_otp_verification_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    phone = models.CharField(
        max_length=15
    )

    otp_hash = models.CharField(
        max_length=255
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0
    )

    is_used = models.BooleanField(
        default=False
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.phone
    

class GoogleIdentity(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_identity",
    )

    google_sub = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    google_email = models.EmailField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Google Identity - {self.google_email}"


        