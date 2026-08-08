from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from accounts.choices import UserRole
from .serializers import (
    BusinessProfileSerializer,
    BusinessUpgradeRequestSerializer,
    ManagedBusinessSerializer,
    RejectUpgradeSerializer,
)
from ..choices import BusinessType, UpgradeRequestStatus
from ..models import BusinessProfile, BusinessUpgradeRequest, ManagedBusiness
from ..services import BusinessUpgradeService
from ..permissions import IsAdminRole


class SubmitBusinessUpgradeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Business Upgrade"],
        request=BusinessUpgradeRequestSerializer,
        responses=BusinessUpgradeRequestSerializer,
    )
    def post(self, request):
        if request.user.role != UserRole.USER:
            return Response(
                {"success": False, "message": "Only USER accounts can request a business upgrade."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BusinessUpgradeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            upgrade = BusinessUpgradeService.submit(
                request.user,
                serializer.validated_data.get("reason", ""),
            )
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "success": True,
                "message": "Business upgrade request submitted for admin review.",
                "data": BusinessUpgradeRequestSerializer(upgrade).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BusinessUpgradeStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Business Upgrade"], responses=BusinessUpgradeRequestSerializer(many=True))
    def get(self, request):
        requests = BusinessUpgradeRequest.objects.filter(user=request.user)
        return Response(
            {
                "success": True,
                "data": BusinessUpgradeRequestSerializer(requests, many=True).data,
            }
        )


class AdminUpgradeRequestListAPIView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(tags=["Business Administration"], responses=BusinessUpgradeRequestSerializer(many=True))
    def get(self, request):
        requests = BusinessUpgradeRequest.objects.select_related("user", "reviewed_by")
        status_filter = request.query_params.get("status")
        if status_filter:
            requests = requests.filter(status=status_filter.upper())
        return Response({"success": True, "data": BusinessUpgradeRequestSerializer(requests, many=True).data})


class AdminApproveUpgradeAPIView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(tags=["Business Administration"], request=None)
    def post(self, request, pk):
        upgrade = get_object_or_404(BusinessUpgradeRequest, pk=pk)
        try:
            upgrade = BusinessUpgradeService.approve(upgrade, request.user)
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "success": True,
            "message": "Business upgrade approved. User role is now BUSINESS.",
            "data": BusinessUpgradeRequestSerializer(upgrade).data,
        })


class AdminRejectUpgradeAPIView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(tags=["Business Administration"], request=RejectUpgradeSerializer)
    def post(self, request, pk):
        upgrade = get_object_or_404(BusinessUpgradeRequest, pk=pk)
        serializer = RejectUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            upgrade = BusinessUpgradeService.reject(
                upgrade,
                request.user,
                serializer.validated_data.get("reason", ""),
            )
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "success": True,
            "message": "Business upgrade request rejected.",
            "data": BusinessUpgradeRequestSerializer(upgrade).data,
        })


class BusinessProfileListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Business Profiles"], responses=BusinessProfileSerializer(many=True))
    def get(self, request):
        profiles = BusinessProfile.objects.filter(owner=request.user)
        return Response({"success": True, "data": BusinessProfileSerializer(profiles, many=True).data})

    @extend_schema(tags=["Business Profiles"], request=BusinessProfileSerializer, responses=BusinessProfileSerializer)
    def post(self, request):
        if request.user.role != UserRole.BUSINESS:
            return Response({"success": False, "message": "Business approval is required first."}, status=status.HTTP_403_FORBIDDEN)

        serializer = BusinessProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(owner=request.user)
        return Response({"success": True, "message": "Business profile created.", "data": BusinessProfileSerializer(profile).data}, status=status.HTTP_201_CREATED)


class ManagedBusinessCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Business Management"], request=ManagedBusinessSerializer, responses=ManagedBusinessSerializer)
    def post(self, request):
        if request.user.role != UserRole.BUSINESS:
            return Response({"success": False, "message": "BUSINESS role required."}, status=status.HTTP_403_FORBIDDEN)

        linked = get_object_or_404(BusinessProfile, pk=request.data.get("linked_business"))
        manager = get_object_or_404(BusinessProfile, pk=request.data.get("manager_business"))

        if manager.owner_id != request.user.id:
            return Response({"success": False, "message": "You do not own the manager business."}, status=status.HTTP_403_FORBIDDEN)

        if manager.business_type not in {BusinessType.COMPANY, BusinessType.INVESTOR}:
            return Response({"success": False, "message": "Only COMPANY and INVESTOR profiles can manage businesses."}, status=status.HTTP_400_BAD_REQUEST)

        relation = ManagedBusiness(manager_business=manager, linked_business=linked)
        try:
            relation.full_clean()
            relation.save()
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "message": "Business linked successfully.", "data": ManagedBusinessSerializer(relation).data}, status=status.HTTP_201_CREATED)
