"""Team-name, competition and date normalization for the Brazilian soccer datasets.

The datasets use several naming conventions for the same club:

- State suffix with dash: ``Palmeiras-SP``, ``Flamengo-RJ``
- State suffix with spaces: ``América - MG``
- State suffix with space instead of dash: ``America MG``, ``Vasco Da Gama RJ``
- No suffix at all: ``Palmeiras``, ``Flamengo`` (Libertadores / BR-Football)
- Country qualifier in parentheses: ``Nacional (URU)``
- Country qualifier as suffix: ``Guaraní-PAR`` / ``Barcelona-EQU``
- Legacy name notes: ``Boavista Sport Club (antigo Esporte Clube Barreira) - RJ``

This module folds all of those variants onto a single canonical team name and
parses the three date formats found in the data.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Low-level text helpers
# ---------------------------------------------------------------------------

def fold(text: str) -> str:
    """Lowercase and strip diacritics ('São Paulo' -> 'sao paulo')."""
    lowered = text.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# Brazilian state abbreviations used as suffixes in the datasets.
BRAZILIAN_STATES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

# Country codes appended to foreign clubs (Libertadores dataset).
_COUNTRY_CODES = {
    "ARG", "BOL", "CHI", "COL", "EQU", "ECU", "PAR", "PER", "URU", "VEN",
}

_PARENTHETICAL = re.compile(r"\s*\(([^()]*)\)\s*")


def _normalize_punctuation(name: str) -> str:
    """Canonicalize spaces/hyphens so 'América - MG' == 'América-MG'."""
    name = _PARENTHETICAL.sub(_replace_parenthetical, name)
    name = re.sub(r"\s*-\s*", "-", name)
    name = re.sub(r"\s+/\s*", "-", name)
    return _collapse_spaces(name)


def _replace_parenthetical(match: re.Match[str]) -> str:
    content = match.group(1).strip()
    upper = content.upper()
    # 'Nacional (URU)' -> 'Nacional-URU'; drop legacy notes like
    # 'Boavista Sport Club (antigo Esporte Clube Barreira)'.
    if upper in _COUNTRY_CODES:
        return f"-{upper}"
    return " "


def canonical_key(name: str) -> str:
    """Fold a raw team name onto a matching key (accents removed)."""
    return fold(_normalize_punctuation(name.strip()))


# ---------------------------------------------------------------------------
# Alias table: folded variant -> canonical display name
# ---------------------------------------------------------------------------

ALIASES: dict[str, str] = {}


def _alias(canonical: str, *variants: str) -> None:
    for variant in variants:
        key = canonical_key(variant)
        ALIASES[key] = canonical


CLASSIC_CLUBS: list[tuple[str, list[str]]] = [
    ("América Mineiro", ["America-MG", "América-MG", "América Mineiro", "America MG", "América MG"]),
    ("América de Natal", ["America-RN", "América-RN", "América de Natal", "América - RN", "America RN", "América RN", "América FC Natal"]),
    ("Athletico Paranaense", [
        "Atletico-PR", "Athletico-PR", "Atlético-PR", "Atlético - PR",
        "Athletico Paranaense", "Atletico Paranaense", "Atlético Paranaense",
        "Athletico", "Atletico Paranaense PR",
    ]),
    ("Atlético Goianiense", ["Atletico-GO", "Atlético-GO", "Atlético - GO", "Atletico Goianiense", "Atlético Goianiense", "Atlético-GO GO"]),
    ("Atlético Mineiro", ["Atletico-MG", "Atlético-MG", "Atlético - MG", "Atlético Mineiro", "Atletico Mineiro"]),
    ("Avaí", ["Avai-SC", "Avaí - SC", "Avaí", "Avai", "Avaí SC"]),
    ("Bahia", ["Bahia-BA", "Bahia - BA", "Bahia", "EC Bahia", "Bahia BA"]),
    ("Botafogo", ["Botafogo-RJ", "Botafogo - RJ", "Botafogo RJ", "Botafogo"]),
    ("Botafogo-PB", ["Botafogo-PB", "Botafogo - PB"]),
    ("Botafogo-SP", ["Botafogo SP", "Botafogo-SP"]),
    ("Bragantino-PA", ["Bragantino - PA", "Bragantino PA", "Bragantino-PA"]),
    ("Ceará", ["Ceara-CE", "Ceará - CE", "Ceará", "Ceara", "Ceará Sporting Club", "Ceara CE"]),
    ("Chapecoense", ["Chapecoense-SC", "Chapecoense - SC", "Chapecoense", "Chapecoense SC"]),
    ("Corinthians", ["Corinthians-SP", "Corinthians - SP", "Corinthians SP", "Corinthians", "Sport Club Corinthians Paulista"]),
    ("Coritiba", ["Coritiba-PR", "Coritiba - PR", "Coritiba PR", "Coritiba"]),
    ("Criciúma", ["Criciuma-SC", "Criciúma", "Criciuma"]),
    ("Cruzeiro", ["Cruzeiro-MG", "Cruzeiro - MG", "Cruzeiro MG", "Cruzeiro"]),
    ("CSA", ["Csa-AL", "CSA - AL", "CSA AL", "CSA", "Centro Sportivo Alagoano"]),
    ("Cuiabá", ["Cuiaba-MT", "Cuiabá - MT", "Cuiaba MT", "Cuiabá", "Cuiaba"]),
    ("Figueirense", ["Figueirense-SC", "Figueirense - SC", "Figueirense SC", "Figueirense"]),
    ("Flamengo", ["Flamengo-RJ", "Flamengo - RJ", "Flamengo RJ", "Flamengo"]),
    ("Fluminense", ["Fluminense-RJ", "Fluminense - RJ", "Fluminense RJ", "Fluminense"]),
    ("Fortaleza", ["Fortaleza-CE", "Fortaleza - CE", "Fortaleza CE", "Fortaleza", "Fortaleza EC"]),
    ("Goiás", ["Goias-GO", "Goiás - GO", "Goiás", "Goias"]),
    ("Grêmio", ["Gremio-RS", "Grêmio - RS", "Grêmio", "Gremio", "Gremio RS"]),
    ("Internacional", ["Internacional-RS", "Internacional - RS", "Internacional RS", "Internacional", "SC Internacional"]),
    ("Joinville", ["Joinville-SC", "Joinville - SC", "Joinville SC", "Joinville"]),
    ("Juventude", ["Juventude-RS", "Juventude - RS", "Juventude RS", "Juventude", "EC Juventude"]),
    ("Náutico", ["Nautico-PE", "Náutico - PE", "Náutico", "Nautico", "Nautico Capibaribe", "Clube Náutico Capibaribe"]),
    ("Palmeiras", ["Palmeiras-SP", "Palmeiras - SP", "Palmeiras SP", "Palmeiras", "Sociedade Esportiva Palmeiras"]),
    ("Paraná", ["Parana-PR", "Paraná - PR", "Paraná", "Parana", "CA Parana"]),
    ("Ponte Preta", ["Ponte Preta-SP", "Ponte Preta - SP", "Ponte Preta SP", "Ponte Preta", "Associação Atlética Ponte Preta"]),
    ("Portuguesa", ["Portuguesa-SP", "Portuguesa - SP", "Portuguesa SP", "Portuguesa", "Portuguesa Desportos"]),
    ("Portuguesa-RJ", ["Portuguesa RJ", "Portuguesa-RJ"]),
    ("Red Bull Bragantino", ["Red Bull Bragantino-SP", "Red Bull Bragantino - SP", "Red Bull Bragantino", "Bragantino - SP", "Bragantino SP", "Bragantino", "Red Bull Brasil"]),
    ("Santa Cruz", ["Santa Cruz-PE", "Santa Cruz - PE", "Santa Cruz PE", "Santa Cruz"]),
    ("Santos", ["Santos-SP", "Santos - SP", "Santos SP", "Santos"]),
    ("São Paulo", ["Sao Paulo-SP", "São Paulo - SP", "São Paulo SP", "São Paulo", "Sao Paulo"]),
    ("Sport Recife", ["Sport-PE", "Sport - PE", "Sport PE", "Sport", "Sport Recife", "Sport Club do Recife"]),
    ("Vasco da Gama", ["Vasco da Gama-RJ", "Vasco da Gama - RJ", "Vasco Da Gama RJ", "Vasco da Gama", "Vasco", "Club de Regatas Vasco da Gama"]),
    ("Vitória", ["Vitoria-BA", "Vitória - BA", "Vitória", "Vitoria", "EC Vitoria", "Vitoria EC", "Vitória EC"]),
    ("Boavista", ["Boavista Sport Club - RJ", "Boavista - RJ", "Boavista RJ", "Boavista"]),
    ("Confiança", ["AD Confianca", "Confianca", "Confiança", "Confianca SE", "Confiança SE"]),
    ("CRB", ["Crb - AL", "CRB - AL", "C. R. B. - AL", "CRB AL", "CRB", "C.R.B.", "C. R. B."]),
    ("ABC", ["ABC - RN", "Abc - RN", "ABC RN", "ABC"]),
    ("Guarani", ["Guarani", "Guarani - SP", "Guarani-SP", "Guarani SP", "Guarani Futebol Clube"]),
]

for canonical, variants in CLASSIC_CLUBS:
    _alias(canonical, *variants)

# Libertadores foreign-club spellings. Note: plain 'Guaraní' is deliberately
# NOT an alias here — 'Guarani' (Campinas, SP) is a different Brazilian club.
_alias("Guaraní (PAR)", "Guaraní-PAR", "Guaraní - PAR", "Guaraní (PAR)")
_alias("Nacional (URU)", "Nacional-URU", "Nacional (URU)")
_alias("Delfín", "Delfín-EQU", "Delfín - EQU", "Delfín")
_alias("Barcelona (EQU)", "Barcelona-EQU", "Barcelona - EQU", "Barcelona (EQU)")

resolve_cache: dict[str, str | None] = {}


def resolve_team(name: str) -> str | None:
    """Map any raw team spelling onto its canonical name.

    Resolution order:
    1. direct alias lookup on the folded key ('atlético - mg' -> 'Atlético Mineiro')
    2. strip a trailing Brazilian state suffix and retry
       ('Atlético Mineiro - MG' -> 'atlético mineiro' -> 'Atlético Mineiro')
    3. fall back to the folded key (deterministic cross-file identifier)

    Returns the canonical display name, or ``None`` when the input is empty.
    Unknown names are returned accent-folded so cross-file matching still has
    a deterministic key.
    """
    raw = (name or "").strip()
    if not raw:
        return None
    key = canonical_key(raw)
    if key in resolve_cache:
        return resolve_cache[key]
    resolved = ALIASES.get(key)
    if resolved is None:
        stripped = _strip_state_suffix(key)
        if stripped != key:
            resolved = ALIASES.get(stripped)
    if resolved is None:
        resolved = key
    resolve_cache[key] = resolved
    return resolved


def _strip_state_suffix(key: str) -> str:
    """Drop a trailing '-sp'-style state suffix from a folded key."""
    if len(key) > 3 and key[-3] == "-" and key[-2:] in _FOLDED_STATES:
        return key[:-3].rstrip("- ")
    return key


_FOLDED_STATES = {state.lower() for state in BRAZILIAN_STATES}


def matches_team(raw_name: str, canonical: str) -> bool:
    """True when ``raw_name`` refers to the canonical team ``canonical``."""
    resolved = resolve_team(raw_name)
    return resolved is not None and resolved == canonical


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


def parse_date(value: str) -> tuple[date | None, datetime | None]:
    """Parse the date formats used across the datasets.

    Returns ``(date, datetime)``; ``datetime`` is ``None`` when only a plain
    date is available. Invalid or empty input yields ``(None, None)``.
    """
    value = (value or "").strip()
    if not value:
        return None, None
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if "%H" in fmt:
            return parsed.date(), parsed
        return parsed.date(), None
    return None, None


def parse_int(value: str | None) -> int | None:
    """Parse an integer column value, tolerating blanks and junk."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None
