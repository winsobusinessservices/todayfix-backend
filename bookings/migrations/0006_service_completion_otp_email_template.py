from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="SERVICE_COMPLETION_OTP",
        defaults={
            "subject": "OTP to confirm your TodayFix service completion",
            "message": (
                "<p>Your provider has marked your "
                "<strong>{{ service_name }}</strong> service with "
                "<strong>{{ business_name }}</strong> as complete.</p>"
                "<p>Please share the OTP below with your provider to "
                "confirm the service is done.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="SERVICE_COMPLETION_OTP").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0005_bookingcompletionotp"),
        ("accounts", "0008_rename_provider_request_id_otpverification_external_request_id_and_more"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]