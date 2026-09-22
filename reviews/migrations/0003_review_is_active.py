from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0002_review_instant_booking'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True),
        ),
    ]