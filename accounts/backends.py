from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailOrPhoneBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        username = username or kwargs.get("email")

        if username is None or password is None:
            return None

        try:
            user = User.objects.get(email=username)

        except User.DoesNotExist:
            try:
                user = User.objects.get(phone=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None