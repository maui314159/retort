"""Multi-format date parsing for the Brazilian soccer datasets.

The source CSVs use three different date conventions (see the spec's
"Data Quality Notes"):

* ISO with time:      ``2012-05-19 18:30:00``
* ISO date only:      ``2023-09-24``
* Brazilian format:   ``29/03/2003`` (DD/MM/YYYY, sometimes with a time)

This module normalises all of them to :class:`datetime.date` objects.
"""

from __future__ import annotations

from datetime import date, datetime

# Formats are tried in order; the first that parses wins.
_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)

#: Sentinel values found in the raw data for missing datetimes.
_MISSING = {"", "na", "n/a", "-", "none", "null", "tbd"}


def parse_date(value: str | None) -> date | None:
    """Parse a date string in any of the dataset formats.

    Returns ``None`` when the value is missing or unparseable, so callers
    must treat ``None`` as "date unknown" rather than raising.
    """
    if not value:
        return None
    text = value.strip()
    if text.lower() in _MISSING:
        return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: the leading ISO portion, e.g. "2012-05-19 18:30:00"
    # already covered above, but guard against other stray variants.
    iso_head = text[:10]
    try:
        return datetime.strptime(iso_head, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_season(value: str | None) -> int | None:
    """Parse a season/year column value to an int (``None`` if missing)."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    season = int(digits)
    # Sanity: plausible season years in these datasets.
    if 1990 <= season <= 2100:
        return season
    return None


def parse_int(value: str | None) -> int | None:
    """Parse a goal/stat column value to an int (``None`` if missing).

    Handles the sentinels used by the raw data (``NA``, ``-``) and float
    formatted numbers (``"2.0"``).
    """
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def iso(day: date | None) -> str:
    """Format a date as ``YYYY-MM-DD`` (``"unknown date"`` if missing)."""
    return day.isoformat() if day else "unknown date"


__all__ = ["parse_date", "parse_season", "parse_int", "iso"]
