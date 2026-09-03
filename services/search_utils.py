"""
WordNet-based synonym expansion for service search.

Free, offline, no API calls. Used as an ADDITIVE layer on top of
full-text + trigram search (see ServiceSearchAPIView) — if this
fails to find anything or the corpus isn't downloaded yet, search
still works normally without it.
"""

import logging

from django.db.models import Q

logger = logging.getLogger(__name__)

# Only the top N most common senses of a word are used, and only
# single-word synonyms are kept. Ambiguous short words (e.g. "fit")
# can still surface noisy synonyms from unrelated meanings — this
# is a known WordNet limitation, not a bug. Zero-result search
# tracking (a separate feature) is meant to catch what this misses.
MAX_SENSES_PER_WORD = 2
MAX_SYNONYMS_PER_WORD = 5

_wordnet = None
_wordnet_load_attempted = False


def _get_wordnet():
    """
    Lazily import and return nltk.corpus.wordnet.
    Returns None if nltk isn't installed or the corpus data
    hasn't been downloaded yet — callers must handle that
    gracefully rather than crashing search.
    """
    global _wordnet, _wordnet_load_attempted

    if _wordnet is not None:
        return _wordnet

    if _wordnet_load_attempted:
        return None

    _wordnet_load_attempted = True

    try:
        from nltk.corpus import wordnet

        # Touch the corpus once so a missing download fails here,
        # not later mid-request.
        wordnet.synsets("test")
        _wordnet = wordnet
        return _wordnet

    except LookupError:
        logger.warning(
            "NLTK WordNet corpus not downloaded. Run: "
            "python manage.py download_search_corpus"
        )
        return None

    except ImportError:
        logger.warning(
            "nltk is not installed. Synonym expansion disabled."
        )
        return None


def get_synonyms(word):
    """
    Return a small set of likely single-word synonyms for `word`,
    using only the most common senses. Returns an empty set on
    any failure (missing corpus, single-character words, etc.)
    so search always degrades gracefully.
    """
    word = (word or "").strip().lower()

    if len(word) < 3:
        return set()

    wordnet = _get_wordnet()
    if wordnet is None:
        return set()

    synonyms = set()

    try:
        synsets = wordnet.synsets(word)[:MAX_SENSES_PER_WORD]

        for synset in synsets:
            for lemma in synset.lemmas():
                name = lemma.name().replace("_", " ").lower()

                # Skip multi-word phrases and the word itself.
                if " " in name or name == word:
                    continue

                synonyms.add(name)

                if len(synonyms) >= MAX_SYNONYMS_PER_WORD:
                    return synonyms

    except Exception:
        # Never let synonym lookup break search.
        logger.exception(
            "Synonym lookup failed for word: %s", word
        )
        return set()

    return synonyms


def get_manual_synonyms(word):
    """
    Look up admin-added SearchSynonym pairs for `word`, matching
    in both directions. Returns an empty set if none found.
    """
    from services.models import SearchSynonym

    word = (word or "").strip().lower()
    if not word:
        return set()

    synonyms = set()

    pairs = SearchSynonym.objects.filter(
        Q(term=word) | Q(synonym=word)
    ).values_list("term", "synonym")

    for term, synonym in pairs:
        if term != word:
            synonyms.add(term)
        if synonym != word:
            synonyms.add(synonym)

    return synonyms


def expand_search_words(words):
    """
    Given a list of search words, return the original words plus
    their WordNet synonyms and any admin-added manual synonyms,
    deduplicated.
    """
    expanded = set(words)

    for word in words:
        expanded |= get_synonyms(word)
        expanded |= get_manual_synonyms(word)

    return expanded