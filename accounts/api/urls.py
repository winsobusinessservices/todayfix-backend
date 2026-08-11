from django.urls import path

from .views import (
    RegisterUserAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    UpdateProfileAPIView,
    UnifiedPasswordResetView,
    ForgotPasswordView,
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
    
]








