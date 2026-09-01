"""Normalization helpers for heterogeneous Brazilian soccer datasets.

Context: the six bundled Kaggle CSV files describe the same real-world
clubs under many different spellings ("Palmeiras-SP", "Palmeiras",
"Sociedade Esportiva Palmeiras", "Grêmio" vs "Gremio-RS", "Athletico-PR"
vs "Atlético-PR"), record dates in ISO, ISO+time and Brazilian day-first
formats, and store numbers as ints, floats or the sentinel "NA"/"-".
Every raw CSV value is funneled through the helpers below so that team
matching, grouping and sorting behave consistently across all files.

Public API:
    strip_accents(value)          -> ASCII-folded string
    clean_text(value)             -> canonical comparison form for names
    split_team(name)              -> (base, qualifier) pair for a team name
    parse_date(value)             -> (date, "HH:MM") or (None, None)
    parse_int(value)              -> int or None
    is_nothing(value)             -> True for empty/"NA"/"-"/"None" cells
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

BRAZILIAN_STATE_ABBRS = frozenset(
    {
        "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma",
        "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn",
        "rs", "ro", "rr", "sc", "sp", "se", "to",
    }
)

COUNTRY_ABBRS = frozenset(
    {
        "arg", "bol", "bra", "chi", "col", "ecu", "equ", "par", "per",
        "uru", "ven", "mex", "usa", "crc", "gua", "hon", "slv", "pan",
        "jam", "can", "tri",
    }
)

QUALIFIER_ABBRS = BRAZILIAN_STATE_ABBRS | COUNTRY_ABBRS

PAREN_STATE_NAMES = {
    "minas gerais": "mg",
    "rio de janeiro": "rj",
    "sao paulo": "sp",
    "rio grande do sul": "rs",
    "santa catarina": "sc",
    "parana": "pr",
    "bahia": "ba",
    "ceara": "ce",
    "pernambuco": "pe",
    "goias": "go",
    "paraiba": "pb",
}

FULL_NAME_ALIASES = {
    "sport club corinthians paulista": "corinthians sp",
    "clube de regatas do flamengo": "flamengo rj",
    "sociedade esportiva palmeiras": "palmeiras sp",
    "sao paulo fc": "sao paulo sp",
    "santos fc": "santos sp",
    "fluminense fc": "fluminense rj",
    "botafogo fr": "botafogo rj",
    "sc internacional": "internacional rs",
    "gremio fbpa": "gremio rs",
    "atletico mineiro": "atletico mg",
    "clube atletico mineiro": "atletico mg",
    "atletico paranaense": "atletico pr",
    "athletico paranaense": "atletico pr",
    "atletico goianiense": "atletico go",
    "sport club do recife": "sport pe",
    "sport recife": "sport pe",
    "ceara sporting club": "ceara ce",
    "fortaleza esporte clube": "fortaleza ce",
    "ec bahia": "bahia ba",
    "esporte clube bahia": "bahia ba",
    "ec vitoria": "vitoria ba",
    "esporte clube vitoria": "vitoria ba",
    "vitoria": "vitoria ba",
    "vitoria fc": "vitoria ba",
    # Bare spellings of big clubs whose base name is also used by small
    # state clubs (Flamengo-PI, Santos-AP, Internacional-SC, ...): the bare
    # form always denotes the big club, so pin it to its home state.
    "flamengo": "flamengo rj",
    "fluminense": "fluminense rj",
    "santos": "santos sp",
    "internacional": "internacional rs",
    "juventude": "juventude rs",
    "nautico": "nautico pe",
    "santa cruz": "santa cruz pe",
    "portuguesa": "portuguesa sp",
    "botafogo": "botafogo rj",
    "guarani": "guarani sp",
    "penarol": "penarol uru",
    # Other big clubs that appear both with and without their state suffix:
    # pinning the bare form keeps the identity pair identical either way.
    "palmeiras": "palmeiras sp",
    "corinthians": "corinthians sp",
    "sao paulo": "sao paulo sp",
    "gremio": "gremio rs",
    "cruzeiro": "cruzeiro mg",
    "vasco": "vasco rj",
    "bahia": "bahia ba",
    "ceara": "ceara ce",
    "fortaleza": "fortaleza ce",
    "chapecoense": "chapecoense sc",
    "coritiba": "coritiba pr",
    "criciuma": "criciuma sc",
    "figueirense": "figueirense sc",
    "avai": "avai sc",
    "goias": "goias go",
    "sport": "sport pe",
    "parana": "parana pr",
    "ponte preta": "ponte preta sp",
    "joinville": "joinville sc",
    "csa": "csa al",
    "cuiaba": "cuiaba mt",
    # Renamed club: Bragantino became Red Bull Bragantino in 2019.
    "bragantino": "red bull bragantino",
    "bragantino sp": "red bull bragantino",
    # Libertadores spells Athletico-PR without any suffix.
    "athletico": "atletico pr",
    "america fc": "america mg",
    "america fc natal": "america rn",
    "america de natal": "america rn",
    "america rj": "america rj",
}

BASE_ALIASES = {
    "athletico": "atletico",
    "vasco da gama": "vasco",
    "america fc": "america",
}

PREFIX_TOKENS = frozenset({"se", "ec", "sc", "aa"})

_PAREN_RE = re.compile(r"\(([^)]*)\)")
_PUNCT_RE = re.compile(r"[^a-z0-9]+")
_SPACE_RE = re.compile(r"\s+")

_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
)
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")

_NOTHING = frozenset({"", "na", "n/a", "-", "none", "null", "?"})


def is_nothing(value) -> bool:
    """True for blank/missing CSV cells of any common flavour."""
    if value is None:
        return True
    return str(value).strip().lower() in _NOTHING


def strip_accents(value: str) -> str:
    """Fold accented characters down to their ASCII equivalents."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean_text(value) -> str:
    """Canonical comparison form for names: ASCII, lowercase, no punctuation.

    Parenthesised content is dropped unless it carries a state/country
    qualifier (e.g. "Nacional (URU)" keeps the "uru" token, while
    "Boavista Sport Club (antigo Esporte Clube Barreira)" loses it).
    """
    if value is None:
        return ""
    text = strip_accents(str(value)).strip().lower()
    if not text:
        return ""

    def _paren(match: re.Match) -> str:
        inner = _PUNCT_RE.sub(" ", match.group(1)).strip()
        if inner in PAREN_STATE_NAMES:
            return " " + PAREN_STATE_NAMES[inner]
        if inner in QUALIFIER_ABBRS:
            return " " + inner
        return " "

    text = _PAREN_RE.sub(_paren, text)
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _split_qualifier(text: str) -> tuple[str, str | None]:
    """Split a trailing state/country code off a cleaned name."""
    tokens = text.split(" ")
    if len(tokens) > 1 and tokens[-1] in QUALIFIER_ABBRS:
        return " ".join(tokens[:-1]), tokens[-1]
    return text, None


def split_team(name) -> tuple[str, str | None]:
    """Reduce a raw team/club spelling to a (base, qualifier) pair.

    "Palmeiras-SP" -> ("palmeiras", "sp"); "Palmeiras" -> ("palmeiras", None);
    "Atlético Paranaense" -> ("atletico", "pr"); "Botafogo-PB" ->
    ("botafogo", "pb"). The pair is stable across all six datasets so that
    equal pairs always denote the same real-world club.
    """
    cleaned = clean_text(name)
    if not cleaned:
        return "", None
    tokens = cleaned.split(" ")
    if len(tokens) > 1 and tokens[0] in PREFIX_TOKENS:
        cleaned = " ".join(tokens[1:])
    cleaned = FULL_NAME_ALIASES.get(cleaned, cleaned)
    base, qualifier = _split_qualifier(cleaned)
    base = BASE_ALIASES.get(base, base)
    return base, qualifier


def parse_date(value) -> tuple[date | None, str | None]:
    """Parse the date formats used across the datasets.

    Accepts "2012-05-19 18:30:00", "2023-09-24" and "29/03/2003".
    Returns (date, "HH:MM") with the time part missing when unknown.
    """
    if is_nothing(value):
        return None, None
    text = str(value).strip()
    for fmt in _DATETIME_FORMATS:
        try:
            stamp = datetime.strptime(text, fmt)
            return stamp.date(), stamp.strftime("%H:%M")
        except ValueError:
            continue
    for fmt in _DATE_FORMATS:
        try:
            stamp = datetime.strptime(text, fmt)
            return stamp.date(), None
        except ValueError:
            continue
    return None, None


def parse_int(value) -> int | None:
    """Parse goals/round numbers stored as int, float or numeric text."""
    if is_nothing(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
