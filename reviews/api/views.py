from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from bookings.models import Booking
from reviews.models import Review, ReviewImage
from reviews.serializers import ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer

class ReviewCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=ReviewCreateSerializer, responses={201: ReviewSerializer})
    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            review = serializer.save()
            read_serializer = ReviewSerializer(review)
            return Response({"success": True, "message": "Review submitted successfully.", "data": read_serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"success": False, "message": "Validation error.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class MyReviewsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        reviews = Review.objects.filter(customer=request.user)
        serializer = ReviewSerializer(reviews, many=True)
        return Response({"success": True, "data": serializer.data})

class RatingSummaryAPIView(APIView):
    def get(self, request):
        business_uuid = request.query_params.get("business_uuid")
        service_uuid = request.query_params.get("service_uuid")
        
        if business_uuid and service_uuid:
            return Response({"success": False, "message": "Provide either business_uuid or service_uuid, not both."}, status=status.HTTP_400_BAD_REQUEST)
        if not business_uuid and not service_uuid:
            return Response({"success": False, "message": "Provide either business_uuid or service_uuid."}, status=status.HTTP_400_BAD_REQUEST)
            
        filters = {}
        if business_uuid: filters["business__business_profile_uuid"] = business_uuid
        if service_uuid: filters["service__service_uuid"] = service_uuid
            
        stats = Review.objects.filter(**filters).aggregate(
            total=Count("id"),
            avg=Avg("rating"),
            s5=Count("id", filter=Q(rating=5)),
            s4=Count("id", filter=Q(rating=4)),
            s3=Count("id", filter=Q(rating=3)),
            s2=Count("id", filter=Q(rating=2)),
            s1=Count("id", filter=Q(rating=1)),
        )
        total = stats["total"] or 0
        avg = round(stats["avg"], 1) if stats["avg"] else 0
        
        return Response({
            "success": True,
            "data": {
                "average_rating": avg,
                "total_reviews": total,
                "rating_distribution": {
                    "5": stats["s5"], "4": stats["s4"], "3": stats["s3"], "2": stats["s2"], "1": stats["s1"]
                }
            }
        })

class ReviewDetailAPIView(APIView):
    def get(self, request, review_uuid):
        review = get_object_or_404(Review, review_uuid=review_uuid)
        serializer = ReviewSerializer(review)
        return Response({"success": True, "data": serializer.data})
        
    def patch(self, request, review_uuid):
        review = get_object_or_404(Review, review_uuid=review_uuid)
        if review.customer != request.user:
            return Response({"success": False, "message": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            review = serializer.save()
            read_serializer = ReviewSerializer(review)
            return Response({"success": True, "data": read_serializer.data})
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_uuid):
        review = get_object_or_404(Review, review_uuid=review_uuid)
        if review.customer != request.user:
            return Response({"success": False, "message": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        review.delete()
        return Response({"success": True, "message": "Review deleted."})

class ReviewImageDeleteAPIView(APIView):
    def delete(self, request, review_uuid, image_uuid):
        review = get_object_or_404(Review, review_uuid=review_uuid)
        if review.customer != request.user:
            return Response({"success": False, "message": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        image = get_object_or_404(ReviewImage, review=review, image_uuid=image_uuid)
        image.delete()
        return Response({"success": True, "message": "Image deleted."})

class ReviewByBookingAPIView(APIView):
    def get(self, request, booking_uuid):
        review = get_object_or_404(Review, booking__uuid=booking_uuid)
        serializer = ReviewSerializer(review)
        return Response({"success": True, "data": serializer.data})

class ReviewEligibilityAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, booking_uuid):
        booking = get_object_or_404(Booking, uuid=booking_uuid)
        if booking.user != request.user:
            return Response({"success": False, "message": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
            
        if hasattr(booking, 'review'):
            return Response({"success": True, "data": {"eligible": False, "already_reviewed": True}})
            
        if booking.status != "COMPLETED":
            return Response({"success": True, "data": {"eligible": False, "already_reviewed": False, "reason": "Service must be completed."}})
            
        return Response({"success": True, "data": {"eligible": True, "already_reviewed": False}})

class BusinessReviewsAPIView(APIView):
    def get(self, request, business_uuid):
        rating = request.query_params.get("rating")
        reviews = Review.objects.filter(business__business_profile_uuid=business_uuid)
        if rating:
            reviews = reviews.filter(rating=rating)
        serializer = ReviewSerializer(reviews, many=True)
        return Response({"success": True, "data": serializer.data})

class ServiceReviewsAPIView(APIView):
    def get(self, request, service_uuid):
        rating = request.query_params.get("rating")
        reviews = Review.objects.filter(service__service_uuid=service_uuid)
        if rating:
            reviews = reviews.filter(rating=rating)
        serializer = ReviewSerializer(reviews, many=True)
        return Response({"success": True, "data": serializer.data})
