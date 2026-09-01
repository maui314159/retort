"""Multi-format date parsing for the Brazilian soccer datasets.

Observed formats across the six CSV files:
- ISO date:               "2023-09-24"
- ISO date + time:        "2012-05-19 18:30:00"
- Brazilian (BR) format:  "29/03/2003"
- Missing markers:        "NA", "-", ""
"""

from __future__ import annotations

import datetime as dt

_MISSING = {"", "na", "n/a", "-", "none", "null", "tbd"}

_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d/%m/%y",
)


def parse_date(value: str | None) -> dt.date | None:
    """Parse any date format used by the datasets; returns None when unknown."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    for fmt in _FORMATS:
        try:
            # naive parsing is intentional: source dates carry no timezone
            return dt.datetime.strptime(text, fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
    return None


def parse_int(value: str | None) -> int | None:
    """Parse goal counts and other integers; 'NA'/'-'/'' become None."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_money_eur(value: str | None) -> int | None:
    """Parse FIFA-style money strings like '€110.5M' or '€565K' into euros."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _MISSING:
        return None
    multiplier = 1
    body = text
    if body[-1] in "Kk":
        multiplier, body = 1_000, body[:-1]
    elif body[-1] in "Mm":
        multiplier, body = 1_000_000, body[:-1]
    try:
        return int(float(body.replace("€", "").replace(",", "")) * multiplier)
    except ValueError:
        return None


def to_iso(date: dt.date | None) -> str | None:
    return date.isoformat() if date else None
