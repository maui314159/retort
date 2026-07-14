"""Normalization helpers for Brazilian soccer data.

Context: The six provided Kaggle datasets use inconsistent conventions for
team names, competition labels and dates (see TASK.md "Data Quality Notes").
This module centralizes the canonicalization so every query layer can match
records across files reliably.

    * Team names arrive with state suffixes ("Palmeiras-SP"), accents
      ("São Paulo"), full legal names ("Sport Club Corinthians Paulista") and
      extra parenthetical notes. We reduce them to a lowercase, de-accented
      base token plus an optional state token.
    * Dates arrive as ISO ("2023-09-24"), ISO with time
      ("2012-05-19 18:30:00") or Brazilian DD/MM/YYYY ("29/03/2003").
    * Competition labels are mapped to a small canonical set so that
      "Brasileirão", "Serie A" and the historical file all answer to the
      same query.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Known Brazilian state abbreviations used as team suffixes in the match data.
STATE_ABBREVS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

# Suffixes commonly appended to club names in Portuguese source data; these
# are stripped so "Sport Club Corinthians Paulista" matches "Corinthians".
CLUB_NOISE_SUFFIXES = (
    "futebol clube", "f.c.", "fc", "sport club", "s.c.", "sc",
    "esporte clube", "e.c.", "ec", "clube de regatas", "cr",
    "athletico", "atletico",
)

_STATE_SUFFIX_RE = re.compile(r"\s*[-–—]\s*([A-Z]{2})\s*$")
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")


def deaccent(text: str) -> str:
    """Return *text* with diacritics folded to ASCII (NFD decomposition)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _strip_state(raw: str) -> tuple[str, Optional[str]]:
    """Split a trailing ``-UF`` state token, returning (base, state|None)."""
    match = _STATE_SUFFIX_RE.search(raw)
    if match and match.group(1) in STATE_ABBREVS:
        state = match.group(1)
        base = raw[: match.start()].strip()
        return base, state
    return raw.strip(), None


def normalize_team(raw: str) -> tuple[str, Optional[str]]:
    """Canonicalize a team name to ``(base_key, state)``.

    ``base_key`` is lowercase, de-accented, parenthetical-free and without a
    state suffix. ``state`` is the two-letter UF when one was present.
    """
    if raw is None:
        return "", None
    name = str(raw).strip()
    name = _PAREN_RE.sub(" ", name).strip()
    # Handle the space-separated form "Botafogo RJ" / "Vasco Da Gama RJ"
    # used by BR-Football-Dataset in addition to the dash form "Vasco-RJ".
    sp_match = re.search(r"\s+([A-Z]{2})\s*$", name)
    if sp_match and sp_match.group(1) in STATE_ABBREVS:
        name = name[: sp_match.start()].rstrip() + "-" + sp_match.group(1)
    base, state = _strip_state(name)
    base = deaccent(base).lower()
    # Collapse the " - " form sometimes written as "América - MG".
    base = re.sub(r"\s*-\s*$", "", base).strip()
    # Strip trailing noise words so full legal names collapse to the common
    # short form used by the match files.
    tokens = base.split()
    while len(tokens) > 1 and " ".join(tokens[-2:]) in CLUB_NOISE_SUFFIXES:
        tokens = tokens[:-2]
    while tokens and tokens[-1] in {"fc", "sc", "ec", "cr", "f.c.", "s.c.",
                                    "e.c."}:
        tokens.pop()
    base = " ".join(tokens).strip()
    return base, state


def team_key(raw: str) -> str:
    """Return just the base key for a team name (no state)."""
    return normalize_team(raw)[0]


def team_display(raw: str) -> str:
    """Return a clean human-readable team label (no parenthetical clutter)."""
    if raw is None:
        return ""
    name = _PAREN_RE.sub(" ", str(raw)).strip()
    base, state = _strip_state(name)
    # Title-case the de-accented base but keep the original accents when the
    # name is already short and clean.
    if " " not in base and len(base) <= 24:
        return name
    return base


# Canonical competition labels and the aliases that map to each.
COMPETITION_ALIASES: dict[str, str] = {
    "brasileirao": "Brasileirão Serie A",
    "brasileirão": "Brasileirão Serie A",
    "serie a": "Brasileirão Serie A",
    "serie a (brasileirao)": "Brasileirão Serie A",
    "campeonato brasileiro": "Brasileirão Serie A",
    "serie b": "Serie B",
    "serie c": "Serie C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "copa do brazil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "historical brasileirao": "Brasileirão (Historical)",
    "historico": "Brasileirão (Historical)",
}

CANONICAL_COMPETITIONS = tuple(dict.fromkeys(COMPETITION_ALIASES.values()))


def normalize_competition(raw: Optional[str]) -> str:
    """Map a competition label to its canonical form.

    Unknown labels are de-accented and title-cased but returned as-is so the
    caller can still see what was provided.
    """
    if raw is None:
        return ""
    key = deaccent(str(raw)).strip().lower()
    if key in COMPETITION_ALIASES:
        return COMPETITION_ALIASES[key]
    return str(raw).strip()


def parse_date(raw) -> Optional[date]:
    """Parse a date from ISO, ISO+time, or Brazilian DD/MM/YYYY formats."""
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    text = str(raw).strip()
    if not text:
        return None
    # ISO 8601: "2023-09-24" or "2012-05-19 18:30:00"
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)),
                        int(iso_match.group(3)))
        except ValueError:
            return None
    # Brazilian: "29/03/2003"
    br_match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if br_match:
        try:
            return date(int(br_match.group(3)), int(br_match.group(2)),
                        int(br_match.group(1)))
        except ValueError:
            return None
    return None


def to_int(value) -> Optional[int]:
    """Coerce a goal/corner cell (int, float, numeric string) to int."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
