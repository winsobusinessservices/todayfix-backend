from django.urls import path

from .views import (
    RegisterUserAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    UpdateProfileAPIView,
    UnifiedPasswordResetView,
    ForgotPasswordView,
    ListUserAddressesAPIView,
    CreateUserAddressAPIView,
    GetUserAddressAPIView,
    UpdateUserAddressAPIView,
    DeleteUserAddressAPIView,
    VerifyEmailAPIView,
)


urlpatterns = [

    path(
        "register/user/",
        RegisterUserAPIView.as_view(),
        name="register-user",
    ),

    path(
        "login/",
        LoginAPIView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="logout",
    ),

    path(
        "profile/",
        ProfileAPIView.as_view(),
        name="profile",
    ),

    path(
        "profile/update/",
        UpdateProfileAPIView.as_view(),
        name="update-profile",
    ),

    path(
        "reset-password/",
        UnifiedPasswordResetView.as_view(),
        name="unified-reset-password",
    ),

    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),

    # Address APIs

    path(
        "users/me/addresses/",
        ListUserAddressesAPIView.as_view(),
        name="list-user-addresses",
    ),

    path(
        "users/me/addresses/add-address/",
        CreateUserAddressAPIView.as_view(),
        name="create-user-address",
    ),

    path(
        "users/me/addresses/<int:address_id>/",
        GetUserAddressAPIView.as_view(),
        name="get-user-address",
    ),

    path(
        "users/me/addresses/<int:address_id>/update-address/",
        UpdateUserAddressAPIView.as_view(),
        name="update-user-address",
    ),

    path(
        "users/me/addresses/<int:address_id>/delete-address/",
        DeleteUserAddressAPIView.as_view(),
        name="delete-user-address",
    ),
    path(
        "register/user/",
        RegisterUserAPIView.as_view(),
        name="register-user",
    ),

    path(
        "verify-email/",
        VerifyEmailAPIView.as_view(),
        name="verify-email",
    ),
]