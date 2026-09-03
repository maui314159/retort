"""
Context Block
=============

Module: brazilian_soccer_mcp.normalizer
Purpose: Normalise team names and dates across heterogeneous CSV
         datasets so that the same team is always matched regardless
         of the naming convention used by a particular source file.

Key functions
-------------
* ``team_match_key(name)``  - produce a canonical, accent-free,
  lower-case, state-suffix-stripped key suitable for broad matching
  across data sources.
* ``team_state(name)``     - extract the 2-letter state code from a
  team name (suffix or trailing word), using alias lookups.
* ``team_canonical(name)`` - return ``(base_name, state)`` tuple.
* ``display_name(name)``   - human-readable name (keeps accents,
  drops state suffix and parenthetical notes).
* ``parse_date(value)``   - parse ISO / Brazilian date strings.
* ``format_date(dt)``      - format a datetime as ISO.

Design notes
------------
The six datasets use several team-name conventions:

1. "Palmeiras-SP"            (Brasileirao - dash + state suffix)
2. "Flamengo"                (Historical  - no suffix)
3. "ABC - RN"                (Copa do Brasil - spaced suffix)
4. "Sao Paulo"               (BR-Football  - no accents, no state)
5. "Atletico Mineiro"        (FIFA / BR-Football - full name)
6. "America FC Natal"        (BR-Football - city name appended)

``team_match_key`` collapses all of these into a single canonical
base-name by removing parenthetical notes, stripping diacritics,
lower-casing, applying a manual alias map, stripping a trailing
state *word* or *suffix*, and removing trailing club designators.

The state is preserved separately via ``team_state`` so that
precise disambiguation is possible when several clubs share a base
name (e.g. the three "Atletico-*" clubs).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Brazilian state abbreviations
# ---------------------------------------------------------------------------
BR_STATES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

# Foreign / Libertadores suffixes that appear in the data
FOREIGN_SUFFIXES = {
    "EQU", "URU", "ARG", "CHI", "PAR", "COL", "BOL", "PER",
    "VEN", "ECU", "MEX", "USA", "CAN",
}

# Words that are pure club designators, removed from the *end* of the
# name only (to avoid mangling names like "Sport Club do Recife").
_CLUB_DESIGNATORS = {"fc", "ec", "sc", "ac", "acbc", "mr", "cb", "club", "clube"}

# ---------------------------------------------------------------------------
# Alias map: full / alternate team name  ->  "base-UF" form.
#
# Applied *after* accent stripping and lower-casing but *before* state
# stripping, so that the state is recovered from the alias value.
# ---------------------------------------------------------------------------
TEAM_ALIASES: dict[str, str] = {
    # Atletico variants (MG, PR, GO, AC, BA)
    "atletico mineiro": "atletico-mg",
    "athletico mineiro": "atletico-mg",
    "atletico paranaense": "atletico-pr",
    "athletico paranaense": "atletico-pr",
    "atletico goianiense": "atletico-go",
    "athletico goianiense": "atletico-go",
    "atletico acreano": "atletico-ac",
    "atletico alagoinhas": "atletico-ba",
    "athletico": "atletico-pr",  # bare "Athletico" in Libertadores

    # America variants
    "america fc natal": "america-rn",
    "america natal": "america-rn",
    "america fc minas gerais": "america-mg",
    "america minas gerais": "america-mg",
    "america fc": "america-mg",

    # Sport / Ceara full names
    "sport club do recife": "sport-pe",
    "sport recife": "sport-pe",
    "ceara sporting club": "ceara-ce",

    # Goias
    "goias ec": "goias-go",
    "goias goiania": "goias-go",

    # Cuiaba
    "cuiaba esporte clube": "cuiaba-mt",
    "cuiaba mt": "cuiaba-mt",

    # Santos
    "santos fc": "santos-sp",
    "santos laguna": "santos laguna",  # Mexican club, keep distinct

    # International clubs that share names with Brazilian clubs
    "barcelona sc": "barcelona sc",  # Ecuadorian, keep distinct
}

# ---------------------------------------------------------------------------
# Base-name fixes applied *after* state stripping to reconcile spelling
# variants and name-length differences across datasets.
# ---------------------------------------------------------------------------
_BASE_NAME_FIXES: dict[str, str] = {
    "athletico": "atletico",       # Historical uses "Athletico", Brasileirao "Atletico"
    "vasco da gama": "vasco",     # Brasileirao "Vasco da Gama", Historical "Vasco"
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _strip_accents(text: str) -> str:
    """Return *text* with all combining diacritics removed."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _strip_state_suffix(name: str) -> Tuple[str, Optional[str]]:
    """Remove a trailing ``-UF`` suffix (case-insensitive).

    Returns ``(name_without_suffix, state_or_None)``.
    Handles "Palmeiras-SP", "palmeiras-sp", "America - MG".
    """
    m = re.search(r"\s*-\s*([A-Za-z]{2,3})\s*$", name)
    if m:
        suffix = m.group(1).upper()
        if suffix in BR_STATES:
            return name[: m.start()].strip(), suffix
        if suffix in FOREIGN_SUFFIXES:
            return name[: m.start()].strip(), suffix
    return name.strip(), None


def _strip_trailing_state_word(name: str) -> Tuple[str, Optional[str]]:
    """Remove a trailing 2-letter state *word* (e.g. "america mg").

    Returns ``(name_without_word, state_or_None)``.  Case-insensitive.
    """
    m = re.search(r"\s+([A-Za-z]{2})\s*$", name)
    if m and m.group(1).upper() in BR_STATES:
        return name[: m.start()].strip(), m.group(1).upper()
    return name.strip(), None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def team_match_key(name: str) -> str:
    """Canonical base-name key for broad team matching.

    The key is the team name with state suffixes/words, accents,
    parenthetical notes and trailing club designators removed,
    lower-cased, and collapsed.  Aliases are applied first so that
    full names like "Atletico Mineiro" resolve to the same key as
    "Atletico-MG".

    Examples
    --------
    >>> team_match_key("Palmeiras-SP")
    'palmeiras'
    >>> team_match_key("Sao Paulo")
    'sao paulo'
    >>> team_match_key("Atletico Mineiro")
    'atletico'
    >>> team_match_key("America MG")
    'america'
    >>> team_match_key("Flamengo")
    'flamengo'
    """
    if not name or not isinstance(name, str):
        return ""

    s = name.strip()

    # Remove parenthetical notes
    s = re.sub(r"\([^)]*\)", " ", s)

    # Normalise unicode and remove accents
    s = _strip_accents(s)

    # Lowercase
    s = s.lower().strip()

    # Apply alias map (check full string first, then progressively
    # shorter prefixes for robustness)
    if s in TEAM_ALIASES:
        s = TEAM_ALIASES[s]
    else:
        # Try stripping trailing club designators then re-check alias
        words = s.split()
        if words and words[-1] in _CLUB_DESIGNATORS:
            candidate = " ".join(words[:-1])
            if candidate in TEAM_ALIASES:
                s = TEAM_ALIASES[candidate]

    # Strip state suffix first ("palmeiras-sp" -> "palmeiras", or
    # "boavista sport club - rj" -> "boavista sport club")
    s, state_suffix = _strip_state_suffix(s)

    # Strip trailing state word ("america mg" -> "america")
    s, state_word = _strip_trailing_state_word(s)

    # Remove trailing club designators
    words = s.split()
    while words and words[-1] in _CLUB_DESIGNATORS:
        words.pop()
    s = " ".join(words).strip()

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # Apply base-name fixes (spelling variants, name length)
    s = _BASE_NAME_FIXES.get(s, s)

    return s


def team_state(name: str) -> Optional[str]:
    """Extract the 2-letter Brazilian state code from a team name.

    Handles suffixes ("Palmeiras-SP"), trailing state words
    ("America MG"), and alias-mapped full names ("Atletico Mineiro"
    -> MG).  Returns ``None`` when no state can be determined.
    """
    if not name or not isinstance(name, str):
        return None

    s = name.strip()
    # Remove parenthetical notes
    s = re.sub(r"\([^)]*\)", " ", s)
    s = _strip_accents(s).lower().strip()

    # Check alias map (may introduce a state suffix)
    if s in TEAM_ALIASES:
        s = TEAM_ALIASES[s]
    else:
        words = s.split()
        if words and words[-1] in _CLUB_DESIGNATORS:
            candidate = " ".join(words[:-1])
            if candidate in TEAM_ALIASES:
                s = TEAM_ALIASES[candidate]

    # Try state suffix first (handles "- rj" style)
    _, state = _strip_state_suffix(s)
    if state:
        return state

    # Try trailing state word (handles "america mg" style)
    _, state = _strip_trailing_state_word(s)
    if state:
        return state

    return None


def team_canonical(name: str) -> Tuple[str, Optional[str]]:
    """Return ``(base_name, state)`` for a team name.

    ``base_name`` is the same value returned by ``team_match_key``.
    """
    return team_match_key(name), team_state(name)


def display_name(name: str) -> str:
    """Produce a tidy, human-readable team name.

    Keeps the original spelling (including accents) but removes the
    state suffix and any parenthetical notes.
    """
    if not name or not isinstance(name, str):
        return ""
    s = name.strip()
    # Remove parenthetical notes
    s = re.sub(r"\([^)]*\)", "", s).strip()
    # Strip trailing state suffix
    m = re.search(r"\s*-\s*([A-Za-z]{2,3})\s*$", s)
    if m and (m.group(1).upper() in BR_STATES or m.group(1).upper() in FOREIGN_SUFFIXES):
        s = s[: m.start()].strip()
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_state(name: str) -> Optional[str]:
    """Alias for ``team_state`` kept for backward compatibility."""
    return team_state(name)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_date(value) -> Optional[datetime]:
    """Parse a date string in any of the known formats.

    Accepts ISO (2023-09-24), ISO-with-time (2012-05-19 18:30:00) and
    Brazilian (29/03/2003) formats.  Returns ``None`` when the value
    cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s or s.lower() in ("nan", "nat", "none", ""):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def format_date(dt: Optional[datetime]) -> Optional[str]:
    """Format a datetime as ``YYYY-MM-DD`` (ISO)."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")
