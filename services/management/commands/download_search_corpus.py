from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    One-time setup: downloads the NLTK WordNet corpus used for
    synonym expansion in service search.

    Run this once per environment (local machine, staging,
    production server) after installing nltk:

        python manage.py download_search_corpus

    Requires internet access at the time it's run (downloads
    ~10-15 MB). Search itself works fine without this — it just
    degrades to full-text + trigram search only until this is run.
    """

    help = (
        "Downloads the NLTK WordNet corpus needed for "
        "synonym-based service search. Run once per environment."
    )

    def handle(self, *args, **options):
        import nltk

        self.stdout.write("Downloading WordNet corpus...")
        nltk.download("wordnet")

        self.stdout.write("Downloading Open Multilingual Wordnet...")
        nltk.download("omw-1.4")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. Service search synonym expansion is now active."
            )
        )