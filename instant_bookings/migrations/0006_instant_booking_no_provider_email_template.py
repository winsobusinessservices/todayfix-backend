from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="INSTANT_BOOKING_NO_PROVIDER",
        defaults={
            "subject": "We couldn't find a provider for your request",
            "message": (
                "<p>We're sorry, we could not find a provider for your "
                "instant booking request for "
                "<strong>{{ service_name }}</strong> within the search "
                "window.</p>"
                "<p>No amount has been charged. You can try again, "
                "possibly with a different time or a higher tip to "
                "attract more providers.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="INSTANT_BOOKING_NO_PROVIDER").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("instant_bookings", "0005_instant_booking_assigned_email_template"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]