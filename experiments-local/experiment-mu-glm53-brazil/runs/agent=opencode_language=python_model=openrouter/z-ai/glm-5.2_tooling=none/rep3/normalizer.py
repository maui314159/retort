"""Brazilian Soccer MCP Server - team name normalization.

Context block
-------------
Purpose: Provide a single canonical key for Brazilian soccer team names
across six heterogeneous CSV datasets so that "Palmeiras-SP",
"Palmeiras", and "Sociedade Esportiva Palmeiras" all resolve to the
same entity.

Why: The spec (TASK.md "Data Quality Notes -> Team Name Variations")
calls out three naming conventions and demands consistent matching.
A normalized key is also required for head-to-head and standings
calculations to be correct.

What:
  - canonical_name(raw)  -> display name (accents preserved)
  - name_key(raw)        -> stable lowercase ASCII key for equality

Design:
  * Suffix stripping handles both "Team-SP" and "Team - RJ" forms.
  * Suffix stripping handles country tags in Libertadores ("Barcelona-EQU").
  * Common legal/entity suffixes ("Sport Club", "Futebol Clube",
    "Esporte Clube", "S/A", "(antigo ...)") are removed.
  * Accents folded via unicodedata NFKD for the key only; display name
    keeps accents for user-facing output.

Test: see tests/test_normalizer.py (BDD scenarios).
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Suffixes that appear as "-STATE" or "-COUNTRY" tokens. Brazilian state
# codes plus common South American country trigrams seen in Libertadores.
_STATE_OR_COUNTRY_SUFFIXES = {
    # Brazilian states
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
    "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
    # South American country tags seen in Libertadores dataset
    "URU","EQU","ARG","CHI","PAR","BOL","COL","PER","VEN","MEX","ECU",
}

# Phrases that may appear as a *leading* prefix of a club's full legal
# name (e.g. "Sociedade Esportiva Palmeiras"). Stripped from the start.
_LEGAL_PREFIXES = (
    "sociedade esportiva", "sport club", "esporte clube", "futebol clube",
    "club de regatas", "clube de regatas", "grêmio recreativo",
    "club atletico", "clube atletico", "atletico clube",
)

# Phrases that may appear as a *trailing* suffix (e.g. "Corinthians Sport
# Club", "Boavista S/A"). Stripped from the end.
_LEGAL_SUFFIXES = (
    "sport club", "esporte clube", "futebol clube", "club de regatas",
    "club atletico", "atletico clube", "s/a", "sa", "fc", "sc", "ac", "ec", "aa",
)

# A parenthetical such as "(antigo Esporte Clube Barreira)" that appears in
# the Copa do Brasil dataset.
_PAREN_RE = re.compile(r"\([^)]*\)")
# "Team - SP" or "Team-SP" or "Team -EQU"
_SUFFIX_RE = re.compile(r"\s*-\s*([A-Za-z]{2,3})\s*$")
# Multiple whitespace collapses
_WS_RE = re.compile(r"\s+")


@lru_cache(maxsize=4096)
def canonical_name(raw: str) -> str:
    """Return a human-readable canonical name (accents preserved)."""
    if not raw:
        return ""
    name = str(raw).strip()
    # Drop parentheticals
    name = _PAREN_RE.sub("", name).strip()
    # Strip trailing -UF / -COUNTRY
    name = _SUFFIX_RE.sub("", name).strip()
    name = _WS_RE.sub(" ", name)
    lowered = name.lower()
    # Strip leading legal prefixes (e.g. "Sociedade Esportiva ")
    changed = True
    while changed:
        changed = False
        for pre in _LEGAL_PREFIXES:
            if lowered.startswith(pre + " "):
                name = name[len(pre) + 1:].lstrip(" ,-")
                lowered = name.lower()
                changed = True
                break
    # Strip trailing legal suffixes (e.g. " Sport Club")
    changed = True
    while changed:
        changed = False
        for suf in _LEGAL_SUFFIXES:
            if lowered.endswith(" " + suf):
                name = name[: -(len(suf) + 1)].rstrip(" ,-")
                lowered = name.lower()
                changed = True
                break
            if lowered == suf:
                name = ""
                lowered = ""
                changed = True
                break
    return name.strip()


@lru_cache(maxsize=4096)
def name_key(raw: str) -> str:
    """Return a stable, accent-folded lowercase key for equality tests."""
    canon = canonical_name(raw)
    # Fold accents
    folded = unicodedata.normalize("NFKD", canon)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return folded.lower().strip()


def teams_match(a: str, b: str) -> bool:
    """True if two raw team strings refer to the same team."""
    return bool(a) and bool(b) and name_key(a) == name_key(b)


def display(raw: str) -> str:
    """Return the canonical display name for a raw team string."""
    return canonical_name(raw) or str(raw).strip()
