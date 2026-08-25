from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailOrPhoneBackend(ModelBackend):

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs
    ):

        username = username or kwargs.get("email")

        if username is None or password is None:
            return None

        identifier = str(username).strip()

        # =================================================
        # EMAIL LOGIN
        # =================================================

        if "@" in identifier:

            try:

                user = User.objects.get(
                    email__iexact=identifier
                )

            except User.DoesNotExist:

                return None

        # =================================================
        # PHONE LOGIN
        # =================================================

        else:

            phone = identifier

            # +91XXXXXXXXXX -> XXXXXXXXXX
            if phone.startswith("+91"):

                phone = phone[3:]

            # 91XXXXXXXXXX -> XXXXXXXXXX
            elif (
                phone.startswith("91")
                and len(phone) == 12
            ):

                phone = phone[2:]

            try:

                user = User.objects.get(
                    phone=phone
                )

            except User.DoesNotExist:

                return None

        # =================================================
        # PASSWORD
        # =================================================

        if (
            user.check_password(password)
            and self.user_can_authenticate(user)
        ):

            return user

        return None