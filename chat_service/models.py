import uuid
from django.conf import settings
from django.db import models
from core.models.base import TimeStampedModel
from business.models import BusinessProfile, Employee
from bookings.models import Booking
from instant_bookings.models import InstantBooking
from .choices import BookingType, ConversationStatus, MessageType

class Conversation(TimeStampedModel):
    conversation_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    
    booking_type = models.CharField(
        max_length=20,
        choices=BookingType.choices,
    )
    
    scheduled_booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_conversation",
    )
    
    instant_booking = models.OneToOneField(
        InstantBooking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_conversation",
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chat_conversations",
    )
    
    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.PROTECT,
        related_name="chat_conversations",
    )
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="chat_conversations",
        null=True,
        blank=True,
    )
    
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        db_index=True,
    )
    
    closed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(scheduled_booking__isnull=False, instant_booking__isnull=True) | 
                          models.Q(scheduled_booking__isnull=True, instant_booking__isnull=False),
                name="chat_conversation_exactly_one_booking",
            ),
        ]
        
    def __str__(self):
        return f"Conversation {self.conversation_uuid} - {self.booking_type}"


class Message(TimeStampedModel):
    message_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages",
        null=True,
        blank=True,
    )
    
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    
    text = models.TextField(blank=True, default="")
    
    attachment = models.FileField(
        upload_to="chat_attachments/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]
        
    def __str__(self):
        return f"Message {self.message_uuid} by {self.sender_id if self.sender else 'System'}"
