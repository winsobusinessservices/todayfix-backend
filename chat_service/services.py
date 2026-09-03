from django.db import transaction
from django.utils import timezone
from bookings.models import Booking
from bookings.choices import BookingStatus
from instant_bookings.models import InstantBooking, InstantBookingStatus
from .models import Conversation, Message
from .choices import BookingType, ConversationStatus, MessageType

class ChatService:
    @staticmethod
    def get_or_create_conversation_for_scheduled_booking(booking: Booking):
        """
        Creates or returns a conversation for a scheduled booking.
        Only allowed if booking is CONFIRMED (or IN_PROGRESS / COMPLETED).
        """
        if booking.status in [BookingStatus.PENDING, BookingStatus.REJECTED]:
            raise ValueError(f"Cannot communicate for a booking in {booking.status} state.")
            
        with transaction.atomic():
            conversation, created = Conversation.objects.select_for_update().get_or_create(
                scheduled_booking=booking,
                defaults={
                    "booking_type": BookingType.SCHEDULED,
                    "customer": booking.user,
                    "business": booking.business,
                    "employee": booking.employee,
                    "status": ConversationStatus.ACTIVE,
                }
            )
            
            # Update employee if reassigned
            if not created and conversation.employee != booking.employee:
                conversation.employee = booking.employee
                conversation.save(update_fields=["employee"])
                
            return conversation, created

    @staticmethod
    def get_or_create_conversation_for_instant_booking(booking: InstantBooking):
        """
        Creates or returns a conversation for an instant booking.
        Only allowed if booking is ASSIGNED (or IN_PROGRESS / COMPLETED).
        """
        if booking.status in [InstantBookingStatus.QUOTED, InstantBookingStatus.SEARCHING, 
                              InstantBookingStatus.TIP_REQUIRED, InstantBookingStatus.NO_PROVIDER]:
            raise ValueError(f"Cannot communicate for an instant booking in {booking.status} state.")
            
        with transaction.atomic():
            conversation, created = Conversation.objects.select_for_update().get_or_create(
                instant_booking=booking,
                defaults={
                    "booking_type": BookingType.INSTANT,
                    "customer": booking.customer,
                    "business": booking.assigned_business,
                    "employee": booking.assigned_employee,
                    "status": ConversationStatus.ACTIVE,
                }
            )
            
            return conversation, created

    @staticmethod
    def create_system_message(conversation: Conversation, text: str):
        """
        Creates a system message in the conversation.
        """
        return Message.objects.create(
            conversation=conversation,
            message_type=MessageType.SYSTEM,
            text=text,
        )

    @staticmethod
    def mark_conversation_read(conversation: Conversation, user):
        """
        Marks all messages in the conversation not sent by the user as read.
        """
        unread_messages = conversation.messages.exclude(sender=user).filter(is_read=False)
        count = unread_messages.update(is_read=True, read_at=timezone.now())
        return count
