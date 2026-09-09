from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="BUSINESS_APPLICATION_RECEIVED",
        defaults={
            "subject": "We've received your TodayFix business application",
            "message": (
                "<p>Thanks for applying to become a provider on "
                "TodayFix! We've received your application and our "
                "team will review it shortly.</p>"
                "<table style='margin-top:15px; font-size:15px; color:#333333;'>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Business Type</strong></td>"
                "<td>{{ business_type }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Category</strong></td>"
                "<td>{{ category_name }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Location</strong></td>"
                "<td>{{ location }}</td></tr>"
                "</table>"
                "<p>We'll email you as soon as a decision is made.</p>"
            ),
        },
    )


def delete_template(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(name="BUSINESS_APPLICATION_RECEIVED").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0008_remove_employeeworkingschedule_unique_owner_schedule_slot_and_more"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]