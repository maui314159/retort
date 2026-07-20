"""Normalization utilities: team names, free text and dates.

The datasets use different naming conventions for the same team
("Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista") and several
date formats (ISO, ISO-with-time, DD/MM/YYYY).  This module provides a single
canonical *key* per team plus accent-insensitive text matching and tolerant
date parsing.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def strip_accents(text: str) -> str:
    """Return *text* without diacritical marks (São -> Sao, Grêmio -> Gremio)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def norm_text(text: object) -> str:
    """Lower-cased, accent-stripped, whitespace-collapsed version of *text*."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------

_PAREN_RE = re.compile(r"\(([^)]*)\)")
_STATE_SUFFIX_RE = re.compile(r"[-–/]\s*([a-zA-Z]{2,3})\s*$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")

# Aliases map a normalized raw key to the canonical key.  Unambiguous,
# well-known clubs collapse to a state-less canonical key; ambiguous names
# (Botafogo, América, Atlético ...) keep their state token so that e.g.
# "Botafogo-SP" and "Botafogo-RJ" remain distinct teams.
_TEAM_ALIASES: dict[str, str] = {
    # Série A regulars
    "palmeiras sp": "palmeiras",
    "flamengo rj": "flamengo",
    "fluminense rj": "fluminense",
    "corinthians sp": "corinthians",
    "sao paulo sp": "sao paulo",
    "santos sp": "santos",
    "gremio rs": "gremio",
    "internacional rs": "internacional",
    "cruzeiro mg": "cruzeiro",
    "bahia ba": "bahia",
    "fortaleza ce": "fortaleza",
    "ceara ce": "ceara",
    "goias go": "goias",
    "coritiba pr": "coritiba",
    "chapecoense sc": "chapecoense",
    "figueirense sc": "figueirense",
    "avai sc": "avai",
    "juventude rs": "juventude",
    "cuiaba mt": "cuiaba",
    "guarani sp": "guarani",
    "ponte preta sp": "ponte preta",
    "nautico pe": "nautico",
    "vitoria ba": "vitoria",
    "parana pr": "parana",
    "portuguesa sp": "portuguesa",
    "sao caetano sp": "sao caetano",
    "paysandu pa": "paysandu",
    "santa cruz pe": "santa cruz",
    "criciuma sc": "criciuma",
    "joinville sc": "joinville",
    "brasiliense df": "brasiliense",
    "santo andre sp": "santo andre",
    "csa al": "csa",
    "crb al": "crb",
    "remo pa": "remo",
    "abc rn": "abc",
    "londrina pr": "londrina",
    "oeste sp": "oeste",
    "ituano sp": "ituano",
    "mirassol sp": "mirassol",
    "novorizontino sp": "novorizontino",
    "bangu rj": "bangu",
    # Ambiguous names -- canonical key keeps the state.
    "sport": "sport recife",
    "sport pe": "sport recife",
    "athletico pr": "athletico paranaense",
    "athletico": "athletico paranaense",
    "atletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "atletico mg": "atletico mineiro",
    "atletico go": "atletico goianiense",
    "america mg": "america mineiro",
    "america mineiro": "america mineiro",
    "america fc natal": "america rn",
    "botafogo": "botafogo rj",
    "vasco": "vasco da gama",
    "vasco rj": "vasco da gama",
    "bragantino sp": "bragantino",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "brasil de pelotas rs": "brasil de pelotas",
    "operario pr": "operario ferroviario",
    "operario ferroviario pr": "operario ferroviario",
    "sampaio correa ma": "sampaio correa",
    "boavista": "boavista rj",
    "boavista sport club": "boavista rj",
    "boavista sc saquarema": "boavista rj",
    "americano": "americano rj",
    "4 de julho ec": "4 de julho pi",
}


def _base_team_key(name: str) -> str:
    """Normalize a raw team name to a key (accents stripped, state kept)."""
    text = norm_text(name)
    if not text:
        return ""

    # Parentheticals: keep short country/state codes ("(URU)"), drop long
    # annotations ("(antigo Esporte Clube Barreira)").
    def _paren_sub(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        return f" {inner} " if len(inner) <= 4 else " "

    text = _PAREN_RE.sub(_paren_sub, text)
    # Turn a trailing state/country suffix "-SP" / " - MG" / "/RJ" into a
    # space-separated token so it survives aliasing instead of being lost.
    text = _STATE_SUFFIX_RE.sub(r" \1", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def team_key(name: object) -> str:
    """Return the canonical key for a raw team name (any naming convention)."""
    base = _base_team_key(name) if isinstance(name, str) else ""
    if not base:
        return ""
    return _TEAM_ALIASES.get(base, base)


def teams_match(raw_or_key: str, key: str) -> bool:
    """True when *raw_or_key* resolves to the canonical *key*."""
    return team_key(raw_or_key) == key


# ---------------------------------------------------------------------------
# Competition normalization
# ---------------------------------------------------------------------------

COMP_BRASILEIRAO_A = "Brasileirão Série A"
COMP_BRASILEIRAO_B = "Brasileirão Série B"
COMP_BRASILEIRAO_C = "Brasileirão Série C"
COMP_COPA_DO_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"

_COMPETITION_ALIASES: dict[str, str] = {
    "brasileirao": COMP_BRASILEIRAO_A,
    "brasileirao serie a": COMP_BRASILEIRAO_A,
    "brasileirao série a": COMP_BRASILEIRAO_A,
    "serie a": COMP_BRASILEIRAO_A,
    "série a": COMP_BRASILEIRAO_A,
    "campeonato brasileiro": COMP_BRASILEIRAO_A,
    "campeonato brasileiro serie a": COMP_BRASILEIRAO_A,
    "brasileirao serie b": COMP_BRASILEIRAO_B,
    "serie b": COMP_BRASILEIRAO_B,
    "brasileirao serie c": COMP_BRASILEIRAO_C,
    "serie c": COMP_BRASILEIRAO_C,
    "copa do brasil": COMP_COPA_DO_BRASIL,
    "brazilian cup": COMP_COPA_DO_BRASIL,
    "libertadores": COMP_LIBERTADORES,
    "copa libertadores": COMP_LIBERTADORES,
    "copa libertadores da america": COMP_LIBERTADORES,
}


def competition_key(name: object) -> str:
    """Resolve a competition name (any spelling) to the canonical label."""
    text = norm_text(name)
    if not text:
        return ""
    if text in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[text]
    # Substring fallback: "copa do brasil 2023" -> Copa do Brasil, etc.
    for alias, canonical in sorted(
        _COMPETITION_ALIASES.items(), key=lambda kv: -len(kv[0])
    ):
        if alias in text:
            return canonical
    return ""


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


def parse_date(value: object) -> date | None:
    """Parse ISO, ISO-with-time and Brazilian DD/MM/YYYY dates.

    Returns a ``datetime.date`` or ``None`` when the value cannot be parsed.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: pandas tolerant parsing (dayfirst for BR-style input).
    for dayfirst in (False, True):
        try:
            ts = pd.to_datetime(text, dayfirst=dayfirst, errors="raise")
            return ts.date() if isinstance(ts, pd.Timestamp) else None
        except (ValueError, TypeError):
            continue
    return None
