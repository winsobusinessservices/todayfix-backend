from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0006_service_completion_otp_email_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookingcompletionotp",
            name="otp",
            field=models.CharField(default="", max_length=6),
        ),
    ]