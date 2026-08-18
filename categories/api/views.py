from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Category, SubCategory
from .permissions import IsAdminRole
from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
)


class CategoryListCreateAPIView(APIView):
    """
    GET:
        List active categories.

    POST:
        ADMIN only - create category.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                IsAdminRole(),
            ]

        return [
            IsAuthenticated(),
        ]

    @extend_schema(
        tags=["Categories"],
        summary="List categories",
        responses=CategorySerializer(many=True),
    )
    def get(self, request):

        categories = (
            Category.objects
            .filter(is_active=True)
            .prefetch_related("subcategories")
        )

        serializer = CategorySerializer(
            categories,
            many=True,
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    @extend_schema(
        tags=["Categories"],
        summary="Create category",
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
        },
    )
    def post(self, request):

        serializer = CategorySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        category = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Category created successfully.",
                "data": CategorySerializer(
                    category
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CategoryDetailAPIView(APIView):
    """
    ADMIN can update category.
    Authenticated users can view it.
    """

    def get_permissions(self):

        if self.request.method in ["PATCH", "PUT", "DELETE"]:
            return [
                IsAuthenticated(),
                IsAdminRole(),
            ]

        return [
            IsAuthenticated(),
        ]

    @extend_schema(
        tags=["Categories"],
        summary="Get category details",
        responses=CategorySerializer,
    )
    def get(self, request, cat_uuid):

        category = get_object_or_404(
            Category.objects.prefetch_related(
                "subcategories"
            ),
            cat_uuid=cat_uuid,
            is_active=True,
        )

        serializer = CategorySerializer(category)

        return Response({
            "success": True,
            "data": serializer.data,
        })

    @extend_schema(
        tags=["Categories"],
        summary="Update category",
        request=CategorySerializer,
        responses=CategorySerializer,
    )
    def patch(self, request, cat_uuid):

        category = get_object_or_404(
            Category,
            cat_uuid=cat_uuid,
        )

        serializer = CategorySerializer(
            category,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        category = serializer.save()

        return Response({
            "success": True,
            "message": "Category updated successfully.",
            "data": CategorySerializer(
                category
            ).data,
        })


class SubCategoryListCreateAPIView(APIView):
    """
    GET:
        List active subcategories under a category.

    POST:
        ADMIN only - create subcategory.
    """

    def get_permissions(self):

        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                IsAdminRole(),
            ]

        return [
            IsAuthenticated(),
        ]

    @extend_schema(
        tags=["SubCategories"],
        summary="List subcategories",
        responses=SubCategorySerializer(many=True),
    )
    def get(self, request, cat_uuid):

        category = get_object_or_404(
            Category,
            cat_uuid=cat_uuid,
            is_active=True,
        )

        subcategories = SubCategory.objects.filter(
            category=category,
            is_active=True,
        )

        serializer = SubCategorySerializer(
            subcategories,
            many=True,
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    @extend_schema(
        tags=["SubCategories"],
        summary="Create subcategory",
        request=SubCategorySerializer,
        responses={
            201: SubCategorySerializer,
        },
    )
    def post(self, request, cat_uuid):

        category = get_object_or_404(
            Category,
            cat_uuid=cat_uuid,
            is_active=True,
        )

        serializer = SubCategorySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        subcategory = serializer.save(
            category=category
        )

        return Response(
            {
                "success": True,
                "message": "Subcategory created successfully.",
                "data": SubCategorySerializer(
                    subcategory
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class SubCategoryDetailAPIView(APIView):

    def get_permissions(self):

        if self.request.method in ["PATCH", "PUT", "DELETE"]:
            return [
                IsAuthenticated(),
                IsAdminRole(),
            ]

        return [
            IsAuthenticated(),
        ]

    @extend_schema(
        tags=["SubCategories"],
        summary="Get subcategory",
        responses=SubCategorySerializer,
    )
    def get(self, request, subCat_uuid):

        subcategory = get_object_or_404(
            SubCategory.objects.select_related(
                "category"
            ),
            subCat_uuid=subCat_uuid,
            is_active=True,
        )

        serializer = SubCategorySerializer(
            subcategory
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    @extend_schema(
        tags=["SubCategories"],
        summary="Update subcategory",
        request=SubCategorySerializer,
        responses=SubCategorySerializer,
    )
    def patch(self, request, subCat_uuid):

        subcategory = get_object_or_404(
            SubCategory,
            subCat_uuid=subCat_uuid,
        )

        serializer = SubCategorySerializer(
            subcategory,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        subcategory = serializer.save()

        return Response({
            "success": True,
            "message": "Subcategory updated successfully.",
            "data": SubCategorySerializer(
                subcategory
            ).data,
        })

        