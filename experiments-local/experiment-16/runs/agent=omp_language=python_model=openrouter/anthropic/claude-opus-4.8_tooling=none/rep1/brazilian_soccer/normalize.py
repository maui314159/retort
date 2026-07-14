"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : brazilian_soccer.normalize
Purpose : Normalization helpers shared by the loader and the graph so that the
          many spelling/format variations across the six datasets collapse to a
          single canonical key for matching.

Key insight on team names: the trailing state/country code is a *disambiguator*,
not decoration. "Atlético-MG", "Atlético-PR" and "Atlético-GO" are three
different clubs that share the base name "atletico". So the canonical key keeps
the code: ``base`` when unknown, ``base|state`` when known. State comes from an
explicit column when the source has one (Brasileirão home_team_state, historical
Mandante_UF) or from the name suffix otherwise (Copa do Brasil "América - MG",
Libertadores "Nacional (URU)"). A query for the bare "Flamengo" is resolved to
the full key "flamengo|rj" by the graph's alias layer.

Also handles (per the spec's "Data Quality Notes"):
  * Accents ("Grêmio" / "Gremio"), long official names, redundant whitespace.
  * Date formats: ISO, ISO+time, Brazilian DD/MM/YYYY, and the 2003.01.0001 id.
  * Scores stored as int, float ("1.0"), str ("2"), or missing ("-", "").

All functions are pure and computed once at load time.
================================================================================
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional, Tuple

# Trailing " - SP", "-SP", " (URU)", " - MG" style location qualifiers, with the
# code captured so it can be folded into the key instead of discarded.
_STATE_SUFFIX = re.compile(r"\s*[-(]\s*([A-Za-zÀ-ÿ]{2,3})\s*\)?\s*$")
# Parenthetical clarifications, e.g. "(antigo Esporte Clube Barreira)".
_PARENS = re.compile(r"\s*\([^)]*\)")
_WS = re.compile(r"\s+")

# Official-name -> short-name canonicalizations (keys already accent-stripped,
# lower-cased and suffix-free).
_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "sao paulo futebol clube": "sao paulo",
    "santos futebol clube": "santos",
    "gremio foot-ball porto alegrense": "gremio",
    "fortaleza esporte clube": "fortaleza",
    # Cross-source spelling variants for the same club. State codes keep these
    # from colliding with genuinely different clubs (e.g. atletico|mg).
    "athletico": "atletico",
    "vasco da gama": "vasco",
}

# Separator between base name and state code in a canonical key. Chosen because
# it never appears in a team name.
_SEP = "|"


def strip_accents(text: str) -> str:
    """Return *text* with combining accents removed (NFD decomposition)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def split_team(raw: object) -> Tuple[str, Optional[str]]:
    """Split a raw team cell into (base_key, state_code_or_None).

    base_key is accent-stripped, lower-cased, suffix-free and alias-resolved.
    state_code is the lower-cased 2-3 letter suffix when the name carries one.
    """
    if raw is None:
        return "", None
    name = str(raw).strip()
    if not name or name.lower() == "nan":
        return "", None
    name = _PARENS.sub("", name) if "(" in name else name
    state: Optional[str] = None
    m = _STATE_SUFFIX.search(name)
    if m:
        state = strip_accents(m.group(1)).lower()
        name = name[: m.start()]
    base = _WS.sub(" ", strip_accents(name).lower()).strip()
    base = _ALIASES.get(base, base)
    return base, state


def team_key(raw: object) -> str:
    """Canonical, state-aware key for a team, derived from the name only.

    The state code comes from the name suffix ("Atletico-MG" -> "atletico|mg"),
    which is reliable across every dataset and already distinguishes genuinely
    different clubs that share a base name. A dedicated state *column* is
    deliberately NOT used: in the historical file it is mislabeled for some
    home rows (e.g. Vitória/BA recorded as ES at home), which would split one
    club into two. Returns ``base`` when the name carries no suffix, else
    ``base|state``.
    """
    base, suffix_state = split_team(raw)
    if not base:
        return ""
    return f"{base}{_SEP}{suffix_state}" if suffix_state else base


def base_of(key: str) -> str:
    """Return the base-name portion of a canonical key (drops the state code)."""
    return key.split(_SEP, 1)[0]


def normalize_team(raw: object) -> str:
    """Base-name key (no state). Used for player clubs and bare-name display."""
    return split_team(raw)[0]


def display_team(raw: object) -> str:
    """Human-readable team name: strip suffixes/parentheticals, keep accents."""
    if raw is None:
        return ""
    name = str(raw).strip()
    if not name or name.lower() == "nan":
        return ""
    name = _PARENS.sub("", name) if "(" in name else name
    name = _STATE_SUFFIX.sub("", name)
    return _WS.sub(" ", name).strip()


def parse_score(raw: object) -> Optional[int]:
    """Parse a goal value that may be int, float, "2", "1.0", "-", "" or NaN."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, float):
        return None if raw != raw else int(raw)  # NaN check
    text = str(raw).strip()
    if not text or text in {"-", "nan", "NaN", "None"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_date(raw: object) -> Optional[date]:
    """Parse ISO, ISO+time, Brazilian (DD/MM/YYYY) and 2003.01.0001 ids."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None
    head = text.split(" ", 1)[0].split("T", 1)[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None
