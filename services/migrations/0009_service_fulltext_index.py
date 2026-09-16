from django.db import migrations


def add_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor == "mysql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE services_service "
                "ADD FULLTEXT INDEX service_name_desc_fulltext "
                "(name, description)"
            )


def drop_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor == "mysql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE services_service "
                "DROP INDEX service_name_desc_fulltext"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0008_service_rank"),
    ]

    operations = [
        migrations.RunPython(
            add_fulltext_index,
            drop_fulltext_index,
        ),
    ]