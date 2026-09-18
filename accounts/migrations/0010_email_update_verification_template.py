from django.db import migrations


def create_template(apps, schema_editor):

    EmailTemplate = apps.get_model(
        "accounts",
        "EmailTemplate",
    )

    EmailTemplate.objects.get_or_create(
        name="EMAIL_UPDATE_VERIFICATION",
        defaults={
            "subject": "Verify your new TodayFix email address",
            "message": (
                "Hi {{ first_name }},\n\n"
                "You requested to add this email address "
                "to your TodayFix profile.\n\n"
                "Please verify your email address by clicking "
                "the button below.\n\n"
                "This verification link is valid for "
                "{{ expiry_minutes }} minutes.\n\n"
                "If you did not request this change, you can "
                "safely ignore this email."
            ),
        },
    )


def delete_template(apps, schema_editor):

    EmailTemplate = apps.get_model(
        "accounts",
        "EmailTemplate",
    )

    EmailTemplate.objects.filter(
        name="EMAIL_UPDATE_VERIFICATION"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0009_emailupdateverification",
        ),
    ]

    operations = [
        migrations.RunPython(
            create_template,
            delete_template,
        ),
    ]