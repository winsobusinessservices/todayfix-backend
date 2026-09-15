from rest_framework import serializers
from .models import Review, ReviewImage
from bookings.models import Booking
from bookings.choices import BookingStatus
from django.db import transaction

class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ["image_uuid", "image", "created_at"]

class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Review
        fields = [
            "review_uuid",
            "booking",
            "customer",
            "business",
            "service",
            "employee",
            "rating",
            "message",
            "images",
            "created_at",
            "updated_at"
        ]
        read_only_fields = fields

class ReviewCreateSerializer(serializers.Serializer):
    booking_uuid = serializers.UUIDField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        max_length=5
    )

    def validate_booking_uuid(self, value):
        user = self.context["request"].user
        try:
            booking = Booking.objects.get(uuid=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")
            
        if booking.user != user:
            raise serializers.ValidationError("You do not own this booking.")
            
        if booking.status != BookingStatus.COMPLETED:
            raise serializers.ValidationError("Service must be completed before submitting a review.")
            
        if hasattr(booking, 'review'):
            raise serializers.ValidationError("You have already reviewed this booking.")
            
        return booking

    def create(self, validated_data):
        booking = validated_data.pop("booking_uuid")
        images = validated_data.pop("images", [])
        
        with transaction.atomic():
            review = Review.objects.create(
                booking=booking,
                customer=booking.user,
                business=booking.business,
                service=booking.service,
                employee=booking.employee,
                rating=validated_data["rating"],
                message=validated_data["message"]
            )
            
            for image in images:
                ReviewImage.objects.create(review=review, image=image)
                
        return review

class ReviewUpdateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    message = serializers.CharField(required=False, allow_blank=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False
    )
    
    def validate(self, attrs):
        if "images" in attrs:
            existing_count = self.instance.images.count()
            new_count = len(attrs["images"])
            if existing_count + new_count > 5:
                raise serializers.ValidationError({"images": "Maximum 5 images allowed per review."})
        return attrs

    def update(self, instance, validated_data):
        if "rating" in validated_data:
            instance.rating = validated_data["rating"]
        if "message" in validated_data:
            instance.message = validated_data["message"]
            
        images = validated_data.pop("images", [])
        
        with transaction.atomic():
            instance.save()
            for image in images:
                ReviewImage.objects.create(review=instance, image=image)
                
        return instance
