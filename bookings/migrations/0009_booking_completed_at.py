from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_rename_bookings_bo_booking_1a2b3c_idx_bookings_bo_booking_147844_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='completed_at',
            field=models.DateTimeField(blank=True, help_text='Timestamp when the booking transitioned to COMPLETED.', null=True),
        ),
    ]