from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_travelfeerule'),
    ]

    operations = [
        migrations.AddField(
            model_name='platformfeerule',
            name='booking_type',
            field=models.CharField(
                choices=[('SCHEDULED', 'Scheduled'), ('INSTANT', 'Instant'), ('BOTH', 'Both')],
                default='BOTH',
                max_length=20,
            ),
        ),
    ]