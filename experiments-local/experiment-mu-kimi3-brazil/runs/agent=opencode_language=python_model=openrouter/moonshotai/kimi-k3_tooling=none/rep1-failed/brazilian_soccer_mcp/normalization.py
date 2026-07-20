"""Team-name normalization for the Brazilian soccer datasets.

Why: the six CSV sources spell the same club in different ways
("Palmeiras-SP", "Palmeiras", "Sport", "Sport-PE", "Sport Club do
Recife"), so every raw name is mapped to a canonical key before
matching, grouping or aggregating. Naively stripping state suffixes is
not enough: "Atletico-MG", "Atletico-GO" and "Atletico-PR" are three
*different* clubs.

What: `normalize_team` folds accents, lowercases, drops punctuation and
parentheticals, applies a curated alias table for the well-known clubs,
and strips a trailing state/country code only when the remaining base
name is unambiguous. `display_team` renders a canonical key back to a
human-friendly name.
"""

from __future__ import annotations

import re
import unicodedata

# Brazilian state codes plus the country suffixes used in the
# Libertadores file (e.g. "Barcelona-EQU", "Nacional (URU)"), plus the
# generic club-suffix tokens "EC"/"FC" (Esporte Clube / Futebol Clube)
# so that "4 de Julho EC" and "4 de Julho" unify.
_STATE_CODES = frozenset(
    """
    ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to
    uru equ ecu par chi arg col per ven bol mex usa bra por esp
    ec fc
    """.split()
)

_PARENS_RE = re.compile(r"\(([^)]*)\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_SPACES_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (São -> Sao, Grêmio -> Gremio)."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _parens_sub(match: re.Match[str]) -> str:
    """Keep parenthetical content only when it is a state/country code.

    "Nacional (URU)" keeps the "uru" token (it disambiguates the club),
    while "Boavista Sport Club (antigo Esporte Clube Barreira)" drops it.
    """
    content = _SPACES_RE.sub(" ", strip_accents(match.group(1)).lower()).strip()
    if content in _STATE_CODES:
        return f" {content} "
    return " "


def _base_normalize(name: object) -> str:
    """Accent-fold, lowercase, drop parentheticals and punctuation."""
    n = strip_accents(str(name)).lower()
    n = _PARENS_RE.sub(_parens_sub, n)
    n = _NON_ALNUM_RE.sub(" ", n)  # dashes -> spaces, dots dropped
    return _SPACES_RE.sub(" ", n).strip()


# Base names shared by two or more distinct clubs in the data. A
# trailing state code is never stripped from these unless the full form
# is explicitly aliased (e.g. "atletico mg" -> "atletico mineiro").
_PROTECTED_BASES = frozenset(
    [
        "america",
        "atletico",
        "athletico",
        "botafogo",
        "bragantino",
        "central",
        "comercial",
        "flamengo",
        "fluminense",
        "guarani",
        "internacional",
        "juventude",
        "nacional",
        "nautico",
        "operario",
        "penarol",
        "portuguesa",
        "rio branco",
        "river",
        "river plate",
        "santa cruz",
        "santos",
        "sao francisco",
        "sao jose",
        "sao raimundo",
        "vitoria",
        "ypiranga",
    ]
)

# Curated aliases: normalized raw form -> canonical key.
_ALIASES: dict[str, str] = {
    # --- Atlético family ---
    "atletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "atletico mineiro mg": "atletico mineiro",
    "atletico go": "atletico goianiense",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "atletico paranaense pr": "athletico paranaense",
    "athletico paranaense pr": "athletico paranaense",
    # --- América family ---
    "america mg": "america mineiro",
    "america rn": "america de natal",
    "america fc natal": "america de natal",
    # --- majors with state suffixes ---
    "flamengo rj": "flamengo",
    "fluminense rj": "fluminense",
    "botafogo rj": "botafogo",
    "vasco da gama rj": "vasco da gama",
    "vasco": "vasco da gama",
    "sao paulo sp": "sao paulo",
    "santos sp": "santos",
    "palmeiras sp": "palmeiras",
    "corinthians sp": "corinthians",
    "gremio rs": "gremio",
    "internacional rs": "internacional",
    "cruzeiro mg": "cruzeiro",
    "bahia ba": "bahia",
    "ec bahia": "bahia",
    "vitoria ba": "vitoria",
    "ec vitoria": "vitoria",
    "vitoria ec": "vitoria",
    "goias go": "goias",
    "ceara ce": "ceara",
    "ceara sporting club": "ceara",
    "fortaleza ce": "fortaleza",
    "fortaleza ec": "fortaleza",
    "fortaleza fc": "fortaleza",
    "avai sc": "avai",
    "chapecoense sc": "chapecoense",
    "figueirense sc": "figueirense",
    "coritiba pr": "coritiba",
    "criciuma sc": "criciuma",
    "cuiaba mt": "cuiaba",
    "csa al": "csa",
    "joinville sc": "joinville",
    "juventude rs": "juventude",
    "ec juventude": "juventude",
    "parana pr": "parana",
    "ponte preta sp": "ponte preta",
    "portuguesa sp": "portuguesa",
    "portuguesa desportos": "portuguesa",
    "guarani sp": "guarani",
    "santo andre sp": "santo andre",
    "sao caetano sp": "sao caetano",
    "paysandu pa": "paysandu",
    "remo pa": "remo",
    "nautico pe": "nautico",
    "nautico capibaribe": "nautico",
    "santa cruz pe": "santa cruz",
    "santa cruz fc": "santa cruz",
    "sport": "sport recife",
    "sport pe": "sport recife",
    "sport club do recife": "sport recife",
    "bragantino": "red bull bragantino",
    "bragantino sp": "red bull bragantino",
    "red bull bragantino sp": "red bull bragantino",
    # --- same club, distinct spelling ---
    "boavista sc saquarema": "boavista",
    "boavista sport club": "boavista",
    "athletic club mg": "athletic club",
    "ec internacional sc": "internacional sc",
}

# Pretty display names for the most relevant canonical keys.
# Anything not listed falls back to title-casing the canonical key.
_DISPLAY: dict[str, str] = {
    "america de natal": "América de Natal",
    "america mineiro": "América Mineiro",
    "athletico paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense",
    "atletico mineiro": "Atlético Mineiro",
    "avai": "Avaí",
    "bahia": "Bahia",
    "botafogo": "Botafogo",
    "brasil de pelotas": "Brasil de Pelotas",
    "ceara": "Ceará",
    "chapecoense": "Chapecoense",
    "corinthians": "Corinthians",
    "coritiba": "Coritiba",
    "criciuma": "Criciúma",
    "cruzeiro": "Cruzeiro",
    "csa": "CSA",
    "cuiaba": "Cuiabá",
    "figueirense": "Figueirense",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "fortaleza": "Fortaleza",
    "goias": "Goiás",
    "gremio": "Grêmio",
    "gremio prudente": "Grêmio Prudente",
    "guarani": "Guarani",
    "internacional": "Internacional",
    "joinville": "Joinville",
    "juventude": "Juventude",
    "nautico": "Náutico",
    "palmeiras": "Palmeiras",
    "parana": "Paraná",
    "paysandu": "Paysandu",
    "ponte preta": "Ponte Preta",
    "portuguesa": "Portuguesa",
    "red bull bragantino": "Red Bull Bragantino",
    "remo": "Remo",
    "santa cruz": "Santa Cruz",
    "santo andre": "Santo André",
    "santos": "Santos",
    "sao caetano": "São Caetano",
    "sao paulo": "São Paulo",
    "sport recife": "Sport Recife",
    "vasco da gama": "Vasco da Gama",
    "vitoria": "Vitória",
}

_UPPER_WORDS = {"csa", "crb", "abc", "asa", "urt"}


def normalize_team(name: object) -> str:
    """Map any raw team spelling to its canonical key.

    Rules, in order:
    1. accent-fold + lowercase + drop parentheticals/punctuation
    2. exact alias hit on the full normalized form
    3. strip a trailing state/country code, unless the base name is
       shared by several distinct clubs (protected base)
    4. the (possibly suffix-stripped) normalized form itself
    """
    n = _base_normalize(name)
    if not n:
        return ""
    if n in _ALIASES:
        return _ALIASES[n]
    tokens = n.split()
    if len(tokens) > 1 and tokens[-1] in _STATE_CODES:
        base = " ".join(tokens[:-1])
        if base in _PROTECTED_BASES:
            return n
        if base in _ALIASES:
            return _ALIASES[base]
        return base
    return n


def display_team(canonical: str) -> str:
    """Render a canonical key as a human-friendly team name."""
    if canonical in _DISPLAY:
        return _DISPLAY[canonical]
    words = []
    for word in canonical.split():
        if word in _UPPER_WORDS:
            words.append(word.upper())
        else:
            words.append(word.capitalize())
    return " ".join(words)


def teams_equal(a: object, b: object) -> bool:
    """True when two raw/queried spellings refer to the same club."""
    na, nb = normalize_team(a), normalize_team(b)
    return bool(na) and na == nb
