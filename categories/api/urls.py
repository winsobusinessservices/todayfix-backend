from django.urls import path

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
        "<uuid:uuid>/",
        CategoryDetailAPIView.as_view(),
        name="category-detail",
    ),

    path(
        "<uuid:category_uuid>/subcategories/",
        SubCategoryListCreateAPIView.as_view(),
        name="subcategory-list-create",
    ),

    path(
        "subcategories/<uuid:uuid>/",
        SubCategoryDetailAPIView.as_view(),
        name="subcategory-detail",
    ),
]

