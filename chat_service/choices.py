from django.db import models

class BookingType(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled Booking"
    INSTANT = "INSTANT", "Instant Booking"

class ConversationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"

class MessageType(models.TextChoices):
    TEXT = "TEXT", "Text"
    IMAGE = "IMAGE", "Image"
    FILE = "FILE", "File"
    LOCATION = "LOCATION", "Location"
    SYSTEM = "SYSTEM", "System"
