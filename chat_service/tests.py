from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Conversation, Message
from .choices import ConversationStatus, MessageType
from business.models import BusinessProfile
from bookings.models import Booking
from bookings.choices import BookingStatus

User = get_user_model()

class ChatTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email="customer@test.com", password="pwd")
        self.business_owner = User.objects.create_user(email="owner@test.com", password="pwd")
        self.business = BusinessProfile.objects.create(owner=self.business_owner, name="Test Business")
        self.booking = Booking.objects.create(
            user=self.customer,
            business=self.business,
            status=BookingStatus.CONFIRMED,
            booking_time="2026-10-10 10:00"
        )
        self.conversation = Conversation.objects.create(
            scheduled_booking=self.booking,
            customer=self.customer,
            business=self.business,
            booking_type="SCHEDULED"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)

    def test_close_conversation(self):
        url = f'/api/chat/conversations/{self.conversation.conversation_uuid}/close/'
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, ConversationStatus.CLOSED)

    def test_archive_conversation(self):
        url = f'/api/chat/conversations/{self.conversation.conversation_uuid}/archive/'
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, ConversationStatus.ARCHIVED)

    def test_send_message(self):
        url = f'/api/chat/conversations/{self.conversation.conversation_uuid}/messages/'
        response = self.client.post(url, {
            "message_type": "TEXT",
            "text": "Hello world"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        
    def test_send_message_validation(self):
        url = f'/api/chat/conversations/{self.conversation.conversation_uuid}/messages/'
        response = self.client.post(url, {
            "message_type": "TEXT",
            "text": ""
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_update_message(self):
        msg = Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            text="Original"
        )
        url = f'/api/chat/messages/{msg.message_uuid}/'
        response = self.client.patch(url, {"text": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg.refresh_from_db()
        self.assertEqual(msg.text, "Updated")
        self.assertIsNotNone(msg.edited_at)
        
    def test_delete_message(self):
        msg = Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            text="To Delete"
        )
        url = f'/api/chat/messages/{msg.message_uuid}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        msg.refresh_from_db()
        self.assertIsNotNone(msg.deleted_at)
        
        # Verify it doesn't show in list
        list_url = f'/api/chat/conversations/{self.conversation.conversation_uuid}/messages/'
        list_response = self.client.get(list_url)
        self.assertEqual(len(list_response.data), 0)
