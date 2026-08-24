from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    CategoryDetailAPIView,
    CategoryListCreateAPIView,
    SubCategoryDetailAPIView,
    SubCategoryListCreateAPIView,
)


urlpatterns = [

    path(
        "",
        CategoryListCreateAPIView.as_view(),
        name="category-list-create",
    ),

    path(
        "<uuid:cat_uuid>/",
        CategoryDetailAPIView.as_view(),
        name="category-detail",
    ),

    path(
        "<uuid:cat_uuid>/subcategories/",
        SubCategoryListCreateAPIView.as_view(),
        name="subcategory-list-create",
    ),

    path(
        "subcategories/<uuid:subCat_uuid>/",
        SubCategoryDetailAPIView.as_view(),
        name="subcategory-detail",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

