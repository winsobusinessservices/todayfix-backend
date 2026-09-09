from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BOOKING_COMPLETED",
        defaults={
            "subject": "Your TodayFix service is complete",
            "message": (
                "<p>Your <strong>{{ service_name }}</strong> service "
                "with <strong>{{ business_name }}</strong> on "
                "<strong>{{ scheduled_date }}</strong> has been "
                "marked as <strong>completed</strong>.</p>"
                "<p>Thank you for using TodayFix. We hope everything "
                "went well!</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="BOOKING_COMPLETED").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0003_booking_cancelled_email_templates"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]