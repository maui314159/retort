"""
Brazilian Soccer MCP - Team Name Normalizer.

This module provides robust team name normalization for Brazilian football data.
Brazilian datasets use inconsistent team naming conventions:
    - With state suffix: "Palmeiras-SP", "Flamengo-RJ"
    - Without suffix: "Palmeiras", "Flamengo"
    - Full legal names: "Sport Club Corinthians Paulista"
    - Local/anglicized variations: "Athletico Paranaense" vs "Athletico-PR"

The normalizer maps these variations onto canonical team keys so that queries
match across all six provided CSV files.  The canonical key is the team's common
short name in Title Case (e.g. "Flamengo", "Palmeiras", "Corinthians").
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable


# Aliases that appear in the datasets and should map to a canonical key.
# Keys are Title Case short names.  Values include the canonical form first
# followed by known aliases (case-insensitive match).
_TEAM_ALIASES: dict[str, list[str]] = {
    "America Mineiro": ["america mg", "america-mg", "america mineiro", "coelho"],
    "America RN": ["america rn", "america-rn"],
    "Athletico-PR": [
        "athletico paranaense",
        "athletico-pr",
        "athletico pr",
        "atletico paranaense",
        "atletico-pr",
        "furacao",
    ],
    "Atletico Goianiense": [
        "atletico goianiense",
        "atletico-goianiense",
        "atletico go",
        "atletico-go",
        "dragao",
    ],
    "Atletico-MG": [
        "atletico mineiro",
        "atletico-mg",
        "atletico mg",
        "atletico-mineiro",
        "galo",
    ],
    "Avai": ["avai fc", "avai"],
    "Bahia": ["bahia", "esporte clube bahia", "ec bahia", "tricolor de aco"],
    "Botafogo": [
        "botafogo",
        "botafogo rj",
        "botafogo-rj",
        "botafogo fr",
        "fogao",
    ],
    "Bragantino": [
        "bragantino",
        "red bull bragantino",
        "rb bragantino",
        "massa bruta",
    ],
    "Ceara": ["ceara", "ceara sc", "ceara sporting club", "vozao"],
    "Corinthians": [
        "corinthians",
        "sport club corinthians paulista",
        "sccp",
        "timao",
    ],
    "Coritiba": ["coritiba", "coritiba fc", "coxa"],
    "Criciuma": ["criciuma", "criciuma ec", "tigre"],
    "Cruzeiro": ["cruzeiro", "cruzeiro ec", "raposa"],
    "Flamengo": ["flamengo", "clube de regatas do flamengo", "crf", "mengao"],
    "Fluminense": ["fluminense", "fluminense fc", "flu", "tricolor"],
    "Fortaleza": ["fortaleza", "fortaleza ec", "leao do pici"],
    "Goias": ["goias", "goias ec", "esmeraldino"],
    "Gremio": [
        "gremio",
        "gremio fbpa",
        "gremio portoalegrense",
        "imortal",
    ],
    "Internacional": ["internacional", "sport club internacional", "colorado"],
    "Juventude": ["juventude", "ec juventude", "papada"],
    "Nautico": ["nautico", "nautico capibaribe", "timbu"],
    "Palmeiras": [
        "palmeiras",
        "sociedade esportiva palmeiras",
        "sep",
        "porco",
    ],
    "Parana": ["parana", "parana clube", "tricolor da vila"],
    "Ponte Preta": ["ponte preta", "aa ponte preta", "macaca"],
    "Portuguesa": [
        "portuguesa",
        "portuguesa sp",
        "portuguesa-sp",
        "portuguesa de desportos",
        "luso",
    ],
    "Santos": ["santos", "santos fc", "peixe"],
    "Sao Paulo": [
        "sao paulo",
        "sao paulo fc",
        "spfc",
        "tricolor paulista",
    ],
    "Sport": ["sport", "sport recife", "sport club do recife", "leao"],
    "Vasco da Gama": [
        "vasco",
        "vasco da gama",
        "cr vasco da gama",
        "vascao",
    ],
    "Vitoria": ["vitoria", "vitoria ec", "esporte clube vitoria", "leao da barra"],
}

# Inverted lookup: alias -> canonical key.
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in _TEAM_ALIASES.items():
    _ALIAS_TO_CANONICAL[_canonical.lower()] = _canonical
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias] = _canonical

# Common Brazilian state abbreviations used as suffixes in the data.
_STATE_ABBREVIATIONS: set[str] = {
    "ac", "al", "ap", "am", "ba", "bh", "ce", "df", "es", "go",
    "ma", "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj",
    "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
}

# FIFA club strings that we want to strip from player Club values.
_CLUB_SUFFIXES = ["fc", "ec", "sc", "ac", "cf", "esporte clube"]


def _strip_accents(text: str) -> str:
    """Return the base form of a Unicode string (NFD + ASCII filter)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def _remove_state_suffix(name: str) -> str:
    """Remove trailing state suffixes such as '-SP' or ' - RJ'."""
    name = name.strip()
    # Handle "Name - XX" and "Name-XX"
    parts = name.rsplit(" - ", 1)
    if len(parts) == 2 and parts[1].strip().lower() in _STATE_ABBREVIATIONS:
        return parts[0].strip()
    if "-" in name:
        last = name.rsplit("-", 1)[1].strip().lower()
        if last in _STATE_ABBREVIATIONS:
            return name.rsplit("-", 1)[0].strip()
    return name


def _normalize_one(name: str) -> str:
    """Normalize a single team name to its canonical key or a clean fallback."""
    if not isinstance(name, str) or not name.strip():
        return ""

    cleaned = name.strip()
    cleaned = _remove_state_suffix(cleaned)
    # Remove parenthetical qualifiers like "(URU)", "(antigo ...)"
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)
    cleaned = cleaned.strip()

    # Direct alias lookup (accent-insensitive, case-insensitive).
    lookup = cleaned.lower().strip()
    lookup = _strip_accents(lookup)
    if lookup in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[lookup]

    # Try again after normalizing "atletico" variants.
    lookup = lookup.replace("athletico", "atletico")
    if lookup in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[lookup]

    # If still no match, clean up common suffixes and try one more time.
    tokens = lookup.split()
    while tokens and tokens[-1].lower() in _CLUB_SUFFIXES:
        tokens.pop()
    retry = " ".join(tokens)
    if retry in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[retry]

    # Fallback: return the cleaned input in Title Case without accents.
    return cleaned.title().strip() or cleaned.strip()


def normalize_team_name(name: str | None) -> str:
    """Return the canonical team name for ``name``.

    Args:
        name: Raw team name as it appears in a dataset.

    Returns:
        Canonical team name (e.g. "Palmeiras").  Returns an empty string for
        missing/empty input.
    """
    if name is None:
        return ""
    return _normalize_one(name)


def normalize_team_names(names: Iterable[str | None]) -> list[str]:
    """Normalize a collection of team names."""
    return [normalize_team_name(n) for n in names]


def canonical_team_names() -> list[str]:
    """Return the list of known canonical team names."""
    return sorted(_TEAM_ALIASES.keys())


def are_same_team(a: str | None, b: str | None) -> bool:
    """Return True if ``a`` and ``b`` refer to the same canonical team."""
    return normalize_team_name(a) == normalize_team_name(b) and normalize_team_name(a) != ""
