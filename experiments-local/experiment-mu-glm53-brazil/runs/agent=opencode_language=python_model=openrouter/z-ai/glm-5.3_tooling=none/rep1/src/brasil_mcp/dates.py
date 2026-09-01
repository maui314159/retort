"""Date and time parsing for the many formats found in the Brazilian soccer datasets.

Handled formats:
- ISO dates: "2023-09-24"
- ISO datetimes: "2012-05-19 18:30:00"
- Brazilian dates: "29/03/2003" (DD/MM/YYYY)
- Sentinel values ("NA", "-", empty) which map to None
"""

from __future__ import annotations

from datetime import date, datetime

_SENTINELS = {"", "na", "n/a", "-", "none", "null", "tbd"}

_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y/%m/%d",
)


def parse_date(value: object) -> date | None:
    """Parse a date from any format used by the datasets.

    Returns None for sentinel/invalid values instead of raising.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _SENTINELS:
        return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(value: object) -> str | None:
    """Parse a kick-off time string such as "20:30:00" or "16:00".

    Returns a normalized "HH:MM" string, or None for sentinel values.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _SENTINELS:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.strftime("%H:%M")
    return None


def to_year(value: object) -> int | None:
    """Parse a season year, tolerating sentinel values."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _SENTINELS:
        return None
    try:
        year = int(float(text))
    except ValueError:
        return None
    if 1900 <= year <= 2100:
        return year
    return None
