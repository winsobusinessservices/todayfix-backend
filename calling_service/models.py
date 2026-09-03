import uuid
from django.conf import settings
from django.db import models
from core.models.base import TimeStampedModel
from chat_service.models import Conversation
from .choices import CallType, CallStatus

class CallSession(TimeStampedModel):
    call_session_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="call_sessions",
    )
    
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_calls",
    )
    
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_calls",
    )
    
    call_type = models.CharField(
        max_length=20,
        choices=CallType.choices,
        default=CallType.AUDIO,
    )
    
    status = models.CharField(
        max_length=20,
        choices=CallStatus.choices,
        default=CallStatus.INITIATED,
        db_index=True,
    )
    
    provider_call_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="External identifier from the 3rd party calling provider",
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "status"]),
        ]
        
    def __str__(self):
        return f"Call {self.call_session_uuid} - {self.status}"
