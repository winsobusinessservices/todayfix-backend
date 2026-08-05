from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from .serializers import (
    RegisterUserSerializer,
    RegisterBusinessSerializer,
)


class RegisterUserAPIView(CreateAPIView):
    """
    Register a normal user.
    """

    serializer_class = RegisterUserSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "data": {
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterBusinessAPIView(CreateAPIView):
    """
    Register a business account.
    """

    serializer_class = RegisterBusinessSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Business account created successfully.",
                "data": {
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )
    