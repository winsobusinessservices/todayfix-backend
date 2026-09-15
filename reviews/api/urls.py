from django.urls import path
from . import views

urlpatterns = [
    path("", views.ReviewCreateAPIView.as_view(), name="review-create"),
    path("my/", views.MyReviewsAPIView.as_view(), name="my-reviews"),
    path("rating-summary/", views.RatingSummaryAPIView.as_view(), name="rating-summary"),
    path("<uuid:review_uuid>/", views.ReviewDetailAPIView.as_view(), name="review-detail"),
    path("<uuid:review_uuid>/images/<uuid:image_uuid>/", views.ReviewImageDeleteAPIView.as_view(), name="review-image-delete"),
    path("booking/<uuid:booking_uuid>/", views.ReviewByBookingAPIView.as_view(), name="review-by-booking"),
    path("booking/<uuid:booking_uuid>/eligibility/", views.ReviewEligibilityAPIView.as_view(), name="review-eligibility"),
    path("business/<uuid:business_uuid>/", views.BusinessReviewsAPIView.as_view(), name="business-reviews"),
    path("service/<uuid:service_uuid>/", views.ServiceReviewsAPIView.as_view(), name="service-reviews"),
]
