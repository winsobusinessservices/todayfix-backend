
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0003_backfill_service_type_and_unit"),
    ]

    operations = [
        TrigramExtension(),
    ]