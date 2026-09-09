from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from accounts.models import EmailTemplate


def send_instant_booking_email(
    booking,
    template_name,
    placeholders,
    recipient=None,
):
    """
    Fetches an EmailTemplate by name, fills in the placeholders,
    and emails the given recipient (defaults to the customer,
    booking.customer). Same pattern as bookings/services.py's
    _send_booking_email.
    """

    recipient = recipient or booking.customer

    if not recipient.email:
        return

    try:
        template = EmailTemplate.objects.get(name=template_name)
    except EmailTemplate.DoesNotExist:
        return

    message = template.message

    for key, value in placeholders.items():
        message = message.replace(
            "{{ " + key + " }}",
            str(value),
        )

    html_message = render_to_string(
        "emails/base_email.html",
        {
            "subject": template.subject,
            "logo_url": settings.EMAIL_LOGO_URL,
            "first_name": recipient.first_name,
            "message": message,
            "otp": "",
            "additional_message": "",
        },
    )

    email_message = EmailMultiAlternatives(
        subject=template.subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient.email],
    )

    email_message.attach_alternative(
        html_message,
        "text/html",
    )

    email_message.send(
        fail_silently=True,
    )