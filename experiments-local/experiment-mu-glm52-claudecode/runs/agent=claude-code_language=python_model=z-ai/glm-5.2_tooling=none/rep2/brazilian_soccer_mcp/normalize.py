"""Normalization helpers for team names and dates.

Context
-------
The six Kaggle CSV files use different team-naming conventions and date formats
(see TASK.md "Data Quality Notes"):

* Team names may carry a state suffix such as ``"Palmeiras-SP"`` / ``"América - MG"``,
  a parenthetical qualifier such as ``"Nacional (URU)"`` or a verbose variant such
  as ``"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"``.
* The BR-Football-Dataset writes names without accents (``"Sao Paulo"``) while the
  other datasets keep the Portuguese spelling (``"São Paulo"``).
* Dates appear as ISO ``"2023-09-24"``, ISO with time ``"2012-05-19 18:30:00"``
  and Brazilian ``"29/03/2003"``.

The functions below turn each of those variants into a canonical display name plus
an accent/case-insensitive match key so the same team in different files joins.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional, Tuple

# Two-letter Brazilian state codes used to strip the ``-SP`` / `` - MG`` suffix.
_STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Country codes seen in the Libertadores file, e.g. ``"Nacional (URU)"``.
_COUNTRY_CODES = {
    "URU", "EQU", "ARG", "CHI", "BOL", "PAR", "COL", "ECU", "VEN", "MEX",
    "PER", "BRA",
}

_PAREN_RE = re.compile(r"\([^)]*\)")
# Trailing " - SP" / "-SP" / " -RJ" (two-letter code, optionally in parens).
_SUFFIX_RE = re.compile(r"\s*[-–—]\s*([A-Z]{2})\s*$")
_MULTI_SPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return *text* with diacritics removed (NFD decomposition + combining strip)."""
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalize_team(name: str) -> str:
    """Canonicalize a team name for display.

    Strips parenthetical qualifiers, trailing state/country codes and extra
    whitespace.  ``"Palmeiras-SP"`` -> ``"Palmeiras"``; ``"América - MG"`` ->
    ``"América"``; ``"Nacional (URU)"`` -> ``"Nacional"``.
    """
    if name is None:
        return ""
    s = str(name).strip()
    # Drop parenthetical content (e.g. "(antigo Esporte Clube Barreira)", "(URU)").
    s = _PAREN_RE.sub("", s).strip()
    # Drop a trailing two-letter state/country code following a dash.
    m = _SUFFIX_RE.search(s)
    while m and m.group(1) in (_STATE_CODES | _COUNTRY_CODES):
        s = _SUFFIX_RE.sub("", s).strip()
        m = _SUFFIX_RE.search(s)
    s = _MULTI_SPACE_RE.sub(" ", s).strip()
    return s


def team_key(name: str) -> str:
    """Accent/case-insensitive match key used to join teams across files."""
    return strip_accents(normalize_team(name)).lower()


def normalize_team_pair(name: str) -> Tuple[str, str]:
    """Return ``(display_name, match_key)`` for *name*."""
    display = normalize_team(name)
    return display, team_key(display)


def parse_date(value) -> Optional[date]:
    """Parse a date from any of the formats used by the datasets.

    Accepts ``date``/``datetime`` objects directly, ISO strings
    (``"2023-09-24"`` / ``"2012-05-19 18:30:00"``) and Brazilian
    ``DD/MM/YYYY`` strings.  Returns ``None`` when the value is empty/invalid.
    """
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None
    # ISO with optional time.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # Brazilian DD/MM/YYYY (with optional time).
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # Pandas Timestamp fallback.
    try:
        return pd_to_date(s)  # type: ignore[name-defined]
    except Exception:
        return None


def parse_int(value) -> Optional[int]:
    """Parse *value* to ``int`` returning ``None`` for blanks / dashes / NaN."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value != value:  # NaN
            return None
        return int(value)
    s = str(value).strip()
    if not s or s in {"-", "nan", "None", "NaN"}:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _pd_to_date(s: str):
    import pandas as pd

    ts = pd.to_datetime(s, errors="coerce", dayfirst=False)
    if ts is None or (hasattr(ts, "isna") and ts.isna()):
        ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if ts is None or (hasattr(ts, "isna") and ts.isna()):
        return None
    return ts.date()


# Late-bound helper so ``parse_date`` does not import pandas at module load.
pd_to_date = _pd_to_date
