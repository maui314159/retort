"""
Normalization helpers for the Brazilian Soccer MCP Server.

The included CSVs use several different naming conventions for teams and
dates. This module hides that complexity by canonicalising team names,
competitions, dates and goal values so the rest of the application works on a
single, stable representation.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Brazilian state/country codes that sometimes appear as trailing suffixes.
_STATE_CODES = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    # Common international codes seen in the Libertadores dataset.
    "URU", "ARG", "BRA", "CHI", "COL", "ECU", "PAR", "PER", "VEN", "BOL",
)

# Matches optional whitespace, a dash and a state code at the end of a team
# name, e.g. "Palmeiras-SP", "Palmeiras - SP" or "Botafogo RJ".
_STATE_SUFFIX_RE = re.compile(r"(?:\s*-\s*|\s+)(" + "|".join(_STATE_CODES) + r")$")

# Matches a parenthetical state/country code at the end, e.g. "Nacional (URU)".
_PARENS_SUFFIX_RE = re.compile(r"\s*\(\s*(" + "|".join(_STATE_CODES) + r")\s*\)$")

# Removes parenthetical explanations such as
# "Boavista Sport Club (antigo Esporte Clube Barreira)".
_PARENS_RE = re.compile(r"\s*\([^)]*\)")

# Collapses punctuation and whitespace for canonical keys.
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Roots that are shared by several distinct clubs. For these we keep a state
# code so that, for example, Atlético-MG and Atlético-PR remain separate.
AMBIGUOUS_ROOTS = (
    "atletico",
    "sport",
    "america",
    "nacional",
    "botafogo",
    "vitoria",
    "victoria",
    "portuguesa",
    "santa",
)

# Map trailing descriptors to state/country codes. Used when a dataset gives
# the long form of an ambiguous team name without a numeric state suffix.
DESCRIPTOR_STATE = {
    "mineiro": "mg",
    "mineira": "mg",
    "paranaense": "pr",
    "parana": "pr",
    "goianiense": "go",
    "goiano": "go",
    "cearense": "ce",
    "ceara": "ce",
    "baiano": "ba",
    "bahia": "ba",
    "paulista": "sp",
    "paulistano": "sp",
    "carioca": "rj",
    "gaucho": "rs",
    "gaucha": "rs",
    "potiguar": "rn",
    "pernambucano": "pe",
    "pernambucana": "pe",
    "recifense": "pe",
    "recife": "pe",
    "fluminense": "rj",
    "amazonense": "am",
    "paraense": "pa",
    "sergipano": "se",
    "sergipana": "se",
    "catarinense": "sc",
    "matogrossense": "mt",
    "matogrosso": "mt",
    "sulmatogrossense": "ms",
    "sulmatogrosso": "ms",
    "rondoniense": "ro",
    "capixaba": "es",
    "maranhense": "ma",
    "paraibano": "pb",
    "piauiense": "pi",
    "alagoano": "al",
    "alagoana": "al",
    "brasiliense": "df",
    "brasilia": "df",
}

# A small set of aliases that map historical/typographic variants to a shared
# canonical base **before** appending the state suffix. This keeps
# Atlético-MG distinct from Athletico-PR while still recognising the
# Athletico -> Atlético rebranding.
_BASE_ALIASES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^athletico"), "atletico"),  # Athletico Paranaense
]

# Friendly display aliases for common shorthand used in queries.
DISPLAY_ALIASES = {
    "spfc": "São Paulo",
    "timao": "Corinthians",
    "mengao": "Flamengo",
    "galo": "Atlético Mineiro",
}

# Map specific raw canonical forms produced by different datasets to a shared
# canonical key. This removes duplicates that arise from different naming
# styles such as "Red Bull Bragantino" vs "Bragantino" or "EC Juventude"
# vs "Juventude".
TEAM_CANONICAL_ALIASES: dict[str, str] = {
    "redbullbragantino": "bragantino",
    "bragantinosp": "bragantino",
    "ecjuventude": "juventude",
    "juventude": "juventude",
    "esporteclubejuventude": "juventude",
    "fortalezafc": "fortaleza",
    "fortalezace": "fortaleza",
    "clubederegatasdoflamengo": "flamengo",
    "flamengorj": "flamengo",
    "sportclubcorinthianspaulista": "corinthians",
    "corinthianssp": "corinthians",
    "saopaulofutebolclube": "saopaulo",
    "saopaulofc": "saopaulo",
    "santosfutebolclube": "santos",
    "santosfc": "santos",
    "gremiofootballportoalegrense": "gremio",
    "gremiors": "gremio",
    "sportclubinternacional": "internacional",
    "internacionalrs": "internacional",
    "cluberecrionegra": "vasco",
    "vascodagama": "vasco",
    "vascorj": "vasco",
    "fluminensefootballclub": "fluminense",
    "fluminenserj": "fluminense",
    "esporteclubebahia": "bahia",
    "bahiaba": "bahia",
    "cearasc": "ceara",
    "paranaclube": "parana",
    "avaisc": "avai",
    "goiasesporteclube": "goias",
    "americamineiro": "americamg",
    "americafcmg": "americamg",
    "botafogodefuteboleregentas": "botafogorj",
    "botafogorj": "botafogorj",
    "botafogofr": "botafogorj",
    "botafogofutebolclube": "botafogorj",
    "pontepreta": "pontepreta",
    "associacaoatleticapontepreta": "pontepreta",
    "criciumaesporteclube": "criciuma",
    "figueirensefc": "figueirense",
    "chapecoenseaf": "chapecoense",
    "nautico": "nautico",
    "clubenautico": "nautico",
    "londrinaesporteclube": "londrina",
    "csa": "csaal",
    "csaal": "csaal",
    "csaalagoas": "csaal",
}


def strip_accents(text: str) -> str:
    """Return an ASCII-fied version of *text* with diacritics removed."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if unicodedata.category(c) != "Mn"
    )


def _clean_base(name: str) -> tuple[str, str]:
    """
    Extract any trailing state/country code and build the accent-free,
    punctuation-free base key for a team name.

    Returns ``(raw_base_key, explicit_state_code)``.
    """
    name = name.strip()
    state = ""
    # "América-MG", "Botafogo - RJ", "Botafogo RJ"
    state_match = _STATE_SUFFIX_RE.search(name)
    if state_match:
        state = state_match.group(1).upper()
        name = name[: state_match.start()].strip()
    else:
        # "Nacional (URU)" or "América (MG)"
        parens_match = _PARENS_SUFFIX_RE.search(name)
        if parens_match:
            state = parens_match.group(1).upper()
            name = name[: parens_match.start()].strip()

    name = _PARENS_RE.sub("", name).strip()
    name = re.sub(r"\s+", " ", name)

    base = name.lower()
    base = strip_accents(base)
    base = _NON_ALNUM_RE.sub("", base)

    for pattern, replacement in _BASE_ALIASES:
        base = pattern.sub(replacement, base)

    return base, state


def _extract_ambiguous_root(key: str) -> tuple[str, str]:
    """Return (root, tail) if *key* starts with an ambiguous club root."""
    for root in AMBIGUOUS_ROOTS:
        if key == root:
            return root, ""
        if key.startswith(root):
            return root, key[len(root) :]
    return "", ""


def _descriptor_state(tail: str) -> str:
    """Infer a state/country code from trailing words such as 'mineiro'."""
    if not tail:
        return ""
    for descriptor, code in DESCRIPTOR_STATE.items():
        if descriptor in tail:
            return code
    return ""


def canonical_team_name(name: str) -> tuple[str, str, str]:
    """
    Canonicalise a team name.

    Returns a 3-tuple ``(canonical_key, state_code, raw_base_key)``.

    For most clubs the state suffix is stripped so that "Flamengo-RJ",
    "Flamengo" and "Clube de Regatas do Flamengo" all share one key. For
    ambiguous roots such as Atlético, América and Botafogo the state is kept so
    that Atlético-MG and Atlético-PR remain distinct.
    """
    raw_key, explicit_state = _clean_base(name)
    root, tail = _extract_ambiguous_root(raw_key)
    if root:
        state = (explicit_state or _descriptor_state(tail)).lower()
        canonical = root + state
    else:
        canonical = raw_key
        state = explicit_state.lower()  # purely informational for non-ambiguous names
    canonical = TEAM_CANONICAL_ALIASES.get(canonical, canonical)
    return canonical.strip(), state, raw_key


def display_team_name(name: str) -> str:
    """Return a human-friendly team name with state suffix and notes removed."""
    name = name.strip()
    match = _STATE_SUFFIX_RE.search(name)
    if match:
        name = name[: match.start()].strip()
    name = _PARENS_RE.sub("", name).strip()
    name = re.sub(r"\s+", " ", name)
    return name


def _normalise_text(value: str) -> str:
    """Lower-case, accent-free form used for substring searches."""
    value = value or ""
    return strip_accents(value).lower()


def competition_canonical(name: str) -> str:
    """
    Map a raw competition name to a canonical label.

    Recognises Portuguese and English variants of the main Brazilian
    competitions.
    """
    value = _normalise_text(name)
    if "libertadores" in value or "copa libertadores" in value:
        return "Copa Libertadores"
    if "copa do brasil" in value or "brazilian cup" in value:
        return "Copa do Brasil"
    if "brasileir" in value or "campeonato brasileiro" in value:
        return "Brasileirão"
    # The extended dataset uses "Serie A" as the Brasileirão and labels the
    # lower divisions explicitly.
    if value in ("serie a", "série a"):
        return "Brasileirão"
    if value in ("serie b", "série b"):
        return "Brasileirão Série B"
    if value in ("serie c", "série c"):
        return "Brasileirão Série C"
    return name.strip()


def parse_season(value: Optional[str | int | float]) -> Optional[int]:
    """Convert a season value to a clean integer year."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_score(value: Optional[str | int | float]) -> Optional[int]:
    """Parse a goal value, returning ``None`` for missing/'NA' entries."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_date(value: Optional[str]) -> Optional[date]:
    """
    Parse dates from the various formats used in the CSV files.

    Supported formats: ``YYYY-MM-DD HH:MM:SS``, ``YYYY-MM-DD``,
    ``DD/MM/YYYY`` (with optional time), and ISO dates.
    """
    if not value:
        return None
    value = str(value).strip()
    # If the value looks like a year-only integer, reject it as a date.
    if value.isdigit():
        return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_date_param(value: Optional[str | date | datetime]) -> Optional[date]:
    """Normalise a user-supplied date parameter to a ``datetime.date``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse_date(value)
