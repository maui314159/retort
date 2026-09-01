"""Normalization utilities for the Brazilian Soccer MCP Server.

Handles the three data-quality concerns called out in the specification:

* Team name variations -- datasets mix state suffixes ("Palmeiras-SP"),
  spaced suffixes ("Palmeiras - SP"), country qualifiers ("Nacional (URU)"),
  club prefixes ("EC Bahia"), accented and unaccented spellings
  ("São Paulo" / "Sao Paulo"), and full legal names.  ``canonical_team``
  reduces every variant to a single canonical display name, and
  ``team_key`` derives a stable lookup key from it.
* Date formats -- ISO ("2023-09-24"), ISO with time ("2012-05-19
  18:30:00") and Brazilian DD/MM/YYYY ("29/03/2003") are all parsed to an
  ISO ``YYYY-MM-DD`` string by ``parse_date``.
* Character encoding -- ``unaccent`` folds Brazilian Portuguese diacritics
  so comparisons never depend on the file's encoding choices.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def unaccent(text: str) -> str:
    """Return ``text`` with diacritics removed (São Paulo -> Sao Paulo)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_key(text: str) -> str:
    """Fold a name into a comparison key: unaccented, lowercase, alnum+space."""
    folded = unaccent(text).lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


# ---------------------------------------------------------------------------
# Team name canonicalization
# ---------------------------------------------------------------------------

# Brazilian state abbreviations used as suffixes in the datasets.
BRAZILIAN_STATES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

# Country codes appended to foreign clubs (mainly Libertadores data).
COUNTRY_CODES = {
    "ARG": "Argentina", "BOL": "Bolivia", "CHI": "Chile", "COL": "Colombia",
    "CRC": "Costa Rica", "ECU": "Ecuador", "EQU": "Ecuador", "HON": "Honduras",
    "MEX": "Mexico", "PAR": "Paraguay", "PER": "Peru", "URU": "Uruguay",
    "USA": "United States", "VEN": "Venezuela",
}

# Base names that must keep a geographic qualifier to stay unambiguous
# (e.g. America-MG vs America-RN, Nacional-AM vs Nacional of Uruguay).
AMBIGUOUS_BASES = {
    "america": "América",
    "nacional": "Nacional",
    "atletico": "Atlético",
    "athletico": "Athletico",
    "barcelona": "Barcelona",
    "juventud": "Juventud",
    "independiente": "Independiente",
    "bolivar": "Bolívar",
    "libertad": "Libertad",
}

# Alias table: normalized-key -> canonical display name.  Covers the
# recurring variants observed across the six datasets.
TEAM_ALIASES: dict[str, str] = {
    # Big clubs
    "corinthians": "Corinthians",
    "corinthians paulista": "Corinthians",
    "sport club corinthians paulista": "Corinthians",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "palmeiras": "Palmeiras",
    "santos": "Santos",
    "sao paulo": "São Paulo",
    "sao paulo fc": "São Paulo",
    "gremio": "Grêmio",
    "gremio fbpa": "Grêmio",
    "gremio foot ball porto alegrense": "Grêmio",
    "internacional": "Internacional",
    "sc internacional": "Internacional",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "club de regatas vasco da gama": "Vasco da Gama",
    "botafogo": "Botafogo",
    "botafogo rj": "Botafogo",
    "botafogo de futebol e regatas": "Botafogo",
    # Atleticos
    "atletico mineiro": "Atlético Mineiro",
    "atletico mg": "Atlético Mineiro",
    "clube atletico mineiro": "Atlético Mineiro",
    "atletico mineiro mg": "Atlético Mineiro",
    "athletico paranaense": "Athletico Paranaense",
    "atletico paranaense": "Athletico Paranaense",
    "athletico pr": "Athletico Paranaense",
    "atletico pr": "Athletico Paranaense",
    "athletico": "Athletico Paranaense",
    "ca paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense",
    "atletico go": "Atlético Goianiense",
    "atletico goianiense go": "Atlético Goianiense",
    "atletico goianiense goiano": "Atlético Goianiense",
    # Remaining Serie A / common clubs
    "cruzeiro": "Cruzeiro",
    "bahia": "Bahia",
    "ec bahia": "Bahia",
    "esporte clube bahia": "Bahia",
    "sport": "Sport Recife",
    "sport recife": "Sport Recife",
    "sport club do recife": "Sport Recife",
    "sport recife pe": "Sport Recife",
    "coritiba": "Coritiba",
    "coritiba fc": "Coritiba",
    "chapecoense": "Chapecoense",
    "chapecoense sc": "Chapecoense",
    "asso chapecoense": "Chapecoense",
    "goias": "Goiás",
    "goias ec": "Goiás",
    "goias esporte clube": "Goiás",
    "ponte preta": "Ponte Preta",
    "associacao atletica ponte preta": "Ponte Preta",
    "ec vitoria": "Vitória",
    "esporte clube vitoria": "Vitória",
    "ceara": "Ceará",
    "ceara sporting club": "Ceará",
    "figueirense": "Figueirense",
    "figueirense fc": "Figueirense",
    "avai": "Avaí",
    "avai fc": "Avaí",
    "bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
    "clube atletico bragantino": "Bragantino",
    "portuguesa": "Portuguesa",
    "portuguesa de desportos": "Portuguesa",
    "nautico": "Náutico",
    "nautico capibaribe": "Náutico",
    "clube nautico capibaribe": "Náutico",
    "criciuma": "Criciúma",
    "criciuma ec": "Criciúma",
    "cuiaba": "Cuiabá",
    "cuiaba ec": "Cuiabá",
    "juventude": "Juventude",
    "ec juventude": "Juventude",
    "joinville": "Joinville",
    "joinville sc": "Joinville",
    "santa cruz": "Santa Cruz",
    "santa cruz fc": "Santa Cruz",
    "santa cruz recife": "Santa Cruz",
    "parana": "Paraná",
    "parana clube": "Paraná",
    "csa": "CSA",
    "centro sportivo alagoano": "CSA",
    "abc": "ABC",
    "abc fc": "ABC",
    "sampaio correa": "Sampaio Corrêa",
    "sampaio correa fc": "Sampaio Corrêa",
    "paysandu": "Paysandu",
    "paysandu sc": "Paysandu",
    "londrina": "Londrina",
    "londrina ec": "Londrina",
    "guarani": "Guarani",
    "guarani sp": "Guarani",
    "guarani fc": "Guarani",
    "vila nova": "Vila Nova",
    "vila nova fc": "Vila Nova",
    "crb": "CRB",
    "club de regatas brasil": "CRB",
    "brasil de pelotas": "Brasil de Pelotas",
    "oeste": "Oeste",
    "oeste fc": "Oeste",
    "brasiliense": "Brasiliense",
    "sao caetano": "São Caetano",
    "sao caetano ec": "São Caetano",
    "ipatinga": "Ipatinga",
    "santo andre": "Santo André",
    "ec santo andre": "Santo André",
    "barueri": "Barueri",
    "gremio prudente": "Grêmio Prudente",
    "boavista": "Boavista",
    "boavista sc": "Boavista",
    "boavista sport club": "Boavista",
    "luverdense": "Luverdense",
    "operario pr": "Operário-PR",
    "remo": "Remo",
    "nautico pe": "Náutico",
    "atletico ac": "Atlético Acreano",
    "atletico goianiense ec": "Atlético Goianiense",
    "america rn": "América-RN",
    "america mg": "América Mineiro",
    "america mineiro": "América Mineiro",
    "sport recife sc": "Sport Recife",
    "bragantino sp": "Bragantino",
    "sao paulo sp": "São Paulo",
    "red bull brasil": "Red Bull Brasil",
    "tombense": "Tombense",
    "confianca": "Confiança",
    "ferroviario": "Ferroviário",
    "botafogo pb": "Botafogo-PB",
    "gremio novo horizontino": "Grêmio Novo Horizontino",
    "inter de limeira": "Inter de Limeira",
    "pontagrossense": "Ponta Grossa",
    "itabuna": "Itabuna",
    "juazeiro": "Juazeiro",
    "central": "Central",
    "cianorte": "Cianorte",
    "novorizontino": "Novorizontino",
    "atletico cearense": "Atlético Cearense",
    "nacional am": "Nacional-AM",
    "gremio anapolis": "Grêmio Anápolis",
    "pacifico fc": "Pacífico FC",
    # Identity splits observed across datasets (same club, name variants)
    "fortaleza fc": "Fortaleza",
    "fortaleza ec": "Fortaleza",
    "fortaleza esporte clube": "Fortaleza",
    "a b c": "ABC",
    "a s a": "ASA",
    "c r b": "CRB",
    "c s a": "CSA",
    "c r a c": "CRAC",
    "ad confianca": "Confiança",
    "america fc natal": "América-RN",
    "america de natal": "América-RN",
    "boavista sc saquarema": "Boavista",
    "brasilia fc": "Brasília",
    "criciu": "Criciúma",  # truncated form found in source data
    "duque de caxias fc": "Duque de Caxias",
    "duque de caxias": "Duque de Caxias",
    "ferroviaria": "Ferroviária",
    "gremio novorizontino": "Novorizontino",
    "gremio novo horizontino": "Novorizontino",
    "grêmio barueri": "Grêmio Barueri",
    "gremio barueri": "Grêmio Barueri",
    "independiente del valle": "Independiente del Valle",
    "macae esporte fc": "Macaé",
    "macae esporte": "Macaé",
    "moto club de sao luis": "Moto Club",
    "moto clube": "Moto Club",
    "nova iguacu": "Nova Iguaçu",
    "nova mutum ec": "Nova Mutum",
    "operario": "Operário Ferroviário",
    "operario fc": "Operário Ferroviário",
    "operario ferroviario esporte c": "Operário Ferroviário",
    "penarol": "Peñarol",
    "porto velho ec": "Porto Velho",
    "portuguesa desportos": "Portuguesa",
    "pstc": "PSTC",
    "real noroeste capixaba": "Real Noroeste",
    "retro fc brasil": "Retrô",
    "retro": "Retrô",
    "sao bento": "São Bento",
    "sao bernardo": "São Bernardo",
    "sao luiz": "São Luiz",
    "sao raimundo": "São Raimundo",
    "sinop fc": "Sinop",
    "toledo ec": "Toledo",
    "tocantinopolis ec": "Tocantinópolis",
    "tocantinopolis": "Tocantinópolis",
    "tubarao": "Tubarão",
    "uberlandia": "Uberlândia",
    "uniao rondonopolis": "União Rondonópolis",
    "uniao de rondonopolis": "União Rondonópolis",
    "urt": "URT",
    "xv piracicaba": "XV de Piracicaba",
    "xv de piracicaba": "XV de Piracicaba",
    "aguia negra": "Águia Negra",
    "4 de julho ec": "4 de Julho",
    "aguia de maraba": "Águia de Marabá",
    "fc atletico cearense": "Atlético Cearense",
    "atletico acreano": "Atlético Acreano",
    "atletico alagoinhas": "Atlético Alagoinhas",
    "vitoria": "Vitória",
    "vitoria ec": "Vitória",
    "vitoria f c": "Vitória-ES",
    "desportiva": "Desportiva Ferroviária",
    "desportiva ferroviaria": "Desportiva Ferroviária",
    "se gama": "Gama",
    "gama": "Gama",
    "jaragua ec": "Jaraguá",
    "caldense": "Caldense",
    "brusque": "Brusque",
    "ituano": "Ituano",
    "mirassol": "Mirassol",
    "volta redonda": "Volta Redonda",
    "clube do remo": "Remo",
}

_TRAILING_CODE = re.compile(r"[\s\-]*-?\s*([A-Za-z]{2,3})$")
_TRAILING_PAREN = re.compile(r"\s*\(([^()]*)\)\s*$")


def _split_qualifiers(name: str) -> tuple[str, str | None, str | None]:
    """Split trailing state/country qualifiers and commentary off a team name.

    Returns ``(base, state, country)`` where the qualifiers may be ``None``.
    """
    base = name.strip()
    state: str | None = None
    country: str | None = None

    # Alternately strip trailing commentary/codes: "X (antigo Y) - RJ",
    # "Nacional (URU)", "Sao Jose - POA", ...
    changed = True
    while changed and base:
        changed = False
        match = _TRAILING_PAREN.search(base)
        if match:
            inner = match.group(1).strip()
            code = inner.upper().replace(".", "")
            if code in COUNTRY_CODES:
                country = COUNTRY_CODES[code]
            elif code in BRAZILIAN_STATES:
                state = code
            # Commentary like "(antigo Esporte Clube Barreira)" is dropped either way.
            base = base[: match.start()].strip()
            changed = True
            continue
        match = _TRAILING_CODE.search(base)
        if match:
            token = match.group(1).upper()
            prefix = base[: match.start()].strip()
            if not prefix:
                break  # never strip the whole name (e.g. "LDU")
            if token in COUNTRY_CODES:
                country = COUNTRY_CODES[token]
            elif token in BRAZILIAN_STATES:
                state = token
            else:
                break  # last token is a word, not a qualifier
            base = prefix
            changed = True

    return base, state, country


def canonical_team(raw_name: str) -> str:
    """Map any team-name variant to its canonical display name.

    Examples::

        "Palmeiras-SP"                 -> "Palmeiras"
        "Grêmio - RS"                  -> "Grêmio"
        "Boavista Sport Club (...) -RJ"-> "Boavista"
        "Sao Paulo"                    -> "São Paulo"
        "Vasco Da Gama RJ"             -> "Vasco da Gama"
        "Nacional (URU)"               -> "Nacional (Uruguay)"
        "Nacional - AM"                -> "Nacional-AM"
        "Barcelona-EQU"                -> "Barcelona (Ecuador)"
        "Athletico"                    -> "Athletico Paranaense"
    """
    if not raw_name or not raw_name.strip():
        return ""
    base, state, country = _split_qualifiers(raw_name)
    if not base:
        return raw_name.strip()
    key = normalize_key(base)

    # 0) State-dependent overrides that beat generic aliases
    #    (Vitória-ES is a different club from EC Vitória).
    if key == "vitoria" and state == "ES":
        return "Vitória-ES"
    # 1) Base name resolves directly ("Sao Paulo", "EC Bahia").
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    # 2) Base + state qualifier resolves ("Atletico" + "PR" -> "Athletico Paranaense").
    if state:
        combo = f"{key} {state.lower()}"
        if combo in TEAM_ALIASES:
            return TEAM_ALIASES[combo]
    # 3) Ambiguous bases must keep a geographic qualifier to stay distinct.
    if key in AMBIGUOUS_BASES:
        if state:
            return f"{AMBIGUOUS_BASES[key]}-{state}"
        if country:
            return f"{AMBIGUOUS_BASES[key]} ({country})"
    if country:
        return f"{base} ({country})"
    return base


def team_key(canonical_name: str) -> str:
    """Stable lookup key for a canonical team name (accent/case folded)."""
    return normalize_key(canonical_name)


def key_team(raw_name: str) -> str:
    """Convenience: canonical key directly from any raw variant."""
    return team_key(canonical_team(raw_name))


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


def parse_date(value: str) -> str | None:
    """Parse the date formats used across the datasets to ISO ``YYYY-MM-DD``.

    Returns ``None`` when the value is empty or unparseable ("NA", "-", ...).
    """
    if value is None:
        return None
    text = value.strip()
    if not text or text.upper() in {"NA", "N/A", "-", "NULL"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_int(value: str | None) -> int | None:
    """Parse numeric CSV values ("2", "2.0", "-", "NA") into ints."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "-", "NULL"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number)


# ---------------------------------------------------------------------------
# Competition canonicalization
# ---------------------------------------------------------------------------

COMPETITION_ALIASES: dict[str, str] = {
    "serie a": "Brasileirão Série A",
    "brasileirao serie a": "Brasileirão Série A",
    "brasileirao": "Brasileirão Série A",
    "campeonato brasileiro": "Brasileirão Série A",
    "campeonato brasileiro serie a": "Brasileirão Série A",
    "serie b": "Brasileirão Série B",
    "brasileirao serie b": "Brasileirão Série B",
    "campeonato brasileiro serie b": "Brasileirão Série B",
    "serie c": "Brasileirão Série C",
    "brasileirao serie c": "Brasileirão Série C",
    "campeonato brasileiro serie c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "copa libertadores": "Copa Libertadores",
    "libertadores": "Copa Libertadores",
}


def canonical_competition(raw_name: str) -> str:
    """Canonical competition display name for any raw variant."""
    key = normalize_key(raw_name)
    return COMPETITION_ALIASES.get(key, raw_name.strip())


def competition_key(canonical_name: str) -> str:
    """Stable lookup key for a competition name (matches aliases too)."""
    key = normalize_key(canonical_name)
    return normalize_key(COMPETITION_ALIASES.get(key, canonical_name))
