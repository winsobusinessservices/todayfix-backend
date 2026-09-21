from django.db import models


class FixCoinTransactionType(models.TextChoices):
    SIGNUP_BONUS = "SIGNUP_BONUS", "Signup Bonus"
    BOOKING_REWARD = "BOOKING_REWARD", "Booking Reward"
    REDEMPTION = "REDEMPTION", "Redemption"
    REFUND_REVERSAL = "REFUND_REVERSAL", "Refund Reversal"
    EXPIRY = "EXPIRY", "Expiry"
    RESERVATION = "RESERVATION", "Reservation"
    RELEASE = "RELEASE", "Release"
    PROMOTIONAL_BONUS = "PROMOTIONAL_BONUS", "Promotional Bonus"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT", "Admin Adjustment"


class FixCoinReferenceType(models.TextChoices):
    SIGNUP = "SIGNUP", "Signup"
    BOOKING = "BOOKING", "Booking"
    PAYMENT = "PAYMENT", "Payment"
    REFUND = "REFUND", "Refund"
    PROMOTION = "PROMOTION", "Promotion"
    ADMIN = "ADMIN", "Admin"
