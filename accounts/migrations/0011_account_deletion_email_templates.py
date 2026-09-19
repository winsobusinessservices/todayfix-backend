from django.db import migrations


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model(
        "accounts",
        "EmailTemplate",
    )

    EmailTemplate.objects.get_or_create(
        name="ACCOUNT_DELETION_OTP",
        defaults={
            "subject": "Your TodayFix Account Deletion OTP",
            "message": (
                "Hi {{ first_name }},\n\n"
                "We received a request to delete your TodayFix "
                "account.\n\n"
                "Your account deletion verification OTP is "
                "{{ otp }}.\n\n"
                "This OTP is valid for {{ expiry_minutes }} minutes.\n\n"
                "If you did not request account deletion, "
                "please ignore this email."
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="ACCOUNT_DELETION_SCHEDULED",
        defaults={
            "subject": "Your TodayFix Account Is Scheduled for Deletion",
            "message": (
                "Hi {{ first_name }},\n\n"
                "Your TodayFix account has been scheduled for deletion.\n\n"
                "Your account is scheduled to be deleted on "
                "{{ scheduled_deletion_at }}.\n\n"
                "You can cancel the deletion request before this date "
                "from your TodayFix profile."
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="ACCOUNT_DELETION_ON_HOLD",
        defaults={
            "subject": "Your TodayFix Account Deletion Is On Hold",
            "message": (
                "Hi {{ first_name }},\n\n"
                "Your TodayFix account deletion could not be completed "
                "because there are outstanding bookings or payments "
                "that need to be completed or cleared.\n\n"
                "Please complete the required actions within the "
                "allowed extension period.\n\n"
                "Your current extension deadline is "
                "{{ extension_deadline }}."
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="ACCOUNT_DELETION_CANCELLED",
        defaults={
            "subject": "Your TodayFix Account Deletion Was Cancelled",
            "message": (
                "Hi {{ first_name }},\n\n"
                "Your TodayFix account deletion request has been "
                "cancelled.\n\n"
                "Your account remains active and your data has not "
                "been deleted or anonymized."
            ),
        },
    )

    EmailTemplate.objects.get_or_create(
        name="ACCOUNT_DELETION_COMPLETED",
        defaults={
            "subject": "Your TodayFix Account Has Been Deleted",
            "message": (
                "Hi {{ first_name }},\n\n"
                "Your TodayFix account deletion has been completed.\n\n"
                "Your account has been anonymized and historical "
                "records have been retained where required."
            ),
        },
    )


def delete_templates(apps, schema_editor):
    EmailTemplate = apps.get_model(
        "accounts",
        "EmailTemplate",
    )

    EmailTemplate.objects.filter(
        name__in=[
            "ACCOUNT_DELETION_OTP",
            "ACCOUNT_DELETION_SCHEDULED",
            "ACCOUNT_DELETION_ON_HOLD",
            "ACCOUNT_DELETION_CANCELLED",
            "ACCOUNT_DELETION_COMPLETED",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0010_email_update_verification_template",
        ),
    ]

    operations = [
        migrations.RunPython(
            create_templates,
            delete_templates,
        ),
    ]