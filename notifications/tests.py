from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Notification
from .services import NotificationService
from .choices import NotificationType

User = get_user_model()

class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_notification_creation(self):
        NotificationService.create(
            recipient=self.user,
            notification_type=NotificationType.SYSTEM,
            title="Welcome",
            message="Welcome to TodayFix",
            data={"key": "value"}
        )
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.recipient, self.user)
        self.assertEqual(notif.notification_type, NotificationType.SYSTEM)

    def test_list_notifications_api(self):
        NotificationService.create(
            recipient=self.user,
            notification_type=NotificationType.SYSTEM,
            title="Welcome",
            message="Welcome to TodayFix",
        )
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_mark_read_api(self):
        notif = NotificationService.create(
            recipient=self.user,
            notification_type=NotificationType.SYSTEM,
            title="Welcome",
            message="Welcome to TodayFix",
        )
        self.assertFalse(notif.is_read)
        response = self.client.post(f'/api/notifications/{notif.notification_uuid}/read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_read_api(self):
        for _ in range(3):
            NotificationService.create(
                recipient=self.user,
                notification_type=NotificationType.SYSTEM,
                title="Welcome",
                message="Welcome to TodayFix",
            )
        response = self.client.post('/api/notifications/mark-all-read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(is_read=True).count(), 3)
