"""Synonym arbitration for guess matching.

Uses NLTK WordNet + omw-1.4 for Portuguese synonym matching.
Provides a three-tier decision: exact -> synonym -> fallback.
"""

import logging
from typing import Optional, Tuple

import nltk
from nltk.corpus import wordnet as wn

logger = logging.getLogger(__name__)


def ensure_nltk_corpora() -> None:
    """Ensure wordnet and omw-1.4 corpora are available.

    Downloads missing corpora. Safe to call at server startup.
    Must use .zip path — NLTK stores corpora as zip archives.
    """
    for corpus_name, zip_path in [
        ('wordnet', 'corpora/wordnet.zip'),
        ('omw-1.4', 'corpora/omw-1.4.zip'),
    ]:
        try:
            nltk.data.find(zip_path)
        except LookupError:
            logger.info("Downloading NLTK corpus: %s", corpus_name)
            nltk.download(corpus_name, quiet=True)


def _max_wup_similarity(synsets_a, synsets_b) -> float:
    """Return max Wu-Palmer similarity over all cross-product pairs."""
    max_sim = 0.0
    for s1 in synsets_a:
        for s2 in synsets_b:
            sim = s1.wup_similarity(s2)
            if sim is not None and sim > max_sim:
                max_sim = sim
    return max_sim


def arbitrate(
    guess: str,
    target: str,
    threshold: float,
) -> Tuple[bool, Optional[str], str]:
    """Arbitrate a player's guess against the target object word.

    Three-tier decision (GUESS-03):
    (a) Case-insensitive exact match
    (b) Wu-Palmer synonym match via NLTK WordNet + omw-1.4 (lang='por')
    (c) Fallback exact-match when WordNet returns no synsets for either word

    Note: Wu-Palmer at threshold 0.7 intentionally accepts near-synonyms
    (e.g., banana ~ apple = 0.82; fruit words share 'edible_fruit' hypernym).
    This is expected game behavior per D-01. Tune via config.WU_PALMER_THRESHOLD.

    Args:
        guess: Player's cleaned guessed word (stripped, max 50 chars).
        target: Canonical object word from image_assignments.
        threshold: Wu-Palmer similarity threshold (config.WU_PALMER_THRESHOLD).

    Returns:
        (is_correct, matched_word, match_type) where:
        - is_correct: True if guess accepted by any method
        - matched_word: canonical target word when correct, None when incorrect (D-05/D-06)
        - match_type: 'exact' | 'synonym' | 'fallback' — never None (D-06)
    """
    guess_clean = guess.strip()
    target_clean = target.strip()

    # (a) Exact match — GUESS-03a
    if guess_clean.lower() == target_clean.lower():
        return True, target, 'exact'

    # (b) WordNet synonym match — GUESS-03b
    guess_synsets = wn.synsets(guess_clean, lang='por')
    target_synsets = wn.synsets(target_clean, lang='por')

    if guess_synsets and target_synsets:
        sim = _max_wup_similarity(guess_synsets, target_synsets)
        is_correct = sim >= threshold
        return is_correct, (target if is_correct else None), 'synonym'

    # (c) Fallback exact-match when WordNet returns no synsets — GUESS-03c
    is_correct = guess_clean.lower() == target_clean.lower()
    return is_correct, (target if is_correct else None), 'fallback'
