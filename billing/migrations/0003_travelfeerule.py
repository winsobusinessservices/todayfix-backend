import uuid
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_billingrecord_unique_draft_per_booking_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TravelFeeRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rule_uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('free_distance_km', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('rate_per_km', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('effective_from', models.DateTimeField(default=django.utils.timezone.now)),
                ('effective_to', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'ordering': ['-effective_from'],
            },
        ),
    ]