from django.db import models

class NotificationType(models.TextChoices):
    # Booking
    BOOKING_CREATED = "BOOKING_CREATED", "Booking Created"
    BOOKING_ACCEPTED = "BOOKING_ACCEPTED", "Booking Accepted"
    BOOKING_REJECTED = "BOOKING_REJECTED", "Booking Rejected"
    BOOKING_CANCELLED = "BOOKING_CANCELLED", "Booking Cancelled"
    EMPLOYEE_ASSIGNED = "EMPLOYEE_ASSIGNED", "Employee Assigned"
    SERVICE_STARTED = "SERVICE_STARTED", "Service Started"
    SERVICE_COMPLETED = "SERVICE_COMPLETED", "Service Completed"

    # Instant Booking
    INSTANT_BOOKING_OFFER = "INSTANT_BOOKING_OFFER", "Instant Booking Offer"
    INSTANT_BOOKING_ACCEPTED = "INSTANT_BOOKING_ACCEPTED", "Instant Booking Accepted"
    INSTANT_BOOKING_REJECTED = "INSTANT_BOOKING_REJECTED", "Instant Booking Rejected"
    INSTANT_BOOKING_EXPIRED = "INSTANT_BOOKING_EXPIRED", "Instant Booking Expired"
    NO_PROVIDER_FOUND = "NO_PROVIDER_FOUND", "No Provider Found"

    # Chat
    NEW_CHAT_MESSAGE = "NEW_CHAT_MESSAGE", "New Chat Message"

    # Calling
    INCOMING_CALL = "INCOMING_CALL", "Incoming Call"
    CALL_MISSED = "CALL_MISSED", "Call Missed"
    CALL_ENDED = "CALL_ENDED", "Call Ended"
