from django.db import models

class CallType(models.TextChoices):
    AUDIO = "AUDIO", "Audio"
    VIDEO = "VIDEO", "Video"

class CallStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    RINGING = "RINGING", "Ringing"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    MISSED = "MISSED", "Missed"
    ENDED = "ENDED", "Ended"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
