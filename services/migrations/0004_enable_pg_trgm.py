from django.db import migrations


def enable_pg_trgm(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def disable_pg_trgm(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("DROP EXTENSION IF EXISTS pg_trgm")


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0003_backfill_service_type_and_unit"),
    ]

    operations = [
        migrations.RunPython(
            enable_pg_trgm,
            disable_pg_trgm,
        ),
    ]