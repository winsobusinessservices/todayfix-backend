from django.db import models


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"

class BookingSlotType(models.TextChoices):

    MORNING = "MORNING", "Morning"

    AFTERNOON = "AFTERNOON", "Afternoon"

    EVENING = "EVENING", "Evening"
