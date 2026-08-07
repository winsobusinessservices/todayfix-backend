from django.urls import path

from .views import (
    RegisterUserAPIView,
    RegisterBusinessAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    UpdateProfileAPIView,
)

urlpatterns = [

    path(
        "register/user/",
        RegisterUserAPIView.as_view(),
        name="register-user",
    ),

    path(
        "register/business/",
        RegisterBusinessAPIView.as_view(),
        name="register-business",
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


    
]





