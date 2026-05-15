"""Unit tests for arbitration module (GUESS-03 coverage)."""

import pytest

try:
    from server.arbitration import arbitrate, ensure_nltk_corpora
except ImportError:
    pytest.skip("server.arbitration not yet implemented", allow_module_level=True)

THRESHOLD = 0.7


def test_exact_match():
    """GUESS-03a: exact case-sensitive match accepted"""
    pytest.skip("not implemented")


def test_exact_match_case_insensitive():
    """GUESS-03a: exact match is case-insensitive"""
    pytest.skip("not implemented")


def test_synonym_pt_guess_pt_target():
    """GUESS-03b: Portuguese guess vs Portuguese target via omw-1.4 synsets"""
    pytest.skip("not implemented")


def test_synonym_wrong_guess():
    """GUESS-03b: non-synonym guess rejected, matched_word is None"""
    pytest.skip("not implemented")


def test_fallback_when_no_synsets():
    """GUESS-03c: unknown word triggers fallback path, does not crash"""
    pytest.skip("not implemented")


def test_match_type_on_incorrect_guess():
    """D-06: match_type is set even on incorrect guesses"""
    pytest.skip("not implemented")


def test_matched_word_is_target_not_guess():
    """D-05: matched_word is canonical target word, not the guess"""
    pytest.skip("not implemented")


def test_wup_threshold_boundary():
    """GUESS-03b: score exactly at threshold is accepted; score below is rejected"""
    pytest.skip("not implemented")
