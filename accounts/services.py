from accounts.models import CustomUser
from accounts.choices import UserRole


class AuthService:

    @staticmethod
    def register_user(validated_data):

        validated_data["role"] = UserRole.USER

        return CustomUser.objects.create_user(
            **validated_data
        )

    @staticmethod
    def register_business(validated_data):

        validated_data["role"] = UserRole.BUSINESS

        return CustomUser.objects.create_user(
            **validated_data
        )