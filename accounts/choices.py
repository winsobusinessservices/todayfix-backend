from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", _("Admin")
    USER = "USER", _("User")
    BUSINESS = "BUSINESS", _("Business")
    
    