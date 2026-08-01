"""Normalization helpers for Brazilian soccer data.

Handles the data-quality issues called out in the specification:

* Team name variations: ``"Palmeiras-SP"``, ``"América - MG"``,
  ``"Athletico-PR"``, ``"Vasco Da Gama RJ"`` and
  ``"Sport Club Corinthians Paulista"`` should all match consistently.
* Date formats: ISO (``"2023-09-24"``), Brazilian (``"29/03/2003"``) and
  ISO with time (``"2012-05-19 18:30:00"``).
* UTF-8 text with accents/cedilla: São Paulo, Grêmio, Avaí, Fortaleza.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

# Brazilian state codes plus common South-American country codes used as
# suffixes in the Libertadores dataset (e.g. "Barcelona-EQU", "Nacional-URU").
_STATE_CODES = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
    "arg", "bol", "chi", "col", "ecu", "equ", "mex", "par", "per", "uru", "ven",
}

_DASH_SUFFIX_RE = re.compile(r"\s*[-–]\s*([A-Za-z]{2,3})\s*$")
_SPACE_SUFFIX_RE = re.compile(r"\s+([A-Za-z]{2,3})\s*$")
_PARENS_RE = re.compile(r"\([^)]*\)")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Remove diacritics: ``"São Paulo"`` -> ``"Sao Paulo"``."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(text: object) -> str:
    """Lowercase, strip accents and parentheticals, collapse whitespace."""
    if text is None:
        return ""
    s = strip_accents(str(text))
    s = _PARENS_RE.sub(" ", s)
    s = s.replace("_", " ")
    return _WHITESPACE_RE.sub(" ", s).strip().lower()


def split_state_suffix(raw_name: object) -> tuple[str, str | None, bool]:
    """Split a raw team name into (normalized base, suffix, dash_form).

    Suffixes may be dash-separated (``"Palmeiras-SP"``, ``"América - MG"``)
    or space-separated (``"America MG"``, ``"Vasco Da Gama RJ"``,
    ``"Nacional (URU)"`` after parenthetical stripping) and are only
    considered when they are known state/country codes.
    """
    if raw_name is None:
        return "", None, False
    s = str(raw_name).strip()

    m = _DASH_SUFFIX_RE.search(s)
    if m and m.group(1).lower() in _STATE_CODES:
        return normalize_text(s[: m.start()]), m.group(1).lower(), True

    m = _SPACE_SUFFIX_RE.search(s)
    if m and m.group(1).lower() in _STATE_CODES and s[: m.start()].strip():
        return normalize_text(s[: m.start()]), m.group(1).lower(), False

    return normalize_text(s), None, False


# (base, state) -> canonical team key. Resolves ambiguous short names where
# the state suffix carries the disambiguating information.
_STATE_ALIASES: dict[tuple[str, str], str] = {
    ("athletico", "pr"): "athletico paranaense",
    ("atletico", "pr"): "athletico paranaense",
    ("atletico", "mg"): "atletico mineiro",
    ("atletico", "go"): "atletico goianiense",
    ("america", "mg"): "america mineiro",
    ("america", "rn"): "america rn",
    ("america", "rj"): "america rj",
    ("sport", "pe"): "sport recife",
    ("vitoria", "ba"): "vitoria",
    ("vitoria", "es"): "vitoria es",
    ("botafogo", "rj"): "botafogo",
    ("botafogo", "sp"): "botafogo sp",
    ("botafogo", "pb"): "botafogo pb",
    ("fluminense", "rj"): "fluminense",
    ("fluminense", "pi"): "fluminense pi",
    ("gremio", "rs"): "gremio",
    ("internacional", "rs"): "internacional",
    ("coritiba", "pr"): "coritiba",
    ("guarani", "sp"): "guarani",
    ("cuiaba", "mt"): "cuiaba",
    ("santo andre", "sp"): "santo andre",
    ("tombense", "mg"): "tombense",
    ("resende", "rj"): "resende",
    ("boavista", "rj"): "boavista",
    ("madureira", "rj"): "madureira",
    ("macae", "rj"): "macae",
    ("remo", "pa"): "remo",
    ("santa cruz", "pe"): "santa cruz",
    ("santa cruz", "rn"): "santa cruz rn",
    ("santa cruz", "rs"): "santa cruz rs",
    ("vasco", "rj"): "vasco",
    ("juventude", "rs"): "juventude",
    ("juventude", "ma"): "juventude ma",
    ("bragantino", "sp"): "bragantino",
    ("bragantino", "pa"): "bragantino pa",
    ("parana", "pr"): "parana",
    ("ceara", "ce"): "ceara",
    ("fortaleza", "ce"): "fortaleza",
    ("bahia", "ba"): "bahia",
    ("avai", "sc"): "avai",
    ("figueirense", "sc"): "figueirense",
    ("chapecoense", "sc"): "chapecoense",
    ("criciuma", "sc"): "criciuma",
    ("joinville", "sc"): "joinville",
    ("goias", "go"): "goias",
    ("vila nova", "go"): "vila nova",
    ("nautico", "pe"): "nautico",
    ("ponte preta", "sp"): "ponte preta",
    ("paysandu", "pa"): "paysandu",
    ("abc", "rn"): "abc",
    ("csa", "al"): "csa",
    ("crb", "al"): "crb",
    ("operario", "pr"): "operario pr",
    ("operario", "ms"): "operario ms",
    ("operario", "mt"): "operario mt",
    ("sao jose", "rs"): "sao jose rs",
    ("sao jose", "pa"): "sao jose pa",
    ("ypiranga", "rs"): "ypiranga rs",
    ("ypiranga", "ap"): "ypiranga ap",
    ("sampaio correa", "ma"): "sampaio correa",
    ("londrina", "pr"): "londrina",
    ("ituano", "sp"): "ituano",
    ("oeste", "sp"): "oeste",
    ("barcelona", "equ"): "barcelona sc",
    ("nacional", "uru"): "nacional",
    ("penarol", "uru"): "penarol",
    ("confianca", "se"): "confianca",
    ("ferroviario", "ce"): "ferroviario",
    ("ferroviaria", "sp"): "ferroviaria",
    ("atletico", "ac"): "atletico acreano",
    ("atletico", "es"): "atletico es",
    ("atletico", "ba"): "atletico alagoinhas",
    ("tupi", "mg"): "tupi",
    ("rio branco", "ac"): "rio branco ac",
    ("rio branco", "es"): "rio branco es",
    ("brasil", "rs"): "brasil de pelotas",
    ("independente", "pa"): "independente pa",
    ("asa", "al"): "asa",
    ("aparecidense", "go"): "aparecidense",
    ("afogados", "pe"): "afogados",
    ("audax", "sp"): "audax",
    ("moto club", "ma"): "moto club",
    ("anapolis", "go"): "anapolis",
    ("aimore", "rs"): "aimore",
    ("altos", "pi"): "altos",
    ("americano", "rj"): "americano",
    ("frei paulistano", "se"): "frei paulistano",
    ("caldense", "mg"): "caldense",
    ("cene", "ms"): "cene",
    ("nacional", "am"): "nacional am",
    ("penarol", "am"): "penarol am",
    ("uniclinic", "ce"): "uniclinic",
    ("urt", "mg"): "urt",
    ("vilhena", "ro"): "vilhena",
}

# bare-name aliases applied after state-aware lookup.
_ALIASES: dict[str, str] = {
    "athletico": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "ca paranaense": "athletico paranaense",
    "atletico mg": "atletico mineiro",
    "america mg": "america mineiro",
    "america fc natal": "america rn",
    "sport": "sport recife",
    "vasco da gama": "vasco",
    "ec bahia": "bahia",
    "ec vitoria": "vitoria",
    "ec juventude": "juventude",
    "fortaleza fc": "fortaleza",
    "fortaleza ec": "fortaleza",
    "nautico capibaribe": "nautico",
    "santa cruz fc": "santa cruz",
    "red bull bragantino": "bragantino",
    "portuguesa desportos": "portuguesa",
    "clube do remo": "remo",
    "macae esporte fc": "macae",
    "macae esporte": "macae",
    "madureira ec": "madureira",
    "boavista sport club": "boavista",
    "boavista sc saquarema": "boavista",
    "tombense mg": "tombense",
    "gremio fbpa": "gremio",
    "sc internacional": "internacional",
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "sao paulo fc": "sao paulo",
    "se palmeiras": "palmeiras",
    "inter": "internacional",
    "cr flamengo": "flamengo",
    "fluminense fc": "fluminense",
    "santos fc": "santos",
    "cr vasco da gama": "vasco",
    "4 de julho ec": "4 de julho",
    "iv de julho": "4 de julho",
    "afogados da ingazeira fc": "afogados",
    "ce aimore": "aimore",
    "ae altos": "altos",
    "audax sp": "audax",
    "anapolis fc": "anapolis",
    "moto club de sao luis": "moto club",
    "americano rj": "americano",
    "ad frei paulistano": "frei paulistano",
    "ad confianca": "confianca",
    "america de natal": "america rn",
    "campinense clube": "campinense",
    "duque de caxias fc": "duque de caxias",
    "globo fc": "globo",
    "nova mutum ec": "nova mutum",
    "retro fc brasil": "retro",
    "sinop fc": "sinop",
    "sousa ec": "sousa",
    "tocantinopolis ec": "tocantinopolis",
    "tuntum ec": "tuntum",
    "nova venecia fc": "nova venecia",
    "vilhenense ec": "vilhenense",
    "fc atletico cearense": "atletico cearense",
    "serra f. c.": "serra",
    "cordino ec": "cordino",
}


def canonical_team(raw_name: object) -> str:
    """Map any raw team name to a canonical lowercase accent-free key.

    Examples::

        canonical_team("Palmeiras-SP")          == "palmeiras"
        canonical_team("América - MG")          == "america mineiro"
        canonical_team("Athletico-PR")          == "athletico paranaense"
        canonical_team("Vasco Da Gama RJ")      == "vasco"
        canonical_team("São Paulo")             == "sao paulo"

    Dash-form suffixes always reduce to the base name (they are systematic
    in the Kaggle match files). Space-form suffixes only reduce when an
    explicit alias is known — otherwise the suffix is kept so distinct
    clubs (Rio Branco-AC vs Rio Branco-ES) never merge by accident.
    """
    base, suffix, dash_form = split_state_suffix(raw_name)
    if not base:
        return ""
    if suffix is not None:
        if (base, suffix) in _STATE_ALIASES:
            return _STATE_ALIASES[(base, suffix)]
        if base in _ALIASES:
            return _ALIASES[base]
        if dash_form:
            return base
        return f"{base} {suffix}"
    return _ALIASES.get(base, base)


# Preferred display names for the most common canonical keys (accents
# restored). Anything not listed falls back to the most frequent raw form
# seen in the data, or title-case.
DISPLAY_OVERRIDES: dict[str, str] = {
    "athletico paranaense": "Athletico Paranaense",
    "atletico mineiro": "Atlético Mineiro",
    "atletico goianiense": "Atlético Goianiense",
    "america mineiro": "América Mineiro",
    "america rn": "América-RN",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "vasco": "Vasco da Gama",
    "botafogo": "Botafogo",
    "bragantino": "Red Bull Bragantino",
    "sport recife": "Sport Recife",
    "cuiaba": "Cuiabá",
    "goias": "Goiás",
    "vitoria": "Vitória",
    "vitoria es": "Vitória-ES",
    "ceara": "Ceará",
    "avai": "Avaí",
    "criciuma": "Criciúma",
    "nautico": "Náutico",
    "sampaio correa": "Sampaio Corrêa",
    "coritiba": "Coritiba",
    "chapecoense": "Chapecoense",
    "figueirense": "Figueirense",
    "parana": "Paraná",
    "ponte preta": "Ponte Preta",
    "atletico": "Atlético",
    "barcelona sc": "Barcelona SC",
    "penarol": "Peñarol",
    "sao jose rs": "São José-RS",
}


# ---------------------------------------------------------------------------
# Competitions
# ---------------------------------------------------------------------------

COMPETITIONS: dict[str, dict[str, object]] = {
    "serie a": {
        "display": "Brasileirão Série A",
        "synonyms": ["serie a", "brasileirao", "brasileirao serie a",
                     "campeonato brasileiro", "brazilian serie a"],
    },
    "serie b": {
        "display": "Brasileirão Série B",
        "synonyms": ["serie b", "brasileirao serie b"],
    },
    "serie c": {
        "display": "Brasileirão Série C",
        "synonyms": ["serie c", "brasileirao serie c"],
    },
    "copa do brasil": {
        "display": "Copa do Brasil",
        "synonyms": ["copa do brasil", "brazilian cup", "copabd"],
    },
    "copa libertadores": {
        "display": "Copa Libertadores",
        "synonyms": ["copa libertadores", "libertadores",
                     "conmebol libertadores"],
    },
}


def canonical_competition(text: object) -> str | None:
    """Map a free-text competition name to a canonical key (or ``None``)."""
    norm = normalize_text(text)
    if not norm:
        return None
    for key, info in COMPETITIONS.items():
        synonyms = info["synonyms"]
        if norm == key or norm in synonyms:
            return key
    # substring fallback: "copa do brasil 2023" -> "copa do brasil"
    for key, info in COMPETITIONS.items():
        if key in norm:
            return key
    return None


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%Y/%m/%d",
)


def parse_date(value: object) -> datetime | None:
    """Parse ISO, ISO-with-time and Brazilian (DD/MM/YYYY) date formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s or s.lower() in {"nan", "nat", "none"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_user_date(text: object) -> datetime | None:
    """Parse user-supplied dates: ``YYYY``, ``YYYY-MM-DD`` or ``DD/MM/YYYY``."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}", s):
        return datetime(int(s), 1, 1)
    return parse_date(s)


# ---------------------------------------------------------------------------
# Derbies
# ---------------------------------------------------------------------------

DERBIES: dict[frozenset[str], str] = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"flamengo", "vasco"}): "Clássico dos Milhões",
    frozenset({"flamengo", "botafogo"}): "Clássico da Rivalidade",
    frozenset({"fluminense", "botafogo"}): "Clássico Vovô",
    frozenset({"fluminense", "vasco"}): "Clássico dos Gigantes",
    frozenset({"botafogo", "vasco"}): "Clássico da Amizade",
    frozenset({"palmeiras", "corinthians"}): "Derby Paulista",
    frozenset({"corinthians", "sao paulo"}): "Majestoso",
    frozenset({"palmeiras", "sao paulo"}): "Choque-Rei",
    frozenset({"santos", "sao paulo"}): "San-São",
    frozenset({"corinthians", "santos"}): "Clássico Alvinegro",
    frozenset({"palmeiras", "santos"}): "Clássico da Saudade",
    frozenset({"gremio", "internacional"}): "Gre-Nal",
    frozenset({"atletico mineiro", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"america mineiro", "atletico mineiro"}): "Clássico das Multidões (MG)",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"fortaleza", "ceara"}): "Clássico-Rei",
    frozenset({"remo", "paysandu"}): "Re-Pa",
    frozenset({"athletico paranaense", "coritiba"}): "Atle-Tiba",
    frozenset({"goias", "vila nova"}): "Clássico do Equilíbrio",
    frozenset({"santa cruz", "nautico"}): "Clássico dos Clássicos",
    frozenset({"sport recife", "santa cruz"}): "Clássico das Multidões (PE)",
    frozenset({"sport recife", "nautico"}): "Clássico dos Aflitos",
    frozenset({"abc", "america rn"}): "Rei do RN",
}


def derby_name(home_key: str, away_key: str) -> str | None:
    """Return the derby name for a fixture, or ``None`` if not a derby."""
    return DERBIES.get(frozenset({home_key, away_key}))
