"""Normalisation helpers for Brazilian soccer data.

CONTEXT
-------
The bundled CSV files come from five different Kaggle datasets and use
inconsistent conventions for the same entities:

* ``Palmeiras-SP`` (Brasileirão), ``América - MG`` (Copa do Brasil) and
  ``Barcelona-EQU`` (Libertadores) carry a trailing state/country suffix.
* The extended-stats file uses bare names (``Palmeiras``) for unambiguous
  clubs but spelled-out disambiguators (``Atletico Mineiro``,
  ``Botafogo RJ``) for ambiguous ones.
* Accents are kept in some files (``São Paulo``) and dropped in others
  (``Sao Paulo``).

Crucially, several short names are shared by *different* clubs that are
only disambiguated by their state — ``Atlético-MG`` (Atlético Mineiro)
vs ``Atlético-GO`` (Atlético Goianiense) vs ``Athletico-PR`` (Athletico
Paranaense).  Stripping the suffix would wrongly merge them, so the
canonical key **retains** the state token.  Equivalence between the
state-suffixed form (``flamengo rj``) and the bare form (``flamengo``)
is resolved through an alias map built in :func:`build_alias_map`.

Two names refer to the same team iff ``resolve_team_key`` agrees::

    resolve_team_key(map, "Palmeiras-SP") == resolve_team_key(map, "Palmeiras")
    resolve_team_key(map, "Atlético-MG") == resolve_team_key(map, "Atletico Mineiro")
    resolve_team_key(map, "Atlético-MG") != resolve_team_key(map, "Atletico-GO")
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Iterable

_BR_STATE_WORDS = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma",
    "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn",
    "rs", "ro", "rr", "sc", "sp", "se", "to",
}

# Trailing "-XX" / " - XX" state or country suffix (2-3 uppercase letters).
_SUFFIX_RE = re.compile(r"\s*-\s*([A-Z]{2,3})\s*$")
# Parenthetical notes: "Nacional (URU)", "Time (antigo ...)".
_PAREN_RE = re.compile(r"\s*\([^)]*\)")


def strip_accents(text: str) -> str:
    """Return *text* with combining diacritics removed (ASCII fold)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


_SMALL_WORDS = {"da", "de", "do", "dos", "das", "e", "del", "la"}


def titlecase_name(name: str) -> str:
    """Title-case a team name, preserving acronyms (``CSA``) and lowering
    Portuguese connectors (``da``, ``de``)."""
    words = str(name).split()
    out = []
    for i, w in enumerate(words):
        if w.isupper() and len(w) <= 4:
            out.append(w)
        elif w and w[0].isdigit():
            out.append(w)
        elif w.lower() in _SMALL_WORDS and i > 0:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def _split_suffix(s: str) -> tuple[str, str | None]:
    """Return (body, state) where *state* is the trailing suffix code or
    None.  Operates on the original-cased string so the [A-Z] class works."""
    m = _SUFFIX_RE.search(s)
    if m:
        return s[: m.start()].strip(), m.group(1)
    return s.strip(), None


# Common Brazilian club legal-form abbreviations that appear as a leading
# or trailing token ("EC Bahia", "Fortaleza FC", "4 de Julho EC").  They
# are stripped so the underlying club name matches across sources.
_CLUB_TOKENS = {"EC", "FC", "SC", "AC", "AA", "GE", "GR", "SE", "CE", "CA"}


def _strip_club_tokens(body: str) -> str:
    """Drop leading/trailing club legal-form tokens (EC, FC, SC, ...)."""
    parts = body.split()
    while parts and parts[0].upper() in _CLUB_TOKENS:
        parts.pop(0)
    while parts and parts[-1].upper() in _CLUB_TOKENS:
        parts.pop()
    return " ".join(parts)


def has_state_suffix(name) -> bool:
    """True if *name* carries a trailing ``-XX`` state/country suffix."""
    if name is None:
        return False
    return bool(_SUFFIX_RE.search(str(name)))


def canonical_key(name) -> str:
    """Reduce a team/club name to a stable matching key that RETAINS the
    state token.

    Examples::

        canonical_key("Palmeiras-SP")  == "palmeiras sp"
        canonical_key("América - MG")  == "america mg"
        canonical_key("Barcelona-EQU") == "barcelona equ"
        canonical_key("São Paulo")     == "sao paulo"
        canonical_key("Botafogo RJ")   == "botafogo rj"
    """
    if name is None:
        return ""
    s = _PAREN_RE.sub("", str(name)).strip()
    body, state = _split_suffix(s)
    body = strip_accents(body).lower().strip()
    body = _strip_club_tokens(body)
    body = re.sub(r"\s+", " ", body).strip()
    if state:
        return f"{body} {state.lower()}"
    return body


def bare_key(name) -> str:
    """Canonical key with the state suffix stripped (used to detect
    ambiguity between same-named clubs from different states)."""
    if name is None:
        return ""
    s = _PAREN_RE.sub("", str(name)).strip()
    body, _ = _split_suffix(s)
    body = strip_accents(body).lower().strip()
    body = _strip_club_tokens(body)
    return re.sub(r"\s+", " ", body).strip()


def display_name(name) -> str:
    """Return a clean display name: accents kept, suffix/notes dropped,
    and a trailing bare state word (``Vasco da Gama RJ``) removed."""
    if name is None:
        return ""
    s = _PAREN_RE.sub("", str(name)).strip()
    body, _ = _split_suffix(s)
    body = _strip_club_tokens(body)
    body = re.sub(r"\s+", " ", body).strip()
    # Drop a trailing bare 2-letter Brazilian state word, e.g. "RJ".
    parts = body.split()
    if len(parts) >= 2 and parts[-1].lower() in _BR_STATE_WORDS and len(parts[-1]) == 2:
        body = " ".join(parts[:-1])
    return titlecase_name(body)


# --- Alias resolution -----------------------------------------------------

# Curated map of spelled-out / bare ambiguous forms -> state-retaining id.
# These cover the well-known Brazilian clubs whose names collide across
# states and whose extended-stats spellings differ from the suffix form.
_CURATED_ALIASES = {
    # Spelled-out forms (extended-stats dataset) -> state id.
    "atletico mineiro": "atletico mg",
    "atletico goianiense": "atletico go",
    "atletico paranaense": "atletico pr",
    "athletico paranaense": "atletico pr",
    "athletico pr": "atletico pr",
    "atletico acreano": "atletico ac",
    "atletico alagoinhas": "atletico ba",
    "sport recife": "sport pe",
    "america fc natal": "america rn",
    "red bull bragantino": "bragantino sp",
    "vasco": "vasco da gama rj",
    # Bare ambiguous names -> the historically prominent club, so that a
    # user typing just "Botafogo" or "Santos" resolves to the famous one.
    "botafogo": "botafogo rj",
    "santos": "santos sp",
    "internacional": "internacional rs",
    "santa cruz": "santa cruz pe",
    "juventude": "juventude rs",
    "bragantino": "bragantino sp",
    "america": "america mg",
    "atletico": "atletico mg",
    "athletico": "atletico pr",
    "vitoria": "vitoria ba",
    "flamengo": "flamengo rj",
    "guarani": "guarani sp",
    "operario": "operario ms",
    "rio branco": "rio branco ac",
    "sao raimundo": "sao raimundo pa",
    "ypiranga": "ypiranga rs",
    "comercial": "comercial ms",
    "abc": "abc rn",
}

# Display-name overrides for ids whose most common spelling is an ambiguous
# bare name (e.g. "Atlético"); use the full disambiguated name instead.
DISPLAY_OVERRIDES = {
    "atletico mg": "Atlético Mineiro",
    "atletico pr": "Athletico Paranaense",
    "atletico go": "Atlético Goianiense",
    "atletico ac": "Atlético Acreano",
    "atletico ba": "Atlético de Alagoinhas",
    "atletico es": "Atlético Esporte Clube",
    "america mg": "América Mineiro",
    "america rn": "América Natal",
    "sport pe": "Sport Recife",
}


def build_alias_map(names: Iterable) -> dict[str, str]:
    """Build an alias map from the set of raw team *names*.

    The map resolves any spelling to a state-retaining canonical id:

    * every state-suffixed name maps to itself,
    * a bare name that corresponds to exactly ONE state-suffixed club is
      mapped to that club's id (auto-derivation, e.g. ``palmeiras`` ->
      ``palmeiras sp``),
    * curated entries override for spelled-out / ambiguous cases.
    """
    alias_map: dict[str, str] = {}
    by_bare: dict[str, list[str]] = {}

    for name in names:
        if name is None:
            continue
        s = str(name).strip()
        if not s:
            continue
        if has_state_suffix(s):
            sid = canonical_key(s)
            alias_map.setdefault(sid, sid)
            by_bare.setdefault(bare_key(s), []).append(sid)
        else:
            # Non-suffixed spelling: identity unless a curated/auto entry
            # resolves it later.
            k = canonical_key(s)
            alias_map.setdefault(k, k)

    # Auto-derive bare -> state id for unambiguous clubs.
    for bare, sids in by_bare.items():
        unique = sorted(set(sids))
        if len(unique) == 1:
            alias_map[bare] = unique[0]

    # Curated overrides (applied last so they win).
    alias_map.update(_CURATED_ALIASES)
    return alias_map


def resolve_team_key(alias_map: dict[str, str], name) -> str:
    """Resolve a team name (raw or user-typed) to its canonical id."""
    key = canonical_key(name)
    if key in alias_map:
        return alias_map[key]
    # Fall back to the bare form (e.g. user typed "Atletico Mineiro" which
    # canonical_key keeps as-is; curated map covers the common cases).
    bk = bare_key(name)
    return alias_map.get(bk, key)


# --- Date parsing ---------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")


def parse_date(value) -> datetime | None:
    """Parse the date/datetime strings found across the datasets.

    Handles ISO datetimes (``2012-05-19 18:30:00``), plain ISO dates
    (``2023-09-24``) and Brazilian ``DD/MM/YYYY`` dates.  Returns ``None``
    for missing/unparseable input.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# --- Competition label normalisation -------------------------------------

_COMPETITION_ALIASES = {
    "brasileirao": "Brasileirão Serie A",
    "brasileirão": "Brasileirão Serie A",
    "serie a": "Brasileirão Serie A",
    "série a": "Brasileirão Serie A",
    "serie b": "Brasileirão Serie B",
    "série b": "Brasileirão Serie B",
    "serie c": "Brasileirão Serie C",
    "série c": "Brasileirão Serie C",
    "campeonato brasileiro": "Brasileirão Serie A",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "copa do brazil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "copa conmebol libertadores": "Copa Libertadores",
}


def canonical_competition(value) -> str | None:
    """Normalise a user-supplied competition name to a canonical label."""
    if value is None:
        return None
    key = strip_accents(str(value)).lower().strip()
    if not key:
        return None
    return _COMPETITION_ALIASES.get(key, str(value).strip())


# --- Player position groups ----------------------------------------------

POSITION_GROUPS = {
    "GK": {"GK"},
    "DEF": {"CB", "RCB", "LCB", "LB", "RB", "LWB", "RWB"},
    "MID": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM",
            "LM", "RM"},
    "FWD": {"ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"},
}


def position_group(position) -> str | None:
    """Map a granular FIFA position code to a broad group (GK/DEF/MID/FWD)."""
    if position is None or str(position).strip() == "":
        return None
    pos = str(position).strip().upper()
    for group, codes in POSITION_GROUPS.items():
        if pos in codes:
            return group
    return None
