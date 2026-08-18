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

