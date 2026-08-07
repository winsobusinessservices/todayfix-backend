from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from .choices import UserRole


class CustomUserManager(BaseUserManager):
    """
    Custom User Manager
    """

    def create_user(
        self,
        email,
        first_name,
        last_name,
        phone,
        password=None,
        role=UserRole.USER,
        **extra_fields,
    ):
        """
        Create and return a regular user.
        """
        if not email:
            raise ValueError("Email is required")

    # Convert email to lowercase before saving
        email = self.normalize_email(email).lower()

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_business(
        self,
        email,
        first_name,
        last_name,
        phone,
        password=None,
        **extra_fields,
    ):
        """
        Create and return a business user.
        """

        extra_fields.setdefault("role", UserRole.BUSINESS)

        return self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            password=password,
            **extra_fields,
        )

    def create_superuser(
        self,
        email,
        first_name,
        last_name,
        phone,
        password=None,
        **extra_fields,
    ):
        """
        Create and return a superuser.
        """

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            password=password,
            **extra_fields,
        )
    