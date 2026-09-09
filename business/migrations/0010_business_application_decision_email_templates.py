from django.db import migrations


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BUSINESS_APPLICATION_APPROVED",
        defaults={
            "subject": "Your TodayFix business application is approved",
            "message": (
                "<p>Congratulations! Your business application has "
                "been <strong>approved</strong>. You're now a "
                "TodayFix provider.</p>"
                "<p>You can now log in, set up your services and "
                "availability, and start receiving bookings.</p>"
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="BUSINESS_APPLICATION_REJECTED",
        defaults={
            "subject": "Update on your TodayFix business application",
            "message": (
                "<p>We've reviewed your business application and "
                "unfortunately it has not been approved at this "
                "time.</p>"
                "<p><strong>Reason:</strong> {{ rejection_reason }}</p>"
                "<p>You're welcome to submit a new application once "
                "the issue above has been addressed.</p>"
            ),
        },
    )


def delete_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(
        name__in=[
            "BUSINESS_APPLICATION_APPROVED",
            "BUSINESS_APPLICATION_REJECTED",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0009_business_application_received_email_template"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_templates, delete_templates),
    ]