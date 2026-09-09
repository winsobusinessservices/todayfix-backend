from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BUSINESS_UPGRADE_SUBMITTED",
        defaults={
            "subject": "Your business upgrade request has been received",
            "message": (
                "<p>We've received your request to upgrade "
                "<strong>{{ business_name }}</strong> from "
                "<strong>{{ current_business_type }}</strong> to "
                "<strong>{{ requested_business_type }}</strong>.</p>"
                "<p>Our team will review your submitted documents and "
                "get back to you shortly.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="BUSINESS_UPGRADE_SUBMITTED").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0011_employee_added_removed_email_templates"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]