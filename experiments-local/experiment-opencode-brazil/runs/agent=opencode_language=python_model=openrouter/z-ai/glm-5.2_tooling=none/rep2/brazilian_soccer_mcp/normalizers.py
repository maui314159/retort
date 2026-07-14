# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# Normalizers for team names and dates. Datasets use inconsistent conventions:
#   - With state suffix:   "Palmeiras-SP", "América - MG", "Flamengo-RJ"
#   - Full official names: "Sport Club Corinthians Paulista"
#   - Date formats:        "2023-09-24", "2012-05-19 18:30:00", "29/03/2003"
# This module produces a canonical display name and a stable matching key so
# that queries like "Flamengo" match "Flamengo-RJ" across all files.
# ----------------------------------------------------------------------------
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Optional

# Brazilian state abbreviations used to strip the "-SP" / " - MG" suffixes.
BR_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Trailing state suffix patterns. Match either "-XX" or " - XX" at end of string.
_STATE_SUFFIX_RE = re.compile(r"\s*[-–—]\s*([A-Z]{2})\s*$")

# Common full-name -> short-name mappings for the major Brazilian clubs.
_NAME_OVERRIDES = {
    "sport club corinthians paulista": "Corinthians",
    "sao paulo futebol clube": "Sao Paulo",
    "são paulo futebol clube": "Sao Paulo",
    "club de regatas do flamengo": "Flamengo",
    "fluminense football club": "Fluminense",
    "vasco da gama": "Vasco",
    "club de regatas vasco da gama": "Vasco",
    "gremio foot ball porto alegrense": "Gremio",
    "sociedade esportiva palmeiras": "Palmeiras",
    "clube de regatas do flamengo": "Flamengo",
    "atletico mineiro": "Atletico-MG",
    "clube atletico mineiro": "Atletico-MG",
    "athletico paranaense": "Athletico-PR",
    "club athletico paranaense": "Athletico-PR",
    "fortaleza esporte clube": "Fortaleza",
    "ceara sporting club": "Ceara",
    "esporte clube bahia": "Bahia",
    "esporte clube vitoria": "Vitoria",
    "botafogo de futebol e regatas": "Botafogo",
    "botafogo futebol e regatas": "Botafogo",
}


def strip_accents(text: str) -> str:
    """Remove diacritics, returning ASCII-friendly text (keeps case)."""
    if not isinstance(text, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def team_key(name: str) -> str:
    """Return a normalized matching key for a team name.

    Lowercases, strips accents, removes state suffixes, drops punctuation and
    parenthetical qualifiers, and collapses whitespace. Two team names that
    refer to the same club will produce identical keys.

    >>> team_key("Palmeiras-SP") == team_key("PALMEIRAS")
    True
    """
    if not isinstance(name, str):
        return ""
    s = name.strip()
    # Drop parenthetical text: "Boavista Sport Club (antigo ...)" -> "Boavista Sport Club"
    s = re.sub(r"\([^)]*\)", "", s)
    # Strip a trailing state suffix once (e.g. "-SP", " - MG").
    m = _STATE_SUFFIX_RE.search(s)
    if m and m.group(1) in BR_STATES:
        s = s[: m.start()].strip()
    s = strip_accents(s).lower()
    # Remove punctuation that is not a letter/digit/space.
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Apply known overrides on the cleaned key.
    if s in _NAME_OVERRIDES:
        s = strip_accents(_NAME_OVERRIDES[s]).lower()
    return s


def canonical_team_name(name: str) -> str:
    """Return a human-friendly canonical display name for a team.

    Strips state suffixes and parenthetical qualifiers, keeps original casing
    of the base name. Falls back to the raw input when nothing matches.

    >>> canonical_team_name("Palmeiras-SP")
    'Palmeiras'
    >>> canonical_team_name("América - MG")
    'América'
    """
    if not isinstance(name, str) or not name.strip():
        return ""
    s = name.strip()
    s = re.sub(r"\([^)]*\)", "", s).strip()
    m = _STATE_SUFFIX_RE.search(s)
    if m and m.group(1) in BR_STATES:
        s = s[: m.start()].strip()
    # Override on the unaccented lowercase form.
    key = re.sub(r"[^\w\s]", " ", strip_accents(s).lower())
    key = re.sub(r"\s+", " ", key).strip()
    if key in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[key]
    return s.strip()


def parse_date(value) -> Optional[datetime]:
    """Parse the multiple date formats present across the datasets.

    Supported:
      - ISO date:        "2023-09-24"
      - ISO datetime:    "2012-05-19 18:30:00"
      - Brazilian date:  "29/03/2003"  (DD/MM/YYYY)

    Returns None for empty/invalid input.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return None
    # Try ISO formats first (most common in the modern datasets).
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # Brazilian DD/MM/YYYY.
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except ValueError:
        return None


def normalize_competition(name: str) -> str:
    """Map raw competition/tournament labels to a canonical competition name.

    The BR-Football-Dataset uses ad-hoc tournament strings ("Serie A",
    "Copa do Brasil", ...). We map those to the canonical labels used across
    the other files so cross-file queries work consistently.

    >>> normalize_competition("Serie A")
    'Brasileirao'
    >>> normalize_competition("Copa do Brasil")
    'Copa do Brasil'
    """
    if not isinstance(name, str):
        return "Unknown"
    key = re.sub(r"\s+", " ", strip_accents(name).lower()).strip()
    if key in {"serie a", "brasileirao serie a", "brasileirao"}:
        return "Brasileirao"
    if key in {"serie b", "brasileirao serie b"}:
        return "Serie B"
    if key in {"serie c", "brasileirao serie c"}:
        return "Serie C"
    if key in {"copa do brasil", "brazilian cup"}:
        return "Copa do Brasil"
    if key in {"libertadores", "copa libertadores", "copa libertadores da america"}:
        return "Copa Libertadores"
    if key in {"sulamericana", "copa sudamericana"}:
        return "Copa Sudamericana"
    # Fallback: return the original cleaned name (title-cased).
    return name.strip()


def to_int(value, default=0) -> int:
    """Best-effort conversion of a goal/corner cell to int. Handles '2', 2.0, ''."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
