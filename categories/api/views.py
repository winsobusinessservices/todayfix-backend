from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Category, SubCategory
from .permissions import IsAdminRole
from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
)

from rest_framework.parsers import MultiPartParser, FormParser

from accounts.choices import UserRole


class CategoryListCreateAPIView(APIView):
    """
    GET:
        List categories.

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
            AllowAny(),
        ]

    @extend_schema(
        tags=["Categories"],
        summary="List categories",
        responses=CategorySerializer(many=True),
    )
    def get(self, request):

        categories = (
            Category.objects
            .prefetch_related("subcategories")
        )

        # Admins can see both active and inactive categories
        if getattr(request.user, "role", None) != UserRole.ADMIN:
            categories = categories.filter(
                is_active=True
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
            AllowAny(),
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
        )

        # Non-admins can only view active categories
        if (
            getattr(request.user, "role", None) != UserRole.ADMIN
            and not category.is_active
        ):
            return Response(
                {
                    "success": False,
                    "message": "Category not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
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
        List subcategories under a category.

    POST:
        ADMIN only - create subcategory.
    """

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def get_permissions(self):

        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                IsAdminRole(),
            ]

        return [
            AllowAny(),
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
        )

        # Non-admins can only access an active category
        if getattr(request.user, "role", None) != UserRole.ADMIN:
            category = get_object_or_404(
                Category,
                cat_uuid=cat_uuid,
                is_active=True,
            )

        subcategories = SubCategory.objects.filter(
            category=category,
        )

        # Non-admins can only see active subcategories
        if getattr(request.user, "role", None) != UserRole.ADMIN:
            subcategories = subcategories.filter(
                is_active=True
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

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def get_permissions(self):

        if self.request.method in ["PATCH", "PUT", "DELETE"]:
            return [
                IsAuthenticated(),
                IsAdminRole(),
            ]

        return [
            AllowAny(),
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
        )

        # Non-admins can only view active subcategories
        if (
            getattr(request.user, "role", None) != UserRole.ADMIN
            and not subcategory.is_active
        ):
            return Response(
                {
                    "success": False,
                    "message": "Subcategory not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Non-admins also cannot view a subcategory
        # belonging to an inactive category
        if (
            getattr(request.user, "role", None) != UserRole.ADMIN
            and not subcategory.category.is_active
        ):
            return Response(
                {
                    "success": False,
                    "message": "Subcategory not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
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

        