"""Unit tests for arbitration module (GUESS-03 coverage)."""

import pytest

try:
    from server.arbitration import arbitrate, ensure_nltk_corpora
except ImportError:
    pytest.skip("server.arbitration not yet implemented", allow_module_level=True)

# Ensure corpora available before any test runs (once per pytest session)
ensure_nltk_corpora()

THRESHOLD = 0.7


def test_exact_match():
    """GUESS-03a: exact case-sensitive match accepted"""
    ok, word, typ = arbitrate('maçã', 'maçã', THRESHOLD)
    assert ok is True, f"Expected ok=True, got {ok}"
    assert word == 'maçã', f"Expected matched_word='maçã', got {word}"
    assert typ == 'exact', f"Expected match_type='exact', got {typ}"


def test_exact_match_case_insensitive():
    """GUESS-03a: exact match is case-insensitive"""
    ok, word, typ = arbitrate('MAÇÃ', 'maçã', THRESHOLD)
    assert ok is True, f"Expected ok=True for case-insensitive match, got {ok}"
    assert typ == 'exact', f"Expected match_type='exact', got {typ}"


def test_synonym_pt_guess_pt_target():
    """GUESS-03b: Portuguese guess vs Portuguese target via omw-1.4 synsets.

    xícara (cup) vs copo (glass/goblet) — verified wup_similarity=0.875 via live test.
    Both words are containers for liquids, share 'container' hypernym in WordNet.
    """
    ok, word, typ = arbitrate('xícara', 'copo', THRESHOLD)
    assert ok is True, f"Expected xícara~copo to be accepted (wup=0.875 > {THRESHOLD}), got ok={ok}"
    assert word == 'copo', f"Expected matched_word='copo' (canonical target), got {word}"
    assert typ == 'synonym', f"Expected match_type='synonym', got {typ}"


def test_synonym_wrong_guess():
    """GUESS-03b: non-synonym guess rejected, matched_word is None"""
    ok, word, typ = arbitrate('cachorro', 'maçã', THRESHOLD)
    assert ok is False, f"Expected cachorro~maçã to be rejected (wup=0.545 < {THRESHOLD}), got ok={ok}"
    assert word is None, f"Expected matched_word=None for incorrect guess (D-05), got {word}"


def test_fallback_when_no_synsets():
    """GUESS-03c: unknown word triggers fallback path, does not crash.

    Uses two distinct unknown words so that exact-match step (a) does not fire,
    and both have no synsets so synonym step (b) is skipped — reaching fallback (c).
    """
    ok, word, typ = arbitrate('xyzzy', 'abcde', THRESHOLD)
    assert ok is False, f"Expected ok=False for different unknown words via fallback, got {ok}"
    assert word is None, f"Expected matched_word=None for non-match, got {word}"
    assert typ == 'fallback', f"Expected match_type='fallback', got {typ}"


def test_match_type_on_incorrect_guess():
    """D-06: match_type is set even on incorrect guesses"""
    ok, word, typ = arbitrate('cachorro', 'maçã', THRESHOLD)
    assert ok is False, f"Expected ok=False for wrong guess, got {ok}"
    assert word is None, f"Expected matched_word=None for incorrect guess (D-06), got {word}"
    assert typ in ('exact', 'synonym', 'fallback'), (
        f"Expected match_type in known values, got {typ}"
    )


def test_matched_word_is_target_not_guess():
    """D-05: matched_word is canonical target word, not the guess"""
    ok, word, typ = arbitrate('maçã', 'maçã', THRESHOLD)
    assert word == 'maçã', f"Expected matched_word='maçã' (target), got {word}"


def test_wup_threshold_boundary():
    """GUESS-03b: threshold gates synonym acceptance correctly.

    xícara vs copo: wup_similarity=0.875 (above 0.7) -> accepted.
    cachorro vs maçã: wup_similarity=0.545 (below 0.7) -> rejected.
    Demonstrates that the threshold parameter controls the boundary.
    """
    # Above threshold: xícara (cup) vs copo (glass/goblet) — wup=0.875, verified live
    ok_above, word_above, typ_above = arbitrate('xícara', 'copo', 0.7)
    assert ok_above is True, f"Expected xícara~copo accepted above 0.7 (wup=0.875), got ok={ok_above}"
    assert typ_above == 'synonym', f"Expected match_type='synonym', got {typ_above}"

    # Below threshold: cachorro (dog) vs maçã (apple) — wup=0.545, verified live
    ok_below, word_below, typ_below = arbitrate('cachorro', 'maçã', 0.7)
    assert ok_below is False, f"Expected cachorro~maçã rejected below 0.7 (wup=0.545), got ok={ok_below}"
    assert word_below is None, f"Expected matched_word=None for rejected guess, got {word_below}"
