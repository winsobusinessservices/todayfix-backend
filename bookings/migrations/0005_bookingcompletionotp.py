import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0004_booking_completed_email_template"),
        ("instant_bookings", "0006_instant_booking_no_provider_email_template"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingCompletionOTP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("otp_verification_uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("otp_hash", models.CharField(max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("is_used", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("booking", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="completion_otps", to="bookings.booking")),
                ("instant_booking", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="completion_otps", to="instant_bookings.instantbooking")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="bookingcompletionotp",
            index=models.Index(fields=["booking", "is_used"], name="bookings_bo_booking_1a2b3c_idx"),
        ),
        migrations.AddIndex(
            model_name="bookingcompletionotp",
            index=models.Index(fields=["instant_booking", "is_used"], name="bookings_bo_instant_4d5e6f_idx"),
        ),
        migrations.AddConstraint(
            model_name="bookingcompletionotp",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("booking__isnull", False), ("instant_booking__isnull", True))
                    | models.Q(("booking__isnull", True), ("instant_booking__isnull", False))
                ),
                name="completion_otp_exactly_one_booking_type",
            ),
        ),
    ]