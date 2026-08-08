from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
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
    UpdateProfileSerializer,
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
                            "first_name": "John",
                            "last_name": "  Doe",
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
                "first_name": "John",
                "last_name": "Doe",
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
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "data": {
                    "access": str(access),
                    "refresh": str(refresh),
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
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

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "success": True,
                "message": "Business account created successfully.",
                "data": {
                    "refresh": str(refresh),
                    "access": str(access),
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )

@extend_schema(
    auth=[],
    tags=["Login"],
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
                            "first_name": "Demo1",
                            "last_name": "User",
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
                    "access": str(access),
                    "refresh": str(refresh),
                    "id": user.id,
                    "uuid": str(user.uuid),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    
                },
            },
            status=status.HTTP_200_OK,
        )

@extend_schema(
    auth=[{"BearerAuth": []}],
    tags=["Login"],
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
    tags=["Accounts"],
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
                            "first_name": "Demo1",
                            "last_name": "User",
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
                    "id": request.user.id,
                    "firstName": request.user.first_name,
                    "lastName": request.user.last_name,
                    "role": request.user.role,
                    "hasBusiness": request.user.role == "BUSINESS",
                    "businessVerified": request.user.business_verified,
                    "email": request.user.email,
                    "profileImage": (
                        request.user.profile_picture.url
                        if request.user.profile_picture
                        else ""
                    ),
                "phone": request.user.phone,
                "joinedate": request.user.created_at.strftime("%b %Y"),
                "addresses": [],
                },
            },
            status=status.HTTP_200_OK,
        )
    
@extend_schema(
    tags=["Accounts"],
    summary="Update Profile",
    description="Update the authenticated user's profile.",
    request=UpdateProfileSerializer,
    responses={
        200: OpenApiResponse(
            description="Profile updated successfully.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "success": True,
                        "message": "Profile updated successfully.",
                        "data": {
                            "firstName": "",
                            "lastName": "",
                            "profileImage": "",
                            "phone": "",
                            "addresses": [],
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validation Error",
        ),
        401: OpenApiResponse(
            description="Authentication credentials were not provided.",
        ),
    },
    examples=[
        OpenApiExample(
            "Update Profile",
            value={
                "firstName": "",
                "lastName": "",
                "profileImage": "",
                "phone": "",
                "addresses": [],
            },
            request_only=True,
        ),
    ],
)
class UpdateProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()
        request.user.refresh_from_db()
        print(request.user.first_name)

        return Response(
            {
                "success": True,
                "message": "Profile updated successfully.",
                "data": {
                    "id": request.user.id,
                    "firstName": request.user.first_name,
                    "lastName": request.user.last_name,
                    "role": request.user.role,
                    "hasBusiness": request.user.role == "BUSINESS",
                    "businessVerified": request.user.business_verified,
                    "email": request.user.email,
                    "profileImage": (
                        request.user.profile_picture.url
                        if request.user.profile_picture
                        else ""
                    ),
                    "phone": request.user.phone,
                    "joinedate": request.user.created_at.strftime("%b %Y"),
                    "addresses": [],
                },
            },
            status=status.HTTP_200_OK,
        )
    



    