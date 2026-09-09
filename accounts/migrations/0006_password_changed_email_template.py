from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="PASSWORD_CHANGED",
        defaults={
            "subject": "Your TodayFix password has been changed",
            "message": (
                "<p>This is a confirmation that your TodayFix account "
                "password was changed successfully.</p>"
                "<p>If you did not make this change, please reset "
                "your password immediately and contact our support "
                "team.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="PASSWORD_CHANGED").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_welcome_email_template"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]