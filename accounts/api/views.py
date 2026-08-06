from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
)

from .serializers import (
    RegisterUserSerializer,
    RegisterBusinessSerializer,
    LoginSerializer,
    LogoutSerializer,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

@extend_schema(
    auth=[],
    tags=["SignUp"],
    summary="Register User",
    description="Registers a new user with role USER.",
    request=RegisterUserSerializer,
    responses={
        201: OpenApiResponse(
            description="User registered successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "User registered successfully.",
                        "data": {
                            "id": 1,
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "full_name": "John Doe",
                            "email": "john@example.com",
                            "phone": "+919876543210",
                            "role": "USER",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validation Error",
            examples=[
                OpenApiExample(
                    "Passwords do not match",
                    value={
                        "confirm_password": [
                            "Passwords do not match."
                        ]
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Email already exists",
                    value={
                        "email": [
                            "A user with this email already exists."
                        ]
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Register User",
            value={
                "full_name": "John Doe",
                "email": "john@example.com",
                "phone": "+919876543210",
                "password": "Password@123",
                "confirm_password": "Password@123",
            },
            request_only=True,
        ),
    ],
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

@extend_schema(
    auth=[],
    tags=["Signup"],
    summary="Register Business",
    description="Registers a new business account.",
    request=RegisterBusinessSerializer,
)
class RegisterBusinessAPIView(CreateAPIView):
    """
    Register a business account.
    """


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

@extend_schema(
    auth=[],
    tags=["Authentication"],
    summary="Login",
    description="Login using email and password.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            description="Login successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Login successful.",
                        "data": {
                            "id": 1,
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "full_name": "Demo1 User",
                            "email": "demo1@example.com",
                            "phone": "+919876543210",
                            "role": "USER",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validation Error",
            examples=[
                OpenApiExample(
                    "Invalid Credentials",
                    value={
                        "detail": [
                            "Invalid email or password."
                        ]
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Email Required",
                    value={
                        "email": [
                            "This field is required."
                        ]
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Password Required",
                    value={
                        "password": [
                            "This field is required."
                        ]
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Login User",
            value={
                "email": "demo1@example.com",
                "password": "Password@123"
            },
            request_only=True,
        ),
    ],
)

class LoginAPIView(CreateAPIView):

    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": {
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "access": str(access),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Authentication"],
    summary="Logout",
    description="Logout the user by blacklisting the refresh token.",
    request=LogoutSerializer,
    responses={
        200: OpenApiResponse(
            description="Logout successful.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Logout successful."
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid refresh token.",
            examples=[
                OpenApiExample(
                    "Invalid Token",
                    value={
                        "detail": "Invalid refresh token."
                    },
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            "Logout",
            value={
                "refresh": "<refresh_token>"
            },
            request_only=True,
        ),
    ],
)
class LogoutAPIView(CreateAPIView):

    serializer_class = LogoutSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Logout successful.",
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Authentication"],
    summary="Profile",
    description="Retrieve the profile details of the authenticated user.",
    responses={
        200: OpenApiResponse(
            description="Profile fetched successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Profile fetched successfully.",
                        "data": {
                            "id": 1,
                            "uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "full_name": "Demo1 User",
                            "email": "demo1@example.com",
                            "phone": "+919876543210",
                            "role": "USER",
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided.",
        ),
    },
)
class ProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        return Response(
            {
                "success": True,
                "message": "Profile fetched successfully.",
                "data": {
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )