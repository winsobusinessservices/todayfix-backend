from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="WELCOME_EMAIL",
        defaults={
            "subject": "Welcome to TodayFix!",
            "message": (
                "<p>Your account is all set up. We're glad to have "
                "you on TodayFix.</p>"
                "<p>You can now browse services, book providers near "
                "you, and track your bookings — all from the app.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="WELCOME_EMAIL").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]