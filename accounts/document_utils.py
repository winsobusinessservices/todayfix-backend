from django.urls import reverse


def get_profile_picture_url(user, request=None):
    """
    Returns the URL to view a user's profile picture through the
    protected ProfilePictureViewAPIView, instead of a raw /media/
    path. Returns "" if the user has no picture uploaded.
    """
    if not user or not user.profile_picture:
        return ""

    url = reverse(
        "profile-picture-view",
        kwargs={"user_uuid": user.user_uuid},
    )

    if request:
        url = request.build_absolute_uri(url)

    return url