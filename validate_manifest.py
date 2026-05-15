"""Standalone manifest validation script.

Run before deployment to verify all image words have WordNet (omw-1.4) coverage.
Prints a human-readable report to stdout. Does NOT modify manifest.json.

Usage: python validate_manifest.py
Exit code: 0 if all words valid, 1 if any are excluded (CI-friendly).
"""
import json
import os
import sys

from nltk.corpus import wordnet as wn

# server/ must be importable to use ensure_nltk_corpora
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server.arbitration import ensure_nltk_corpora

# Ensure corpora present before any wordnet usage
ensure_nltk_corpora()

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'server', 'images', 'manifest.json'
)

with open(MANIFEST_PATH, encoding='utf-8') as f:
    manifest = json.load(f)

valid = []
excluded = []

for filename, word in manifest.items():
    synsets = wn.synsets(word, lang='por')
    if synsets:
        valid.append((filename, word, len(synsets)))
    else:
        excluded.append((filename, word))

print(f"Manifest validation: {len(valid)} valid, {len(excluded)} excluded")
for filename, word, count in valid:
    print(f"  OK  {filename}: '{word}' ({count} synsets)")
for filename, word in excluded:
    print(f"  EXCLUDED  {filename}: '{word}' — no synsets found")

if excluded:
    sys.exit(1)
