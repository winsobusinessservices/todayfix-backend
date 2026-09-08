import logging

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is not None:
        return response

    view = context.get("view")
    logger.exception(
        "Unhandled exception in %s: %s",
        getattr(view, "__class__", view),
        exc,
    )

    return Response(
        {
            "success": False,
            "message": "Something went wrong. Please try again later.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )