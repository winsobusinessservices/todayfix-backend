from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('instant_bookings', '0006_instant_booking_no_provider_email_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='instantbooking',
            name='completed_at',
            field=models.DateTimeField(blank=True, help_text='Timestamp when the booking transitioned to COMPLETED.', null=True),
        ),
    ]