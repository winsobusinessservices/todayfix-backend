from django.core.management.base import BaseCommand
from django.utils.text import slugify

from services.models import ServiceType


TYPES = [
    "Sell/Buy",
    "Maintenance",
    "Time Based",
    "Rental",
    "Documentation",
    "Transport",
    "Training/Education",
    "Healthcare",
]


class Command(BaseCommand):
    help = "Seed the fixed set of service types."

    def handle(self, *args, **options):
        for name in TYPES:
            obj, created = ServiceType.objects.get_or_create(
                name=name,
                defaults={"slug": slugify(name)},
            )
            self.stdout.write(
                ("Created " if created else "Exists   ")
                + obj.name
            )