"""Normalization helpers: unicode text, dates and team names.

The datasets mix naming conventions ("Palmeiras-SP", "Palmeiras",
"São Paulo-SP", "Sao Paulo", "Sport Club do Recife", "A.s.a. - AL") and
date formats ("2023-09-24", "29/03/2003", "2012-05-19 18:30:00").
This module provides deterministic normalization so that lookups and
cross-file joins behave consistently.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# All 27 Brazilian federative-unit (UF) abbreviations.
BRAZILIAN_UFS = frozenset(
    "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
)

# Country codes used as suffixes in the Libertadores file ("Barcelona-EQU").
FOREIGN_COUNTRY_CODES = {
    "ARG": "Argentina",
    "BOL": "Bolivia",
    "CHI": "Chile",
    "COL": "Colombia",
    "ECU": "Ecuador",
    "EQU": "Ecuador",
    "MEX": "Mexico",
    "PAR": "Paraguay",
    "PER": "Peru",
    "URU": "Uruguay",
    "VEN": "Venezuela",
    "USA": "United States",
    "JPN": "Japan",
}

_WS_RE = re.compile(r"\s+")
# Remove periods without introducing spaces so "A.s.a." -> "asa".
_DOT_RE = re.compile(r"(?<=\w)\.(?=\w)")
# Any remaining punctuation becomes a space separator.
_PUNCT_RE = re.compile(r"[^\w\s]")


def strip_accents(text: str) -> str:
    """Convert accented characters to their ASCII equivalents (NFKD)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def normalize_text(text: str) -> str:
    """Aggressively normalize a team/player/club name to a matching key.

    Steps: unicode NFKD accent stripping, lowercasing, intra-word dot removal
    ("A.s.a." -> "asa"), remaining punctuation to spaces, whitespace collapse.
    Parentheses become spaces so their content is kept as words ("Nacional
    (URU)" -> "nacional uru") which keeps same-named foreign clubs distinct.
    """
    s = strip_accents(text or "").lower().strip()
    s = _DOT_RE.sub("", s)
    s = s.replace("(", " ").replace(")", " ")
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def split_state_suffix(key: str) -> tuple[str, str | None]:
    """Split a trailing Brazilian UF token off a normalized key.

    ("atletico pr", ) -> ("atletico", "PR"); ("flamengo", ) -> ("flamengo", None).
    Foreign country codes (URU, PAR, EQU...) are never split off.
    """
    tokens = key.split()
    if len(tokens) >= 2 and tokens[-1].upper() in BRAZILIAN_UFS:
        return " ".join(tokens[:-1]), tokens[-1].upper()
    return key, None


def normalized_sort_key(text: str) -> str:
    """Sort-friendly normalized form of arbitrary text."""
    return normalize_text(text)


def parse_datetime(value: str) -> tuple[date | None, str | None]:
    """Parse the date formats used across the datasets.

    Supported: "2023-09-24", "2012-05-19 18:30:00", "29/03/2003",
    "29/03/2003 16:00". Returns (date, time-or-None); unparseable input
    yields (None, None).
    """
    if not value or not value.strip():
        return None, None
    raw = value.strip()
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.date(), dt.strftime("%H:%M") if "%H" in fmt else None
        except ValueError:
            continue
    # Fallback: try to salvage at least the date portion.
    head = raw.split()[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(head, fmt).date(), None
        except ValueError:
            continue
    return None, None


def parse_int(value) -> int | None:
    """Parse an integer, tolerating 'NA', '', None, '2.0' and whitespace."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"NA", "N/A", "NULL", "NONE", "-"}:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def parse_money_eur(value: str) -> int | None:
    """Parse FIFA money strings like '€110.5M' / '€565K' into whole euros."""
    if not value:
        return None
    s = str(value).replace("€", "").strip().upper()
    m = re.match(r"^([\d.]+)\s*([KM]?)$", s)
    if not m:
        return None
    amount = float(m.group(1))
    multiplier = {"K": 1_000, "M": 1_000_000}.get(m.group(2), 1)
    return int(amount * multiplier)
