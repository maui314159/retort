"""Team-name normalization for Brazilian soccer datasets.

The six source CSV files spell club names in several conventions:
state-suffixed ("Palmeiras-SP", "América - MG"), unaccented ("Atletico-MG"),
full legal names ("Sport Club Corinthians Paulista"), FIFA-style names
("Atlético Paranaense") and country-tagged Libertadores names
("Barcelona-EQU", "Nacional (URU)").

This module reduces every spelling to a single canonical key so matches,
players and statistics can be joined across files.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

BRAZILIAN_UFS: frozenset[str] = frozenset(
    {
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
        "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR",
        "RS", "SC", "SE", "SP", "TO",
    }
)

COUNTRY_CODES: frozenset[str] = frozenset(
    {
        "ARG", "BOL", "CHI", "COL", "EQU", "MEX", "PAR", "PER", "URU", "VEN",
        "USA", "JPN", "KOR", "CRC", "GUA", "HON", "SLV", "PAN",
    }
)

_LEGAL_TOKENS: frozenset[str] = frozenset(
    {
        "aa", "ac", "cb", "cbd", "clube", "club", "da", "das", "de", "do",
        "dos", "ec", "esporte", "esportiva", "esportivo", "fc", "futebol",
        "regatas", "sc", "sociedade", "the",
    }
)

# Club bases shared by more than one club (state suffix disambiguates them).
# The famous club of each base keeps the short key; small Serie C/D clubs that
# happen to share the name get "base-uf" keys.
AMBIGUOUS_BASES: dict[str, dict[str, str]] = {
    "america": {"MG": "america-mg", "RN": "america-rn", "SC": "america-sc"},
    "atletico": {"MG": "atletico-mg", "GO": "atletico-go", "PR": "athletico-pr"},
    "athletico": {"PR": "athletico-pr"},
    "botafogo": {"RJ": "botafogo", "PB": "botafogo-pb", "SP": "botafogo-sp"},
    "bragantino": {"SP": "red bull bragantino", "PA": "bragantino-pa"},
    "central": {"PE": "central", "SC": "central-sc"},
    "comercial": {"MS": "comercial-ms", "PI": "comercial-pi"},
    "flamengo": {"RJ": "flamengo", "PI": "flamengo-pi"},
    "fluminense": {"RJ": "fluminense", "PI": "fluminense-pi"},
    "guarani": {"SP": "guarani", "CE": "guarani-ce"},
    "internacional": {"RS": "internacional", "SC": "internacional-sc"},
    "juventude": {"RS": "juventude", "MA": "juventude-ma"},
    "nautico": {"PE": "nautico", "RR": "nautico-rr"},
    "operario": {"PR": "operario-pr", "MS": "operario-ms", "MT": "operario-mt"},
    "portuguesa": {"SP": "portuguesa", "RJ": "portuguesa-rj"},
    "rio branco": {"AC": "rio branco-ac", "ES": "rio branco-es"},
    "river": {"PI": "river-pi", "AC": "river-ac"},
    "santa cruz": {"PE": "santa cruz", "RN": "santa cruz-rn", "RS": "santa cruz-rs"},
    "santos": {"SP": "santos", "AP": "santos-ap"},
    "sao francisco": {"PA": "sao francisco-pa", "AC": "sao francisco-ac"},
    "sao jose": {"RS": "sao jose-rs", "PA": "sao jose-pa"},
    "sao raimundo": {
        "PA": "sao raimundo-pa",
        "AM": "sao raimundo-am",
        "RR": "sao raimundo-rr",
    },
    "vitoria": {"BA": "vitoria", "ES": "vitoria-es"},
    "ypiranga": {"RS": "ypiranga-rs", "AP": "ypiranga-ap"},
}

# Resolution for ambiguous bases written without a state suffix (the famous club).
_BARE_DEFAULTS: dict[str, str] = {
    "america": "america-mg",
    "athletico": "athletico-pr",
    "botafogo": "botafogo",
    "bragantino": "red bull bragantino",
    "flamengo": "flamengo",
    "fluminense": "fluminense",
    "guarani": "guarani",
    "internacional": "internacional",
    "juventude": "juventude",
    "nautico": "nautico",
    "portuguesa": "portuguesa",
    "santa cruz": "santa cruz",
    "santos": "santos",
    "vitoria": "vitoria",
}

# Full names / alternate spellings that generic rules cannot unify by themselves.
ALIASES: dict[str, str] = {
    "atletico mineiro": "atletico-mg",
    "atletico paranaense": "athletico-pr",
    "athletico paranaense": "athletico-pr",
    "paranaense": "athletico-pr",
    "corinthians paulista": "corinthians",
    "sport corinthians paulista": "corinthians",
    "sport recife": "sport",
    "ceara sporting": "ceara",
    "vasco gama": "vasco",
    "spfc": "sao paulo",
    "rb bragantino": "red bull bragantino",
    "junior": "junior barranquilla",
}

# Canonical display names (accented Portuguese forms where appropriate).
DISPLAY_NAMES: dict[str, str] = {
    "america-mg": "América-MG",
    "america-rn": "América-RN",
    "america-sc": "América-SC",
    "atletico-go": "Atlético-GO",
    "atletico-mg": "Atlético-MG",
    "athletico-pr": "Athletico-PR",
    "avai": "Avaí",
    "bahia": "Bahia",
    "botafogo": "Botafogo",
    "botafogo-pb": "Botafogo-PB",
    "botafogo-sp": "Botafogo-SP",
    "ceara": "Ceará",
    "chapecoense": "Chapecoense",
    "corinthians": "Corinthians",
    "coritiba": "Coritiba",
    "criciuma": "Criciúma",
    "csa": "CSA",
    "cuiaba": "Cuiabá",
    "cruzeiro": "Cruzeiro",
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
    "santa cruz": "Santa Cruz",
    "santos": "Santos",
    "sao caetano": "São Caetano",
    "sao paulo": "São Paulo",
    "santo andre": "Santo André",
    "sport": "Sport",
    "vasco": "Vasco da Gama",
    "vitoria": "Vitória",
}

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
_PARENS = re.compile(r"\(([^)]*)\)")


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def team_key(name: str) -> str:
    """Reduce any spelling of a team name to its canonical key."""
    if not name:
        return ""
    text = name.strip()
    # Keep country tags from parentheticals ("Nacional (URU)" -> "nacional-uru"),
    # drop every other parenthetical annotation ("(antigo ...)", "(Minas Gerais)").
    kept_codes: list[str] = []
    for inside in _PARENS.findall(text):
        token = inside.strip().upper().split()[0] if inside.strip() else ""
        if token in COUNTRY_CODES:
            kept_codes.append(token)
    text = _PARENS.sub(" ", text)

    tokens = [t for t in _TOKEN_SPLIT.split(_fold(text)) if t]
    for country_code in kept_codes:
        tokens.append(country_code.lower())

    code: str | None = None
    if len(tokens) > 1 and tokens[-1].upper() in (BRAZILIAN_UFS | COUNTRY_CODES):
        code = tokens.pop().upper()

    base_tokens = [t for t in tokens if t not in _LEGAL_TOKENS]
    base = " ".join(base_tokens).strip()
    if not base:
        base = " ".join(tokens).strip()

    if code in COUNTRY_CODES:
        return f"{base}-{code.lower()}"

    if base in AMBIGUOUS_BASES:
        if code:
            return AMBIGUOUS_BASES[base].get(code, f"{base}-{code.lower()}")
        return _BARE_DEFAULTS.get(base, base)

    return ALIASES.get(base, base)


def display_name(key: str, fallback: str | None = None) -> str:
    """Canonical human-readable name for a team key."""
    if key in DISPLAY_NAMES:
        return DISPLAY_NAMES[key]
    if fallback:
        return fallback
    return key.replace("-", " ").title()


def fold_text(text: str) -> str:
    """Case- and accent-insensitive form used for substring searches."""
    return " ".join(_fold(text).split())


def similar_names(query: str, candidates: list[str], limit: int = 5) -> list[str]:
    """Fuzzy suggestions for an unrecognized name."""
    return difflib.get_close_matches(query, list(candidates), n=limit, cutoff=0.5)


class TeamResolutionError(ValueError):
    """Raised when a team name cannot be resolved to a known club."""


# Canonical competition labels and their accepted spellings.
COMPETITIONS: list[str] = [
    "Brasileirão Série A",
    "Brasileirão Série B",
    "Brasileirão Série C",
    "Copa do Brasil",
    "Copa Libertadores",
]

_COMPETITION_ALIASES: dict[str, str] = {
    "brasileirao": "Brasileirão Série A",
    "brasileirao serie a": "Brasileirão Série A",
    "serie a": "Brasileirão Série A",
    "campeonato brasileiro": "Brasileirão Série A",
    "brasileirao serie b": "Brasileirão Série B",
    "serie b": "Brasileirão Série B",
    "brasileirao serie c": "Brasileirão Série C",
    "serie c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "copa libertadores da america": "Copa Libertadores",
}


def competition_label(name: str) -> str | None:
    """Resolve a user-supplied competition name to its canonical label."""
    if not name:
        return None
    key = fold_text(name)
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    if name in COMPETITIONS:
        return name
    for label in COMPETITIONS:
        if key in fold_text(label) or fold_text(label) in key:
            return label
    return None


# Named rivalries answerable from the provided match data.
DERBIES: dict[str, tuple[str, str]] = {
    "Fla-Flu": ("flamengo", "fluminense"),
    "Clássico dos Milhões": ("flamengo", "vasco"),
    "Gre-Nal": ("gremio", "internacional"),
    "Clássico Mineiro": ("atletico-mg", "cruzeiro"),
    "Derby Paulista": ("corinthians", "palmeiras"),
    "Majestoso": ("corinthians", "sao paulo"),
    "Choque-Rei": ("palmeiras", "sao paulo"),
    "San-São": ("santos", "sao paulo"),
    "Ba-Vi": ("bahia", "vitoria"),
    "Atletiba": ("athletico-pr", "coritiba"),
    "Clássico-Rei": ("ceara", "fortaleza"),
    "Clássico dos Clássicos": ("sport", "nautico"),
    "Clássico dos Emoções": ("sport", "santa cruz"),
}
