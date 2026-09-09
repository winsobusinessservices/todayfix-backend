from django.db import migrations


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BUSINESS_UPGRADE_APPROVED",
        defaults={
            "subject": "Your business upgrade request is approved",
            "message": (
                "<p>Good news! Your request to upgrade "
                "<strong>{{ business_name }}</strong> to "
                "<strong>{{ requested_business_type }}</strong> has "
                "been <strong>approved</strong>.</p>"
                "<p>Your business profile has been updated. You can "
                "log in to see the changes.</p>"
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="BUSINESS_UPGRADE_REJECTED",
        defaults={
            "subject": "Update on your business upgrade request",
            "message": (
                "<p>We've reviewed your request to upgrade "
                "<strong>{{ business_name }}</strong> to "
                "<strong>{{ requested_business_type }}</strong> and "
                "unfortunately it has not been approved.</p>"
                "<p><strong>Reason:</strong> {{ rejection_reason }}</p>"
                "<p>You're welcome to submit a new upgrade request "
                "once the issue above has been addressed.</p>"
            ),
        },
    )


def delete_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(
        name__in=[
            "BUSINESS_UPGRADE_APPROVED",
            "BUSINESS_UPGRADE_REJECTED",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0012_business_upgrade_submitted_email_template"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_templates, delete_templates),
    ]