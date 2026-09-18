from rest_framework import serializers
from .models import Review, ReviewImage
from bookings.models import Booking
from bookings.choices import BookingStatus
from instant_bookings.models import InstantBooking, InstantBookingStatus
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
            "instant_booking",
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
    booking_uuid = serializers.UUIDField(required=False)
    instant_booking_uuid = serializers.UUIDField(required=False)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        max_length=5
    )

    def validate(self, attrs):
        booking_uuid = attrs.get("booking_uuid")
        instant_booking_uuid = attrs.get("instant_booking_uuid")

        if bool(booking_uuid) == bool(instant_booking_uuid):
            raise serializers.ValidationError(
                "Provide exactly one of booking_uuid or instant_booking_uuid."
            )

        user = self.context["request"].user

        if booking_uuid:
            try:
                booking = Booking.objects.get(uuid=booking_uuid)
            except Booking.DoesNotExist:
                raise serializers.ValidationError({"booking_uuid": "Booking not found."})

            if booking.user != user:
                raise serializers.ValidationError({"booking_uuid": "You do not own this booking."})

            if booking.status != BookingStatus.COMPLETED:
                raise serializers.ValidationError({"booking_uuid": "Service must be completed before submitting a review."})

            if hasattr(booking, 'review'):
                raise serializers.ValidationError({"booking_uuid": "You have already reviewed this booking."})

            attrs["booking"] = booking
            attrs["instant_booking"] = None
        else:
            try:
                instant_booking = InstantBooking.objects.get(instant_booking_uuid=instant_booking_uuid)
            except InstantBooking.DoesNotExist:
                raise serializers.ValidationError({"instant_booking_uuid": "Instant booking not found."})

            if instant_booking.customer != user:
                raise serializers.ValidationError({"instant_booking_uuid": "You do not own this booking."})

            if instant_booking.status != InstantBookingStatus.COMPLETED:
                raise serializers.ValidationError({"instant_booking_uuid": "Service must be completed before submitting a review."})

            if hasattr(instant_booking, 'review'):
                raise serializers.ValidationError({"instant_booking_uuid": "You have already reviewed this booking."})

            attrs["booking"] = None
            attrs["instant_booking"] = instant_booking

        return attrs

    def create(self, validated_data):
        booking = validated_data.pop("booking", None)
        instant_booking = validated_data.pop("instant_booking", None)
        validated_data.pop("booking_uuid", None)
        validated_data.pop("instant_booking_uuid", None)
        images = validated_data.pop("images", [])

        source = booking or instant_booking

        with transaction.atomic():
            review = Review.objects.create(
                booking=booking,
                instant_booking=instant_booking,
                customer=source.user if booking else source.customer,
                business=source.business if booking else source.assigned_business,
                service=source.service if booking else source.selected_service,
                employee=source.employee if booking else source.assigned_employee,
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
