from django.contrib import admin
from .models import Review, ReviewImage

class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("review_uuid", "booking", "instant_booking", "customer", "business", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("customer__email", "business__name", "review_uuid")
    inlines = [ReviewImageInline]
    readonly_fields = ("review_uuid", "created_at", "updated_at")

@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ("image_uuid", "review", "created_at")
    readonly_fields = ("image_uuid", "created_at")
