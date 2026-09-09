from django.db import migrations


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BOOKING_CANCELLED_CUSTOMER",
        defaults={
            "subject": "Your TodayFix booking has been cancelled",
            "message": (
                "<p>This confirms your booking with "
                "<strong>{{ business_name }}</strong> for "
                "<strong>{{ service_name }}</strong> on "
                "<strong>{{ scheduled_date }}</strong> has been "
                "<strong>cancelled</strong> as requested.</p>"
                "<p>You can book again anytime from the app.</p>"
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="BOOKING_CANCELLED_BUSINESS",
        defaults={
            "subject": "A booking has been cancelled by the customer",
            "message": (
                "<p>Heads up! <strong>{{ customer_name }}</strong> has "
                "cancelled their booking for "
                "<strong>{{ service_name }}</strong> scheduled on "
                "<strong>{{ scheduled_date }}</strong>.</p>"
                "<p>No action is needed from your side.</p>"
            ),
        },
    )


def delete_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(
        name__in=[
            "BOOKING_CANCELLED_CUSTOMER",
            "BOOKING_CANCELLED_BUSINESS",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0002_booking_email_templates"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_templates, delete_templates),
    ]