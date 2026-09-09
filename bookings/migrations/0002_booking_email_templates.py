from django.db import migrations


def create_booking_email_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BOOKING_CONFIRMED",
        defaults={
            "subject": "Your TodayFix booking is confirmed",
            "message": (
                "<p>Good news! Your booking with "
                "<strong>{{ business_name }}</strong> has been "
                "<strong>confirmed</strong>.</p>"
                "<table style='margin-top:15px; font-size:15px; color:#333333;'>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Service</strong></td>"
                "<td>{{ service_name }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Date</strong></td>"
                "<td>{{ scheduled_date }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Time Slot</strong></td>"
                "<td>{{ slot_type }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Price</strong></td>"
                "<td>₹{{ price }}</td></tr>"
                "</table>"
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="BOOKING_REJECTED",
        defaults={
            "subject": "Your TodayFix booking was not accepted",
            "message": (
                "<p>We're sorry, your booking with "
                "<strong>{{ business_name }}</strong> for "
                "<strong>{{ service_name }}</strong> on "
                "<strong>{{ scheduled_date }}</strong> could not be "
                "accepted.</p>"
                "<p>You can try booking with another provider or a "
                "different time slot.</p>"
            ),
        },
    )


def delete_booking_email_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(
        name__in=["BOOKING_CONFIRMED", "BOOKING_REJECTED"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0001_initial"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(
            create_booking_email_templates,
            delete_booking_email_templates,
        ),
    ]