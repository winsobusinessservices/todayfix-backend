from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('billing', '0004_platformfeerule_booking_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingrecord',
            name='confirmed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='confirmed_billing_records',
                to=settings.AUTH_USER_MODEL,
                help_text='Business owner (or admin) who confirmed this billing record via the confirm action.',
            ),
        ),
    ]