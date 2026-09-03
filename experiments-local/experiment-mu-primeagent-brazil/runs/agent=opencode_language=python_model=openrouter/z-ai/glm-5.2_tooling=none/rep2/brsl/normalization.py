"""Team-name normalization utilities for the Brazilian Soccer MCP server.

The bundled datasets use many different conventions for the same club:

* with a state suffix        -> ``"Palmeiras-SP"``, ``"América - MG"``
* with a country code        -> ``"Nacional (URU)"``, ``"Barcelona-EQU"``
* without diacritics         -> ``"Sao Paulo"`` (BR-Football-Dataset)
* with diacritics            -> ``"São Paulo"`` (FIFA, novo campeonato)
* long descriptive names     -> ``"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"``

This module exposes :func:`normalize_team` which returns a :class:`TeamName`
record holding a cleaned *display* name, a canonical ASCII *key* used for
matching across datasets, and the parsed state / country suffixes.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Two-letter abbreviations of the 27 Brazilian federative units.
BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Club-name suffix words that may be appended after the distinctive name.
# They are stripped only when *trailing* (and another token remains), so the
# distinctive leading token (e.g. the club "Sport") is never lost.
_CLUB_SUFFIX_TOKENS = {
    "fc", "sc", "ec", "ac", "aa", "sa", "cf", "scp",
    "futebol", "clube", "club", "esporte", "sporting",
}

# Trailing " - STATE" or "-STATE" or "-COUNTRY" patterns.
_TRAILING_DASH_STATE = re.compile(r"\s*-\s*([A-Z]{2})\s*$")
_TRAILING_DASH_COUNTRY = re.compile(r"\s*-\s*([A-Z]{3})\s*$")
_TRAILING_PAREN_COUNTRY = re.compile(r"\s*\(([A-Z]{2,4})\)\s*$")
_TRAILING_PARENS = re.compile(r"\s*\(.*?\)\s*$")


@dataclass(frozen=True)
class TeamName:
    """A normalized team name."""

    display: str
    key: str
    state: str | None
    country: str | None

    def __str__(self) -> str:
        return self.display


def _strip_accents(value: str) -> str:
    """Return ``value`` with diacritical marks removed (NFD decomposition)."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _collapse(value: str) -> str:
    """Lowercase, strip punctuation noise and collapse whitespace.

    Only *trailing* club-suffix tokens (``fc``, ``sc``, ``club`` ...) are
    removed, so a distinctive leading word such as the club ``"Sport"`` is
    preserved for matching.
    """
    value = _strip_accents(value).strip().lower()
    value = re.sub(r"[^\w\s]", " ", value)  # punctuation -> space
    tokens = [t for t in value.split() if t]
    while len(tokens) > 1 and tokens[-1] in _CLUB_SUFFIX_TOKENS:
        tokens.pop()
    return " ".join(tokens).strip()


def normalize_team(name: str) -> TeamName:
    """Normalize a raw team name from any of the source datasets.

    Returns a :class:`TeamName` with:

    * ``display``  - cleaned human readable name (accents preserved, state /
      country suffixes removed);
    * ``key``      - canonical ASCII key used for cross-dataset matching;
    * ``state``    - Brazilian state abbreviation if one was detected;
    * ``country``  - 2-4 letter country code if one was detected.
    """
    if name is None:
        return TeamName("", "", None, None)
    raw = str(name).strip()

    # 0) strip a leading "FC " / "SC " / "EC " style prefix (FIFA exports).
    m = re.match(r"^([A-Za-z]{2})\s+", raw)
    if m and m.group(1).lower() in _CLUB_SUFFIX_TOKENS:
        raw = raw[m.end():]

    state = None
    country = None

    # 1) trailing " - STATE" (2-letter Brazilian state abbreviation).
    m = _TRAILING_DASH_STATE.search(raw)
    if m and m.group(1) in BRAZILIAN_STATES:
        state = m.group(1)
        raw = raw[: m.start()].rstrip()

    # 2) trailing " - COUNTRY" (3-letter country code, e.g. "Barcelona-EQU").
    if state is None:
        m = _TRAILING_DASH_COUNTRY.search(raw)
        if m:
            country = m.group(1)
            raw = raw[: m.start()].rstrip()

    # 3) trailing "(COUNTRY)" parenthetical, e.g. "Nacional (URU)".
    m = _TRAILING_PAREN_COUNTRY.search(raw)
    if m and country is None:
        country = m.group(1)
        raw = raw[: m.start()].rstrip()

    # 4) drop any remaining descriptive parentheticals for the display form
    #    but keep a copy for the key (collapsing handles it).
    display = raw.strip()
    if _TRAILING_PARENS.search(display):
        display = _TRAILING_PARENS.sub("", display).strip()

    key = _collapse(raw)
    return TeamName(display=display or str(name).strip(), key=key,
                   state=state, country=country)


def team_key(name: str) -> str:
    """Return only the canonical ASCII key for ``name``."""
    return normalize_team(name).key


def team_matches(query: str, candidate: str) -> bool:
    """Return ``True`` when ``query`` refers to ``candidate``.

    A query matches when the canonical keys are equal, or when the query key
    is a non-trivial substring of the candidate key (or vice versa).
    """
    q = _collapse(query)
    c = _collapse(candidate)
    if not q or not c:
        return False
    if q == c:
        return True
    # Require the shorter token to be at least 3 chars to avoid spurious
    # matches such as "SP" matching "Sport".
    short, long = (q, c) if len(q) <= len(c) else (c, q)
    if len(short) >= 3 and (short in long.split() or short in long):
        return True
    return False
