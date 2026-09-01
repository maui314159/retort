"""Name, date and competition normalisation for the Brazilian Soccer MCP server.

The five match datasets and the FIFA player dataset spell the same club in
many different ways ("Palmeiras-SP", "Palmeiras", "Palmeiras - SP",
"Sociedade Esportiva Palmeiras", "SE Palmeiras").  This module maps every
variant onto a single *canonical id* so that queries, head-to-head records
and standings aggregate correctly across files.

Canonical ids are lowercase, accent-stripped identifiers such as
``flamengo``, ``athletico-pr`` or ``botafogo-rj``.  A curated alias table
covers the major clubs and every spelling found in the provided datasets;
anything not in the table falls back to a rule-based normaliser (strip
accents/punctuation, detect trailing state or country tags).

The module also parses the three date formats present in the data
(ISO, ISO+time, Brazilian DD/MM/YYYY) and normalises competition names.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

#: Brazilian state abbreviations (UFs) used as team-name suffixes.
BRAZILIAN_STATES = frozenset(
    """AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS
    SC SE SP TO""".split()
)

#: South/Latin-American country tags seen in the Libertadores dataset.
COUNTRY_TAGS = frozenset(
    """URU PAR EQU PER VEN ARG BOL CHI COL MEX ECU""".split()
)

#: Club-legal-form tokens stripped from generic names (e.g. "EC Bahia").
CLUB_FORM_TOKENS = frozenset("ec fc sc ac ca cb aa sd".split())

#: Base names that exist for several distinct clubs: keep the state suffix.
AMBIGUOUS_BASES = frozenset(
    {
        "botafogo",
        "america",
        "vitoria",
        "santos",
        "atletico",
        "nacional",
        "guarani",
        "river plate",
        "internacional",
        "gremio",
        "csa",
        "parana",
    }
)

#: Resolution for ambiguous bases appearing without a state suffix.
BARE_DEFAULTS = {
    "botafogo": "botafogo-rj",
    "america": "america-mg",
    "vitoria": "vitoria-ba",
    "santos": "santos",
    "internacional": "internacional",
    "gremio": "gremio",
    "csa": "csa",
    "parana": "parana",
    "river plate": "river plate",
    "guarani": "guarani",
    "atletico": "atletico-mg",
    "nacional": "nacional",
}

#: canonical id -> pretty display name.
CLUB_DISPLAY: dict[str, str] = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "vasco": "Vasco da Gama",
    "botafogo-rj": "Botafogo",
    "corinthians": "Corinthians",
    "palmeiras": "Palmeiras",
    "sao-paulo": "São Paulo",
    "santos": "Santos",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "cruzeiro": "Cruzeiro",
    "atletico-mg": "Atlético Mineiro",
    "athletico-pr": "Athletico Paranaense",
    "atletico-go": "Atlético Goianiense",
    "america-mg": "América Mineiro",
    "america-rn": "América RN",
    "bahia": "Bahia",
    "vitoria-ba": "Vitória",
    "vitoria-es": "Vitória ES",
    "sport": "Sport Recife",
    "ceara": "Ceará",
    "fortaleza": "Fortaleza",
    "goias": "Goiás",
    "coritiba": "Coritiba",
    "parana": "Paraná",
    "chapecoense": "Chapecoense",
    "criciuma": "Criciúma",
    "avai": "Avaí",
    "figueirense": "Figueirense",
    "juventude": "Juventude",
    "nautico": "Náutico",
    "csa": "CSA",
    "cuiaba": "Cuiabá",
    "bragantino": "Red Bull Bragantino",
    "portuguesa": "Portuguesa",
    "joinville": "Joinville",
    "guarani": "Guarani",
    "paysandu": "Paysandu",
    "remo": "Remo",
    "crb": "CRB",
    "criciuma-sc": "Criciúma",
    "athletico": "Athletico Paranaense",
    "nacional-uru": "Nacional (URU)",
    "nacional-par": "Nacional (PAR)",
    "river plate": "River Plate (ARG)",
    "river plate-uru": "River Plate (URU)",
    "barcelona-equ": "Barcelona (EQU)",
    "guarani-par": "Guaraní (PAR)",
    "bolivar": "Bolívar",
    "penarol": "Peñarol",
    "saopaulo": "São Paulo",
}

#: Explicit aliases: normalised spelling -> canonical id.  Every variant of
#: the major clubs found across the six datasets is listed here.
CLUB_ALIASES: dict[str, str] = {
    # Rio de Janeiro
    "flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "clube de regatas do flamengo": "flamengo",
    "fluminense": "fluminense",
    "fluminense rj": "fluminense",
    "vasco": "vasco",
    "vasco rj": "vasco",
    "vasco da gama": "vasco",
    "vasco da gama rj": "vasco",
    "botafogo": "botafogo-rj",
    "botafogo rj": "botafogo-rj",
    "botafogo pb": "botafogo-pb",
    "botafogo sp": "botafogo-sp",
    # São Paulo
    "corinthians": "corinthians",
    "corinthians sp": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "palmeiras": "palmeiras",
    "palmeiras sp": "palmeiras",
    "sociedade esportiva palmeiras": "palmeiras",
    "se palmeiras": "palmeiras",
    "sao paulo": "sao-paulo",
    "sao paulo sp": "sao-paulo",
    "sao paulo fc": "sao-paulo",
    "saopaulo": "sao-paulo",
    "santos": "santos",
    "santos sp": "santos",
    "santos fc": "santos",
    "santos ap": "santos-ap",
    "portuguesa": "portuguesa",
    "portuguesa sp": "portuguesa",
    "bragantino": "bragantino",
    "bragantino sp": "bragantino",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "guarani sp": "guarani",
    # Minas Gerais
    "cruzeiro": "cruzeiro",
    "cruzeiro mg": "cruzeiro",
    "cruzeiro ec": "cruzeiro",
    "atletico mineiro": "atletico-mg",
    "atletico mg": "atletico-mg",
    "clube atletico mineiro": "atletico-mg",
    "america fc minas gerais": "america-mg",
    "america mg": "america-mg",
    "america fc": "america-mg",
    # Paraná
    "athletico paranaense": "athletico-pr",
    "atletico paranaense": "athletico-pr",
    "athletico pr": "athletico-pr",
    "atletico pr": "athletico-pr",
    "athletico": "athletico-pr",
    "atletico goianiense": "atletico-go",
    "atletico go": "atletico-go",
    "coritiba": "coritiba",
    "coritiba pr": "coritiba",
    "parana": "parana",
    "parana clube": "parana",
    # Rio Grande do Sul
    "gremio": "gremio",
    "gremio rs": "gremio",
    "internacional": "internacional",
    "internacional rs": "internacional",
    "sc internacional": "internacional",
    "internacional sm": "internacional",
    "juventude": "juventude",
    "juventude rs": "juventude",
    # Bahia / Northeast
    "bahia": "bahia",
    "bahia ba": "bahia",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "vitoria": "vitoria-ba",
    "vitoria ba": "vitoria-ba",
    "vitoria ec": "vitoria-ba",
    "ec vitoria": "vitoria-ba",
    "vitoria es": "vitoria-es",
    "sport": "sport",
    "sport recife": "sport",
    "sport pe": "sport",
    "sport club do recife": "sport",
    "sport club recife": "sport",
    "ceara": "ceara",
    "ceara ce": "ceara",
    "ceara sporting club": "ceara",
    "fortaleza": "fortaleza",
    "fortaleza ce": "fortaleza",
    "fortaleza fc": "fortaleza",
    "nautico": "nautico",
    "nautico pe": "nautico",
    "csa": "csa",
    "csa al": "csa",
    "csa alagoas": "csa",
    # Centro-Oeste / North
    "goias": "goias",
    "goias go": "goias",
    "goias ec": "goias",
    "cuiaba": "cuiaba",
    "cuiaba mt": "cuiaba",
    "cuiaba ec": "cuiaba",
    # Santa Catarina
    "chapecoense": "chapecoense",
    "chapecoense sc": "chapecoense",
    "criciuma": "criciuma",
    "criciuma sc": "criciuma",
    "avai": "avai",
    "avai sc": "avai",
    "figueirense": "figueirense",
    "figueirense sc": "figueirense",
    "joinville": "joinville",
    "joinville sc": "joinville",
    # Libertadores foreign clubs (tags kept for disambiguation)
    "nacional uru": "nacional-uru",
    "nacional par": "nacional-par",
    "river plate uru": "river plate-uru",
    "barcelona equ": "barcelona-equ",
    "guarani par": "guarani-par",
    "libertad par": "libertad",
    "olimpia par": "olimpia",
    "delfin equ": "delfin",
    "delfin": "delfin",
    "deportes tolima": "tolima",
    "universitario per": "universitario",
}

#: Inverse structure used for lookups by canonical id.
ALIAS_TO_CANONICAL: dict[str, str] = dict(CLUB_ALIASES)


def strip_accents(text: str) -> str:
    """Remove diacritics (São Paulo -> Sao Paulo)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _clean(text: str) -> str:
    """Lowercase, strip accents and collapse punctuation to single spaces.

    Dots are removed outright so dotted abbreviations like "A.b.c." survive as
    "abc" rather than being blown apart into single letters.
    """
    flat = strip_accents(text).casefold()
    flat = flat.replace(".", "")
    flat = re.sub(r"[^a-z0-9]+", " ", flat)
    return " ".join(flat.split())


def _split_tag(tokens: list[str]) -> tuple[list[str], Optional[str]]:
    """Split a trailing state/country tag off the token list, if present."""
    if len(tokens) >= 2:
        last = tokens[-1]
        if len(last) == 3 and last.upper() in COUNTRY_TAGS:
            return tokens[:-1], last
        if len(last) == 2 and last.upper() in BRAZILIAN_STATES:
            return tokens[:-1], last
    return tokens, None


def normalize_team_id(raw: str) -> str:
    """Return the canonical team id for any spelling of a club name.

    Resolution order:
    1. Full-string alias lookup, keeping parenthetical words (covers the
       FIFA dataset's "América FC (Minas Gerais)" and Libertadores'
       "Nacional (URU)").
    2. Same lookup after dropping parenthetical content (covers noise such
       as "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ").
    3. Split off a trailing state/country tag:
       - ambiguous bases (botafogo, america, vitoria, ...) keep the tag;
       - unambiguous bases drop it ("Palmeiras-SP" -> "palmeiras").
    4. Strip trailing club-legal-form tokens ("EC Bahia" -> "bahia").
    """
    if not raw:
        return ""
    cleaned = _clean(raw)
    if not cleaned:
        return ""
    if cleaned in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[cleaned]

    no_parens = _clean(re.sub(r"\([^)]*\)", " ", raw))
    if no_parens and no_parens != cleaned:
        if no_parens in ALIAS_TO_CANONICAL:
            return ALIAS_TO_CANONICAL[no_parens]

    tokens = (no_parens or cleaned).split()
    base_tokens, tag = _split_tag(tokens)
    base = " ".join(base_tokens)

    if base in AMBIGUOUS_BASES:
        if tag:
            return f"{base}-{tag}"
        return BARE_DEFAULTS.get(base, base)

    if base in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[base]

    if tag and base:
        return base

    trimmed = [t for t in base_tokens if t not in CLUB_FORM_TOKENS]
    if trimmed and trimmed != base_tokens:
        return normalize_team_id(" ".join(trimmed))
    return base


def team_display_name(canonical_id: str) -> str:
    """Pretty display name for a canonical id (accents restored)."""
    if not canonical_id:
        return ""
    if canonical_id in CLUB_DISPLAY:
        return CLUB_DISPLAY[canonical_id]
    if "-" in canonical_id:
        base, _, suffix = canonical_id.rpartition("-")
        if len(suffix) == 2 and suffix.upper() in BRAZILIAN_STATES | COUNTRY_TAGS:
            return f"{team_display_name(base)}-{suffix.upper()}"
    return canonical_id.title()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M",
    "%H:%M:%S",
)


def parse_date(raw: str) -> Optional[date]:
    """Parse the date formats present in the datasets.

    Handles ISO dates ("2023-09-24"), ISO datetimes ("2012-05-19 18:30:00")
    and Brazilian format ("29/03/2003").  Returns None for blank/NA values.
    """
    parsed = parse_datetime(raw)
    return parsed.date() if parsed else None


def parse_datetime(raw: str) -> Optional[datetime]:
    """Parse a dataset timestamp into a datetime, keeping the time part."""
    if not raw:
        return None
    text = raw.strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Competition normalisation
# ---------------------------------------------------------------------------

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

#: Raw tournament label -> canonical competition name.
COMPETITION_ALIASES: dict[str, str] = {
    "serie a": SERIE_A,
    "serie b": SERIE_B,
    "serie c": SERIE_C,
    "brasileirao": SERIE_A,
    "brasileirao serie a": SERIE_A,
    "campeonato brasileiro": SERIE_A,
    "brasileirão série a": SERIE_A,
    "série a": SERIE_A,
    "serie b nacional": SERIE_B,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "copa libertadores da america": LIBERTADORES,
    "conmebol libertadores": LIBERTADORES,
}

KNOWN_COMPETITIONS = [SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES]


def normalize_competition(raw: Optional[str]) -> Optional[str]:
    """Map a user-supplied or dataset competition label to canonical name."""
    if not raw:
        return None
    cleaned = _clean(raw)
    return COMPETITION_ALIASES.get(cleaned, raw.strip())


# ---------------------------------------------------------------------------
# Derby knowledge base (traditional rivalries)
# ---------------------------------------------------------------------------

DERBIES: list[dict[str, str]] = [
    {"name": "Fla-Flu", "team_a": "flamengo", "team_b": "fluminense"},
    {"name": "Clássico Vovô", "team_a": "botafogo-rj", "team_b": "fluminense"},
    {"name": "Clássico da Amizade", "team_a": "flamengo", "team_b": "vasco"},
    {"name": "Clássico dos Milhões", "team_a": "flamengo", "team_b": "vasco"},
    {"name": "Derby Paulista", "team_a": "palmeiras", "team_b": "corinthians"},
    {"name": "Majestoso", "team_a": "sao-paulo", "team_b": "corinthians"},
    {"name": "Choque-Rei", "team_a": "palmeiras", "team_b": "sao-paulo"},
    {"name": "Grenal", "team_a": "gremio", "team_b": "internacional"},
    {"name": "Clássico Mineiro", "team_a": "atletico-mg", "team_b": "cruzeiro"},
    {"name": "Ba-Vi", "team_a": "bahia", "team_b": "vitoria-ba"},
    {"name": "Clássico dos Gigantes", "team_a": "vasco", "team_b": "botafogo-rj"},
    {"name": "Clássico Rei do Norte", "team_a": "sport", "team_b": "csa"},
]
