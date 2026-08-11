from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_todayfix_email(
    *,
    to_email,
    subject,
    first_name,
    message,
    otp=None,
    reset_link=None,
    additional_message=None,
):
    context = {
        "subject": subject,
        "first_name": first_name,
        "message": message,
        "otp": otp,
        "reset_link": reset_link,
        "additional_message": additional_message,
        "logo_url": getattr(settings, "EMAIL_LOGO_URL", ""),
    }

    html_content = render_to_string(
        "emails/base_email.html",
        context,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send()
    