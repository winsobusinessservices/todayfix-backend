from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="INSTANT_BOOKING_ASSIGNED",
        defaults={
            "subject": "A provider has been assigned to your request",
            "message": (
                "<p>Good news! <strong>{{ business_name }}</strong> "
                "has accepted your instant booking request for "
                "<strong>{{ service_name }}</strong>.</p>"
                "<table style='margin-top:15px; font-size:15px; color:#333333;'>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Provider</strong></td>"
                "<td>{{ business_name }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Service</strong></td>"
                "<td>{{ service_name }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Total Payable</strong></td>"
                "<td>₹{{ total_payable_price }}</td></tr>"
                "</table>"
                "<p>You can chat with your provider directly in the app.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="INSTANT_BOOKING_ASSIGNED").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("instant_bookings", "0004_instantbooking_offer_round_and_more"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]