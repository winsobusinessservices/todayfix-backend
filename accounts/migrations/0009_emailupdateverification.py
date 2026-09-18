from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0008_rename_provider_request_id_otpverification_external_request_id_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailUpdateVerification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "email_update_verification_uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        db_index=True,
                        max_length=254,
                    ),
                ),
                (
                    "token",
                    models.CharField(
                        max_length=128,
                        unique=True,
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(),
                ),
                (
                    "is_used",
                    models.BooleanField(
                        default=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="email_update_verifications",
                        to="accounts.customuser",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]