"""Normalization utilities for team names, dates, and competition names.

The source datasets use several naming conventions for the same club
("Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista"), multiple
date formats ("2012-05-19 18:30:00", "29/03/2003"), and accented Portuguese
text.  This module centralizes the rules that map every observed variant onto
a canonical, accent-free, lowercase team key so that lookups behave
consistently across files.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

BRAZILIAN_STATE_CODES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

TEAM_ALIASES = {
    "atletico mineiro": "atletico mg",
    "atletico mineiro mg": "atletico mg",
    "clube atletico mineiro": "atletico mg",
    "atletico goianiense": "atletico go",
    "atletico goianiense go": "atletico go",
    "atletico paranaense": "atletico pr",
    "atletico paranaense pr": "atletico pr",
    "athletico paranaense": "atletico pr",
    "athletico paranaense pr": "atletico pr",
    "athletico pr": "atletico pr",
    "athletico": "atletico pr",
    "sport recife": "sport",
    "sport club do recife": "sport",
    "sport recife pe": "sport",
    "ceara sporting club": "ceara",
    "ceara sc": "ceara",
    "clube do remo": "remo",
    "nautico capibaribe": "nautico",
    "vasco da gama": "vasco",
    "vasco da gama rj": "vasco",
    "cs alagoano": "csa",
    "centro sportivo alagoano": "csa",
    "cs sergipe": "sergipe",
    "boavista sport club": "boavista",
    "boavista sport club rj": "boavista",
    "boavista sc saquarema": "boavista",
    "gremio rs": "gremio",
    "internacional rs": "internacional",
    "vitoria ec": "vitoria ba",
    "ec vitoria": "vitoria ba",
    "vitoria": "vitoria ba",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "red bull bragantino sp": "bragantino",
    "botafogo": "botafogo rj",
    "sport club corinthians paulista": "corinthians",
    "spfc": "sao paulo",
    "parana clube": "parana",
    "santa cruz fc": "santa cruz",
    "aa ponte preta": "ponte preta",
    "portuguesa desportos": "portuguesa",
    "america fc natal": "america rn",
    "gremio novorizontino": "novorizontino",
    "athletic club": "athletic mg",
    "athletic club mg": "athletic mg",
    "fortaleza ec": "fortaleza",
    "fortaleza fc": "fortaleza",
    "sao jose poa": "sao jose rs",
    "operario fc ms": "operario ms",
    "operario fc": "operario pr",
    "ad confianca": "confianca",
    "vila nova fc": "vila nova",
    "sampaio correa ma": "sampaio correa",
    "4 de julho ec": "4 de julho pi",
    "macae esporte fc": "macae",
    "macae esporte rj": "macae",
    "madureira ec": "madureira",
    "madureira rj": "madureira",
    "caldense mg": "caldense",
    "tombense mg": "tombense",
    "urt mg": "urt",
    "tupi mg": "tupi",
    "real noroeste es": "real noroeste",
    "resende rj": "resende",
    "ec juventude": "juventude",
    "nova mutum ec": "nova mutum",
    "cordino ec": "cordino",
    "retro fc brasil": "retro",
    "santo andre sp": "santo andre",
    "ferroviaria sp": "ferroviaria",
    "capivariano sp": "capivariano",
    "guarulhos sp": "guarulhos",
    "suzano sp": "suzano",
    "audax sp": "audax",
    "costa rica ec": "costa rica",
    "metropolitano maringa pr": "maringa",
    "porto velho ec": "porto velho",
    "vilhena ro": "vilhena",
    "toledo ec": "toledo",
    "jaragua ec": "jaragua",
    "ge bage": "bage",
    "ge gloria": "gloria",
    "ce aimore": "aimore",
    "ce dom bosco": "dom bosco",
    "se gama": "gama",
    "ca taguatinga": "taguatinga",
    "brasilia fc": "brasilia",
    "palmas fr": "palmas",
    "sinop fc": "sinop",
    "galvez ac": "galvez",
    "trem ap": "trem",
    "moto club de sao luis": "moto clube",
    "moto club de sao luis ma": "moto clube",
    "nautico capibaribe pe": "nautico",
}

UNAMBIGUOUS_BASES = {
    "palmeiras", "flamengo", "corinthians", "santos", "sao paulo", "sport",
    "bahia", "ceara", "fortaleza", "cruzeiro", "coritiba", "parana",
    "chapecoense", "avai", "figueirense", "criciuma", "goias", "gremio",
    "internacional", "fluminense", "guarani", "portuguesa", "juventude",
    "caxias", "nautico", "remo", "paysandu", "sampaio correa", "csa", "crb",
    "abc", "vasco", "vila nova", "ponte preta", "santa cruz", "joinville",
    "bragantino", "confianca", "operario ms", "america rn", "cuiaba",
}

DISPLAY_OVERRIDES = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "vasco": "Vasco da Gama",
    "botafogo rj": "Botafogo",
    "botafogo sp": "Botafogo-SP",
    "botafogo pb": "Botafogo-PB",
    "corinthians": "Corinthians",
    "palmeiras": "Palmeiras",
    "sao paulo": "São Paulo",
    "santos": "Santos",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "cruzeiro": "Cruzeiro",
    "atletico mg": "Atlético-MG",
    "atletico pr": "Athletico-PR",
    "atletico go": "Atlético-GO",
    "sport": "Sport",
    "bahia": "Bahia",
    "vitoria ba": "Vitória",
    "ceara": "Ceará",
    "fortaleza": "Fortaleza",
    "coritiba": "Coritiba",
    "parana": "Paraná",
    "chapecoense": "Chapecoense",
    "avai": "Avaí",
    "figueirense": "Figueirense",
    "criciuma": "Criciúma",
    "goias": "Goiás",
    "america mg": "América-MG",
    "america rn": "América-RN",
    "cuiaba": "Cuiabá",
    "bragantino": "Red Bull Bragantino",
    "ponte preta": "Ponte Preta",
    "santa cruz": "Santa Cruz",
    "joinville": "Joinville",
    "juventude": "Juventude",
    "caxias": "Caxias",
    "nautico": "Náutico",
    "remo": "Remo",
    "paysandu": "Paysandu",
    "csa": "CSA",
    "crb": "CRB",
    "abc": "ABC",
    "sampaio correa": "Sampaio Corrêa",
    "vila nova": "Vila Nova",
    "guarani": "Guarani",
    "portuguesa": "Portuguesa",
    "sao caetano": "São Caetano",
    "santo andre": "Santo André",
    "athletic mg": "Athletic",
    "novorizontino": "Novorizontino",
    "operario pr": "Operário-PR",
    "operario ms": "Operário-MS",
    "confianca": "Confiança",
    "sergipe": "Sergipe",
    "boavista": "Boavista",
    "macae": "Macaé",
    "madureira": "Madureira",
    "volta redonda": "Volta Redonda",
    "ferroviaria": "Ferroviária",
    "fluminense de feira": "Fluminense de Feira",
    "bahia de feira": "Bahia de Feira",
    "vitoria es": "Vitória-ES",
    "vitoria da conquista": "Vitória da Conquista",
    "sao jose rs": "São José-RS",
    "maringa": "Maringá",
    "londrina": "Londrina",
    "sinop": "Sinop",
    "luverdense": "Luverdense",
    "gama": "Gama",
    "brasilia": "Brasília",
    "brasiliense": "Brasiliense",
    "ceilandia": "Ceilândia",
    "taguatinga": "Taguatinga",
    "sao bento": "São Bento",
    "sao bernardo": "São Bernardo",
    "mirassol": "Mirassol",
    "ituano": "Ituano",
    "oeste": "Oeste",
    "inter de limeira": "Inter de Limeira",
    "aguia negra ms": "Águia Negra",
    "cene ms": "CENE",
}

_PAREN_RE = re.compile(r"\(([^)]*)\)")


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def slug(value: str) -> str:
    """Lowercase, de-accent, and tokenize a raw name for matching."""
    text = strip_accents(value or "").lower()
    kept_parens = []
    for inner in _PAREN_RE.findall(text):
        inner = inner.strip()
        if inner and len(inner.split()) == 1 and len(inner) <= 4:
            kept_parens.append(inner)
    text = _PAREN_RE.sub(" ", text)
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    tokens = text.split() + kept_parens
    return " ".join(tokens)


def team_key(name: str) -> str:
    """Return the canonical team key for a raw team or club name."""
    key = slug(name)
    if not key:
        return key
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    tokens = key.split()
    if len(tokens) > 1 and tokens[-1].upper() in BRAZILIAN_STATE_CODES:
        base = " ".join(tokens[:-1])
        if base in UNAMBIGUOUS_BASES:
            return base
    return key


def display_name(key: str, fallback: str | None = None) -> str:
    """Return a human-friendly display name for a canonical team key."""
    if key in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[key]
    if fallback:
        return fallback
    return key.title()


DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_date(value: str | None) -> date | None:
    """Parse the date formats used across the datasets.

    Handles ISO dates with or without time ("2012-05-19 18:30:00",
    "2023-09-24") and Brazilian day-first dates ("29/03/2003").
    """
    if not value:
        return None
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


DERBIES: tuple[tuple[str, str, str], ...] = (
    ("flamengo", "fluminense", "Fla-Flu"),
    ("flamengo", "vasco", "Clássico dos Milhões"),
    ("botafogo rj", "fluminense", "Clássico Vovô"),
    ("botafogo rj", "flamengo", "Clássico da Rivalidade"),
    ("botafogo rj", "vasco", "Clássico dos Gigantes"),
    ("gremio", "internacional", "Gre-Nal"),
    ("corinthians", "sao paulo", "Clássico Majestoso"),
    ("sao paulo", "santos", "Choque-Rei"),
    ("corinthians", "palmeiras", "O Derby (Derby Paulista)"),
    ("palmeiras", "santos", "Clássico da Saudade"),
    ("atletico mg", "cruzeiro", "Clássico Mineiro"),
    ("bahia", "vitoria ba", "Ba-Vi"),
    ("sport", "nautico", "Clássico dos Clássicos"),
    ("sport", "santa cruz", "Clássico das Multidões"),
    ("nautico", "santa cruz", "Clássico dos Emoções"),
    ("coritiba", "atletico pr", "Atletiba"),
    ("atletico pr", "parana", "Paratiba"),
    ("ceara", "fortaleza", "Clássico-Rei"),
    ("remo", "paysandu", "Re-Pa"),
    ("avai", "figueirense", "Clássico de Florianópolis"),
    ("goias", "vila nova", "Clássico Goiano"),
)

DERBY_PAIRS = {frozenset((a, b)): name for a, b, name in DERBIES}
