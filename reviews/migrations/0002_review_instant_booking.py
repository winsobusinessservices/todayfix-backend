import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('instant_bookings', '0006_instant_booking_no_provider_email_template'),
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='review',
            name='booking',
            field=models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='review',
                to='bookings.booking',
            ),
        ),
        migrations.AddField(
            model_name='review',
            name='instant_booking',
            field=models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='review',
                to='instant_bookings.instantbooking',
            ),
        ),
        migrations.AddConstraint(
            model_name='review',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(('booking__isnull', False), ('instant_booking__isnull', True))
                    | models.Q(('booking__isnull', True), ('instant_booking__isnull', False))
                ),
                name='review_exactly_one_booking_type',
            ),
        ),
    ]