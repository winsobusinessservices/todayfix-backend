import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0015_alter_businessapplication_location_businessportfolio_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessportfolio',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True),
        ),
        migrations.CreateModel(
            name='DeletedBusinessIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_business_identity_uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('original_business_identity_uuid', models.UUIDField(db_index=True)),
                ('original_business_application_id', models.PositiveBigIntegerField(db_index=True)),
                ('business_profile_uuid', models.UUIDField(blank=True, db_index=True, null=True)),
                ('owner_user_uuid', models.UUIDField(db_index=True)),
                ('business_name', models.CharField(blank=True, default='', max_length=200)),
                ('business_type', models.CharField(blank=True, default='', max_length=20)),
                ('identity_data', models.JSONField(blank=True, default=dict)),
                ('deleted_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-deleted_at'],
            },
        ),
    ]