from django.db import migrations


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")

    EmailTemplate.objects.get_or_create(
        name="EMPLOYEE_ADDED",
        defaults={
            "subject": "You've been added as staff on TodayFix",
            "message": (
                "<p><strong>{{ business_name }}</strong> has added you "
                "as a staff member on TodayFix.</p>"
                "<table style='margin-top:15px; font-size:15px; color:#333333;'>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Name</strong></td>"
                "<td>{{ employee_name }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Phone</strong></td>"
                "<td>{{ employee_phone }}</td></tr>"
                "<tr><td style='padding:4px 10px 4px 0;'><strong>Email</strong></td>"
                "<td>{{ employee_email }}</td></tr>"
                "</table>"
                "<p>If these details are incorrect, please contact "
                "{{ business_name }} to have them corrected.</p>"
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="EMPLOYEE_REMOVED",
        defaults={
            "subject": "You've been removed from a TodayFix business",
            "message": (
                "<p><strong>{{ business_name }}</strong> has removed "
                "you as a staff member on TodayFix.</p>"
                "<p>If you believe this was a mistake, please contact "
                "{{ business_name }} directly.</p>"
            ),
        },
    )


def delete_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("accounts", "EmailTemplate")
    EmailTemplate.objects.filter(
        name__in=["EMPLOYEE_ADDED", "EMPLOYEE_REMOVED"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("business", "0010_business_application_decision_email_templates"),
        ("accounts", "0004_alter_address_location"),
    ]

    operations = [
        migrations.RunPython(create_templates, delete_templates),
    ]