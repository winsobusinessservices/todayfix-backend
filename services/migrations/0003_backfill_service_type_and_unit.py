from django.db import migrations, models
import django.db.models.deletion


def backfill_existing_services(apps, schema_editor):
    ServiceType = apps.get_model("services", "ServiceType")
    Unit = apps.get_model("services", "Unit")
    Service = apps.get_model("services", "Service")

    legacy_service_type, _ = ServiceType.objects.get_or_create(
        name="Legacy",
        defaults={
            "slug": "legacy",
            "is_active": True,
        },
    )

    legacy_unit, _ = Unit.objects.get_or_create(
        service_type=legacy_service_type,
        name="Per Service",
        defaults={
            "is_active": True,
        },
    )

    Service.objects.filter(
        service_type__isnull=True
    ).update(
        service_type_id=legacy_service_type.id
    )

    Service.objects.filter(
        unit__isnull=True
    ).update(
        unit_id=legacy_unit.id
    )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        (
            "services",
            "0002_servicetype_service_service_type_unit_service_unit_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            backfill_existing_services,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="service",
            name="service_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="services",
                to="services.servicetype",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="services",
                to="services.unit",
            ),
        ),
    ]