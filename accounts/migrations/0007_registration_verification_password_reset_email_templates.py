from django.db import migrations


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="REGISTRATION_VERIFICATION",
        defaults={
            "subject": "Verify your TodayFix account",
            "message": (
                "Hi {{ first_name }},\n\n"
                "Welcome to TodayFix!\n\n"
                "Thank you for creating your account. Please "
                "verify your email address by clicking the "
                "button below.\n\n"
                "Your verification link is valid for "
                "{{ expiry_hours }}.\n\n"
                "If you did not create this account, you can "
                "safely ignore this email."
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="PASSWORD_RESET_LINK",
        defaults={
            "subject": "Reset your TodayFix password",
            "message": (
                "Hi {{ first_name }},\n\n"
                "We received a request to reset your TodayFix "
                "account password.\n\n"
                "Click the button below to create a new "
                "password.\n\n"
                "This password reset link is valid for "
                "{{ expiry_minutes }} minutes.\n\n"
                "If you did not request a password reset, you "
                "can safely ignore this email."
            ),
        },
    )


def delete_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(
        name__in=[
            "REGISTRATION_VERIFICATION",
            "PASSWORD_RESET_LINK",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_password_changed_email_template"),
    ]

    operations = [
        migrations.RunPython(create_templates, delete_templates),
    ]