import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from core.models.base import TimeStampedModel
from bookings.models import Booking
from business.models import BusinessProfile, Employee
from services.models import Service


class Review(TimeStampedModel):
    """
    Review submitted by a Customer for a completed Booking.
    Contributes to Business, Service, and potentially Employee ratings.
    """
    
    review_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    
    # 1 Review per Booking enforced at DB level
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="review",
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    
    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    
    rating = models.PositiveSmallIntegerField(
        help_text="Rating from 1 to 5.",
    )
    
    message = models.TextField(
        blank=True,
        default="",
    )
    
    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="rating_range_1_to_5",
            ),
        ]
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["service"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["rating"]),
        ]
        
    def clean(self):
        super().clean()
        if self.rating is not None and not (1 <= self.rating <= 5):
            raise ValidationError({"rating": "Rating must be between 1 and 5."})
            
    def __str__(self):
        return f"Review {self.review_uuid} - {self.rating} Stars"


class ReviewImage(TimeStampedModel):
    """
    Optional images attached to a Review. Maximum 5 images per Review.
    """
    
    image_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="images",
    )
    
    image = models.FileField(
        upload_to="reviews/images/",
    )
    
    class Meta:
        ordering = ["created_at"]
        
    def __str__(self):
        return f"ReviewImage {self.image_uuid} for Review {self.review.review_uuid}"
