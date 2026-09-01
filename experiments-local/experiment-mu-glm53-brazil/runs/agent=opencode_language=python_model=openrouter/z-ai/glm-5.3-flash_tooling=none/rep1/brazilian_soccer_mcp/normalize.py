"""Text, team-name, and date normalization for Brazilian soccer datasets."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Generic text helpers
# ---------------------------------------------------------------------------


def strip_accents(text: str) -> str:
    """Remove diacritics: "São Paulo" -> "sao paulo" (after lowercasing)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def text_key(text: str) -> str:
    """Case/diacritic/punctuation-insensitive lookup key.

    "Atlético - PR" -> "atletico pr"; "Nacional (URU)" -> "nacional uru".
    """
    lowered = strip_accents(collapse_ws(text)).lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------

# Brazilian state abbreviations used as "-SP" style suffixes, and the
# country codes used in the Libertadores dataset ("Nacional (URU)").
_STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}
_COUNTRY_CODES = {
    "URU", "ARG", "PAR", "EQU", "BOL", "CHI", "COL", "PER", "VEN", "CRC",
    "HON", "GUA", "PAN", "MEX", "USA",
}
_SUFFIX_CODES = _STATE_CODES | _COUNTRY_CODES

_SUFFIX_RE = re.compile(
    r"^(?P<base>.+?)\s*[-–(]+\s*(?P<code>[A-Za-z]{2,3})\s*\)?$", re.UNICODE
)

# alias key (accent-stripped, lowercased, punctuation-as-space) -> canonical
# display name. Keys must therefore themselves be suffix-free.
_TEAM_ALIASES = {
    # Big clubs (state-suffix collisions need explicit entries)
    "america mg": "América Mineiro",
    "america mineiro": "América Mineiro",
    "america fc minas gerais": "América Mineiro",
    "america rn": "América de Natal",
    "america natal": "América de Natal",
    "america de natal": "América de Natal",
    "america football club natal": "América de Natal",
    "america de cali": "América de Cali",
    "atletico mg": "Atlético Mineiro",
    "atletico mineiro": "Atlético Mineiro",
    "clube atletico mineiro": "Atlético Mineiro",
    "atletico pr": "Athletico Paranaense",
    "atletico paranaense": "Athletico Paranaense",
    "athletico pr": "Athletico Paranaense",
    "athletico paranaense": "Athletico Paranaense",
    "athletico": "Athletico Paranaense",
    "atletico go": "Atlético Goianiense",
    "atletico goianiense": "Atlético Goianiense",
    "atletico goianiense go": "Atlético Goianiense",
    "atletico nacional": "Atlético Nacional",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "club de regatas vasco da gama": "Vasco da Gama",
    "sao paulo": "São Paulo",
    "sao paulo fc": "São Paulo",
    "sao paulo futebol clube": "São Paulo",
    "sport": "Sport Recife",
    "sport club do recife": "Sport Recife",
    "sport recife": "Sport Recife",
    "red bull bragantino": "Red Bull Bragantino",
    "bragantino": "Red Bull Bragantino",
    "red bull brasil": "Red Bull Bragantino",
    "gremio prudente": "Grêmio Prudente",
    "santo andre": "Santo André",
    "sao caetano": "São Caetano",
    "parana": "Paraná",
    "parana clube": "Paraná",
    "cuiaba": "Cuiabá",
    "cuiaba esporte clube": "Cuiabá",
    "csa": "CSA",
    "centro sportivo alagoano": "CSA",
    "asa": "ASA",
    "asa al": "ASA",
    "boavista": "Boavista",
    "boavista rj": "Boavista",
    "boavista sc saquarema": "Boavista",
    "chapecoense": "Chapecoense",
    "atletico de capelense": "Atlético Capelense",
    "abc": "ABC",
    "abc rn": "ABC",
    "a s a": "ASA",
    "aguia negra": "Águia Negra",
    "aimore": "Aimoré",
    "avai": "Avaí",
    "ceara": "Ceará",
    "ceara sporting club": "Ceará",
    "criciuma": "Criciúma",
    "goias": "Goiás",
    "nautico": "Náutico",
    "vitoria": "Vitória",
    "juventude": "Juventude",
    "figueirense": "Figueirense",
    "joinville": "Joinville",
    "ponte preta": "Ponte Preta",
    "portuguesa": "Portuguesa",
    "santa cruz": "Santa Cruz",
    "paysandu": "Paysandu",
    "guarani": "Guarani",
    "ipatinga": "Ipatinga",
    "brasiliense": "Brasiliense",
    "barueri": "Barueri",
    "gremio barueri": "Barueri",
    "fortaleza": "Fortaleza",
    "fortaleza esporte clube": "Fortaleza",
    # Space-suffixed variants from BR-Football-Dataset that must not be
    # confused with their more famous namesakes.
    "botafogo rj": "Botafogo",
    "botafogo pb": "Botafogo-PB",
    "botafogo sp": "Botafogo-SP",
    "fluminense rj": "Fluminense",
    "fluminense pi": "Fluminense-PI",
    "santos ap": "Santos-AP",
    "santa cruz rn": "Santa Cruz-RN",
    "santa cruz rs": "Santa Cruz-RS",
    "vitoria es": "Vitória-ES",
    "nautico rr": "Náutico-RR",
    "juventude ma": "Juventude-MA",
    "americano rj": "Americano",
    "cuiaba mt": "Cuiabá",
    "coritiba pr": "Coritiba",
    "gremio rs": "Grêmio",
    "internacional rs": "Internacional",
    "caxias rs": "Caxias",
    "guarani sp": "Guarani",
    "audax sp": "Audax",
    "vasco da gama rj": "Vasco da Gama",
    "nacional am": "Nacional-AM",
    "bragantino pa": "Bragantino-PA",
    "ldu": "LDU Quito",
    "ldu quito": "LDU Quito",
    "ind santa fe": "Independiente Santa Fe",
    "independiente santa fe": "Independiente Santa Fe",
    "independiente del valle": "Independiente Del Valle",
    "independiente medellin": "Independiente Medellín",
    "atletico tucuman": "Atlético Tucumán",
    "estudiantes de merida": "Estudiantes de Mérida",
    "deportes tolima": "Deportes Tolima",
    "junior de barranquilla": "Junior",
    "junior": "Junior",
    "cerro porteno": "Cerro Porteño",
    "guarani par": "Guaraní",
    "guarani asuncion": "Guaraní",
    "club guarani": "Guaraní",
    "defensor sporting": "Defensor Sporting",
    "jorge wilstermann": "Jorge Wilstermann",
    "colo colo": "Colo-Colo",
    "barcelona equ": "Barcelona SC",
    "barcelona sc": "Barcelona SC",
    "barcelona ecuador": "Barcelona SC",
    "delfin": "Delfín",
    "delfin equ": "Delfín",
    "nacional uru": "Nacional",
    "nacional": "Nacional",
    "nacional montevideo": "Nacional",
}

# Pairs of canonical team names that are traditional rivalries. Keys are
# stored alphabetically sorted so lookups are order-independent.
DERBIES = {
    ("Botafogo", "Flamengo"): "Clássico da Rivalidade",
    ("Botafogo", "Fluminense"): "Clássico Vovô",
    ("Botafogo", "Vasco da Gama"): "Clássico da Amizade",
    ("Flamengo", "Fluminense"): "Fla-Flu",
    ("Flamengo", "Vasco da Gama"): "Clássico dos Milhões",
    ("Palmeiras", "São Paulo"): "Choque-Rei",
    ("Corinthians", "São Paulo"): "Majestoso",
    ("Corinthians", "Palmeiras"): "Dérbi Paulista",
    ("Grêmio", "Internacional"): "Gre-Nal",
    ("Bahia", "Vitória"): "Ba-Vi",
    ("Athletico Paranaense", "Coritiba"): "Atletiba",
    ("Ceará", "Fortaleza"): "Clássico-Rei",
}


def _display_fallback(base: str) -> str:
    """Title-case a suffix-stripped name while preserving accents/spacing."""
    out = []
    for word in base.split(" "):
        if not word:
            continue
        out.append(word[0].upper() + word[1:])
    return " ".join(out)


def strip_team_suffix(name: str) -> tuple[str, str | None]:
    """Split "Palmeiras-SP" -> ("Palmeiras", "SP"); returns (base, code|None)."""
    cleaned = collapse_ws(name)
    match = _SUFFIX_RE.match(cleaned)
    if match and match.group("code").upper() in _SUFFIX_CODES:
        base = match.group("base").strip(" -–(")
        if base:
            return base, match.group("code").upper()
    return cleaned, None


def normalize_team(name: str) -> str:
    """Canonicalize a team name across dataset conventions.

    Handles: state suffixes ("Palmeiras-SP"), spaced suffixes ("América - MG"),
    country codes ("Nacional (URU)", "Guaraní-PAR"), missing accents
    ("Sao Paulo", "Gremio"), and known spelling variants ("Athletico-PR",
    "Atletico Goianiense").
    """
    if not name or not collapse_ws(name):
        return ""
    cleaned = collapse_ws(name)

    key = text_key(cleaned)
    if key in _TEAM_ALIASES:
        return _TEAM_ALIASES[key]

    base, _code = strip_team_suffix(cleaned)
    if base != cleaned:
        base_key = text_key(base)
        if base_key in _TEAM_ALIASES:
            return _TEAM_ALIASES[base_key]
        return _display_fallback(base)
    return cleaned


def team_key(name: str) -> str:
    """Stable identity key for a team after canonicalization."""
    return text_key(normalize_team(name))


def club_alias(name: str) -> str | None:
    """Canonical club name for FIFA-style club spellings, or None.

    FIFA data spells Brazilian clubs formally ("Sport Club do Recife",
    "América FC (Minas Gerais)"); the alias table maps those onto the
    canonical names used in the match data ("Sport Recife",
    "América Mineiro").
    """
    return _TEAM_ALIASES.get(text_key(name))


# Generic club-type tokens ignored when computing a team's identity key, so
# "Fortaleza", "Fortaleza FC", and "Fortaleza EC" share one identity.
_GENERIC_TOKENS = {"fc", "ec", "sc", "cf", "club", "clube", "esporte",
                   "futebol"}
_GENERIC_PAIRS = {"esporte clube", "futebol clube", "sport club"}


def identity_key(name: str) -> str:
    """Identity used for cross-file dedup and team matching.

    Same as team_key but additionally ignores generic club-type tokens:
    "Fortaleza FC" and "Fortaleza" share the identity "fortaleza".
    """
    tokens = team_key(name).split()
    while len(tokens) >= 2 and " ".join(tokens[-2:]) in _GENERIC_PAIRS:
        del tokens[-2:]
    while tokens and tokens[-1] in _GENERIC_TOKENS:
        tokens.pop()
    while tokens and tokens[0] in _GENERIC_TOKENS:
        tokens.pop(0)
    return " ".join(tokens)


def derby_name(team_a: str, team_b: str) -> str | None:
    """Return the rivalry name if two teams are a known derby, else None."""
    a, b = normalize_team(team_a), normalize_team(team_b)
    pair = (a, b) if a < b else (b, a)
    return DERBIES.get(pair)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_date(value: str | None) -> date | None:
    """Parse the date formats found across the datasets (or None)."""
    if value is None:
        return None
    text = collapse_ws(str(value))
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
    return None


def parse_season(value: str | int | None) -> int | None:
    """Parse a season/year cell ("2012", 2012, "NA") or None."""
    if value is None:
        return None
    text = collapse_ws(str(value))
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE"}:
        return None
    match = re.match(r"(\d{4})", text)
    return int(match.group(1)) if match else None


def parse_int(value: str | float | None) -> int | None:
    """Parse a goals/score cell; missing or non-numeric becomes None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = collapse_ws(str(value))
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE", "D", "E", "V"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_money(value: str | None) -> float | None:
    """Parse FIFA value/wage cells like "€110.5M" / "€565K" into euros."""
    if not value:
        return None
    text = strip_accents(
        value.strip().lstrip("€$R$ ").replace(",", "")  # noqa: B005
    )
    if not text or text.upper() in {"NA", "N/A"}:
        return None
    multiplier = 1.0
    if text and text[-1].upper() in {"K", "M", "B"}:
        multiplier = {"K": 1e3, "M": 1e6, "B": 1e9}[text[-1].upper()]
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None
