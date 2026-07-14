"""
================================================================================
brazil_soccer_mcp.normalize
================================================================================
Context:
    The datasets use inconsistent conventions for team names, dates and
    competition labels. This module centralizes normalization so the same
    real-world entity from different files maps to one canonical key.

Responsibilities:
    - normalize_team(name)        -> canonical lookup key (accent-folded,
                                     lowercase, state/country suffix removed)
    - display_team(name)          -> cleaned human-readable team name
    - normalize_date(value)       -> datetime.date | None across ISO / BR /
                                     datetime formats
    - normalize_competition(name) -> canonical competition label

Design note:
    normalize_team is deliberately conservative: it folds accents, lowercases
    and drops trailing state/country suffixes and parenthetical asides, but
    does NOT strip interior club-type words ("Sport", "Club", "FC"). Stripping
    those creates collisions ("Sport-PE" -> "sport" vs. "Sport Club do Recife"
    -> "recife"). Fuzzy / partial matching for user queries is handled in the
    graph layer via substring containment, which is robust without guessing.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Country code parentheses, e.g. "Nacional (URU)".
_COUNTRY_PARENS = re.compile(r"\s*\([A-Z]{2,4}\)\s*$")
# Any parenthetical aside, e.g. "Boavista Sport Club (antigo ...)".
_PAREN_ASIDE = re.compile(r"\s*\([^)]*\)")
# Trailing state/country abbreviation: " - RJ", "-RJ", " RJ", "-EQU".
_STATE_SUFFIX = re.compile(r"[\s-]+[A-Z]{2,4}$")

_COMPETITION_ALIASES = {
    "serie a": "Brasileirao Serie A",
    "brasileirao": "Brasileirao Serie A",
    "brasileirao serie a": "Brasileirao Serie A",
    "campeonato brasileiro": "Brasileirao Serie A",
    "serie b": "Serie B",
    "serie c": "Serie C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "copa libertadores": "Copa Libertadores",
    "libertadores": "Copa Libertadores",
}

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
)


def strip_accents(text: str) -> str:
    """Fold accented characters to ASCII (São -> Sao, Grêmio -> Gremio)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def display_team(name) -> str:
    """Return a cleaned, human-readable team name (suffixes/asides removed)."""
    if name is None:
        return ""
    cleaned = str(name).strip().strip('"').strip()
    cleaned = _PAREN_ASIDE.sub("", cleaned)
    cleaned = _COUNTRY_PARENS.sub("", cleaned)
    cleaned = _STATE_SUFFIX.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned or str(name).strip()


def parse_team(name) -> tuple[str, Optional[str]]:
    """Split a raw team name into (base_key, state/country code or None).

    base_key is accent-folded, lowercase, punctuation-stripped, with any
    trailing 2-4 letter state/country suffix removed. The removed suffix is
    returned separately (uppercase) so the graph can decide, corpus-wide,
    whether it is needed to disambiguate same-base clubs.
    """
    if name is None:
        return "", None
    cleaned = str(name).strip().strip('"').strip()
    uf = None
    country = _COUNTRY_PARENS.search(cleaned)
    if country:
        uf = country.group(0).strip().strip("()")
        cleaned = _COUNTRY_PARENS.sub("", cleaned)
    cleaned = _PAREN_ASIDE.sub("", cleaned)
    if uf is None:
        m = _STATE_SUFFIX.search(cleaned)
        if m:
            uf = m.group(0).strip(" -")
            cleaned = _STATE_SUFFIX.sub("", cleaned)
    base = strip_accents(cleaned).lower()
    base = re.sub(r"[^a-z0-9 ]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base, (uf.upper() if uf else None)


def normalize_team(name) -> str:
    """Canonical accent-folded base key for a team (state suffix removed).

    Suitable for player clubs/nationalities and as the base component of the
    corpus-aware canonical key built in the graph layer.
    """
    base, _ = parse_team(name)
    return base


def normalize_competition(name) -> str:
    """Map a raw competition/tournament string to a canonical label."""
    if not name:
        return "Unknown"
    key = strip_accents(str(name)).strip().lower()
    return _COMPETITION_ALIASES.get(key, str(name).strip())


def normalize_date(value) -> Optional[date]:
    """Parse ISO / Brazilian / datetime strings into a date. None if unparseable."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip().strip('"')
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
