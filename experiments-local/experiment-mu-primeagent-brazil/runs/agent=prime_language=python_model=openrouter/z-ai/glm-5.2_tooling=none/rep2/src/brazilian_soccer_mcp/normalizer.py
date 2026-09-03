"""
Context block
=============
Brazilian Soccer MCP Server - Team Name Normalizer
---------------------------------------------------
Purpose: Provide robust, cross-dataset team-name normalization so that the same
club can be matched across all provided CSV files even though each file uses a
different naming convention (state suffixes "Palmeiras-SP", full names
"Sport Club Corinthians Paulista", accented forms "Atlético-MG" vs ascii
"Atletico-MG", FIFA club strings "América FC (Minas Gerais)", etc.).

Design:
  * canonical_key(name) -> a stable lowercase ascii key used for matching/joins.
  * display_name(name) -> a human friendly accented display name.
  * An explicit alias table disambiguates clubs that share a short base name
    and only differ by state (e.g. "Atletico-MG" vs "Atletico-GO" vs
    "Athletico-PR" / "Atletico-PR" / "Athletico").
  * A fallback generic normalizer handles teams not listed in the alias table
    (mostly foreign clubs that only appear in the Libertadores file).

This module is pure-Python and has no third-party dependencies so it can be
imported and unit-tested in isolation.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Brazilian state abbreviations (UF) plus a few South-American country codes
# that appear as suffixes in the Libertadores dataset (e.g. "Barcelona-EQU").
STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
    "URU", "EQU", "ARG", "BOL", "PAR", "COL", "CHI", "VEN", "ECU", "PER",
    "MEX",
}

# Generic club-designator words removed when building a key. We deliberately
# KEEP "sport", "esporte", "futebol" because some clubs ("Sport" of Recife)
# use them as the actual club name.
GENERIC_WORDS = {
    "fc", "ec", "ac", "sc", "clube", "club", "regatas",
    "de", "do", "da", "dos", "das",
}

# Canonical display name -> list of alias lookup keys. Each lookup key is the
# _key_from_base() form (accent-folded, lowercased, generic words removed,
# state kept as a lowercase token when present).
CLUB_ALIASES: dict[str, list[str]] = {
    "Flamengo": ["flamengo"],
    "Fluminense": ["fluminense"],
    "Palmeiras": ["palmeiras"],
    "Santos": ["santos"],
    "Corinthians": ["corinthians", "corinthians paulista"],
    "São Paulo": ["sao paulo"],
    "Grêmio": ["gremio"],
    "Cruzeiro": ["cruzeiro"],
    "Internacional": ["internacional"],
    "Botafogo": ["botafogo"],
    "Vasco da Gama": ["vasco gama"],
    "Bahia": ["bahia"],
    "Vitória": ["vitoria"],
    "Chapecoense": ["chapecoense"],
    "Fortaleza": ["fortaleza", "fortaleza ec"],
    "Ceará": ["ceara", "ceara sporting"],
    "Goiás": ["goias"],
    "Coritiba": ["coritiba"],
    "Athletico Paranaense": [
        "athletico", "athletico pr", "atletico pr",
        "athletico paranaense", "atletico paranaense",
    ],
    "Atlético Mineiro": ["atletico mg", "atletico mineiro"],
    "Atlético Goianiense": ["atletico go", "atletico goianiense"],
    "Sport": ["sport", "sport recife", "sport club recife"],
    "América Mineiro": [
        "america mg", "america", "america minas gerais", "america mineiro",
    ],
    "América RN": ["america rn"],
    "América CE": ["america ce"],
    "Criciúma": ["criciuma"],
    "Figueirense": ["figueirense"],
    "Náutico": ["nautico"],
    "Ponte Preta": ["ponte preta"],
    "Portuguesa": ["portuguesa"],
    "Santa Cruz": ["santa cruz"],
    "Joinville": ["joinville"],
    "Paraná": ["parana", "parana clube"],
    "CSA": ["csa"],
    "Avaí": ["avai"],
    "Red Bull Bragantino": ["red bull bragantino", "bragantino"],
    "Cuiabá": ["cuiaba"],
    "Juventude": ["juventude"],
    "Botafogo SP": ["botafogo sp"],
    "América RJ": ["america rj"],
    "Bahia de Feira": ["bahia feira"],
}

# alias key -> display name
_ALIAS_LOOKUP: dict[str, str] = {}
for _display, _keys in CLUB_ALIASES.items():
    for _k in _keys:
        _ALIAS_LOOKUP[_k] = _display


def _fold(s: str) -> str:
    """Fold accents to ascii and lowercase."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _key_from_base(base: str, state: str) -> str:
    """Build a lookup key from a (possibly accented) base name and state."""
    base = _fold(base)
    tokens = [t for t in base.split() if t and t not in GENERIC_WORDS]
    if state:
        tokens.append(state)
    key = " ".join(tokens)
    key = re.sub(r"[^a-z0-9 ]", "", key)
    key = re.sub(r"\s+", " ", key).strip()
    return key


def _display_to_key(display: str) -> str:
    """Stable ascii key derived from a display name (no alias recursion)."""
    return _key_from_base(display, "")


# Pre-compute canonical key for every display name to avoid recursion.
_DISPLAY_KEY: dict[str, str] = {d: _display_to_key(d) for d in CLUB_ALIASES}


def _strip_suffix(name: str) -> tuple[str, str]:
    """Return (base, state) where state is a lowercase code or ''.

    Removes trailing "-XX", " - XX" suffixes and a trailing standalone state
    token such as "Botafogo RJ". Parenthetical content like "(URU)" is removed
    but if it contains a known code it is captured as the state.
    """
    s = name.strip()
    state = ""

    m = re.search(r"\(([A-Z]{2,3})\)", s)
    if m and m.group(1) in STATE_CODES:
        state = m.group(1).lower()
    region_map = {"minas gerais": "mg", "parana": "pr", "sao paulo": "sp"}
    m2 = re.search(r"\(([^)]+)\)", s)
    if m2 and not state:
        region = _fold(m2.group(1))
        if region in region_map:
            state = region_map[region]

    s = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()

    m = re.search(r"\s*-\s*([A-Z]{2,3})$", s)
    if m and m.group(1) in STATE_CODES:
        state = m.group(1).lower()
        s = s[: m.start()].strip()

    m = re.match(r"^(.*)\s+([A-Z]{2})$", s)
    if m and m.group(2) in STATE_CODES:
        state = m.group(2).lower()
        s = m.group(1).strip()

    return s, state


@lru_cache(maxsize=4096)
def canonical_key(name: object) -> str:
    """Return a stable lowercase ascii key for a team name."""
    if name is None:
        return ""
    s = str(name)
    if s.lower() in ("nan", "none", ""):
        return ""
    base, state = _strip_suffix(s)
    key_keep = _key_from_base(base, state)
    if key_keep in _ALIAS_LOOKUP:
        return _DISPLAY_KEY[_ALIAS_LOOKUP[key_keep]]
    key_strip = _key_from_base(base, "")
    if key_strip in _ALIAS_LOOKUP:
        return _DISPLAY_KEY[_ALIAS_LOOKUP[key_strip]]
    return key_strip


@lru_cache(maxsize=4096)
def display_name(name: object) -> str:
    """Return the best human-friendly display name for a team."""
    if name is None:
        return ""
    s = str(name)
    if s.lower() in ("nan", "none", ""):
        return ""
    base, state = _strip_suffix(s)
    key_keep = _key_from_base(base, state)
    if key_keep in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[key_keep]
    key_strip = _key_from_base(base, "")
    if key_strip in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[key_strip]
    return base.strip() or s.strip()


# Traditional Brazilian derby pairs (canonical display names).
DERBY_PAIRS: list[tuple[str, str]] = [
    ("Flamengo", "Fluminense"),
    ("Flamengo", "Vasco da Gama"),
    ("Flamengo", "Botafogo"),
    ("Palmeiras", "Corinthians"),
    ("Palmeiras", "São Paulo"),
    ("Corinthians", "São Paulo"),
    ("Santos", "São Paulo"),
    ("Grêmio", "Internacional"),
    ("Atlético Mineiro", "Cruzeiro"),
    ("Bahia", "Vitória"),
    ("Fortaleza", "Ceará"),
    ("Sport", "Santa Cruz"),
    ("Sport", "Náutico"),
    ("Náutico", "Santa Cruz"),
    ("Coritiba", "Athletico Paranaense"),
    ("Botafogo", "Vasco da Gama"),
    ("Fluminense", "Vasco da Gama"),
]


def is_derby(team_a: object, team_b: object) -> bool:
    """True if the two (possibly differently-spelled) teams are traditional rivals."""
    a = display_name(team_a)
    b = display_name(team_b)
    return (a, b) in DERBY_PAIRS or (b, a) in DERBY_PAIRS
