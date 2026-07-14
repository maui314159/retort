"""
Context
=======
Module: brazilian_soccer_mcp.normalize

Brazilian soccer datasets name the same club many different ways, and the
differences are load-bearing for cross-file deduplication and team queries:

    "Palmeiras-SP" / "Palmeiras" / "Palmeiras SP"   -> same club
    "Botafogo-RJ"  / "Botafogo RJ" / "Botafogo"     -> same club
    "Vasco"        / "Vasco da Gama-RJ"             -> same club
    "Atletico-MG"  / "Atletico Mineiro"            -> Atlético Mineiro
    "Atletico-GO"  / "Atletico Goianiense"         -> a *different* club
    "Athletico-PR" / "Atletico Paranaense"         -> a *third* club
    "America-MG"   vs "America-RN"                 -> two different clubs

So the two-letter trailing state code is sometimes redundant noise
("Botafogo-RJ") and sometimes the only discriminator ("Atletico-MG" vs
"Atletico-GO"). A blind "strip the suffix" rule merges clubs that must stay
apart. This module therefore matches via:

- `strip_affixes` : human-readable display name (drops trailing "- MG" /
                    "(URU)" markers) - presentation only.
- `canonical`     : the matching/dedup key. Folds accents+case+punctuation,
                    then resolves through a curated `_ALIASES` table BEFORE
                    falling back to dropping a redundant trailing state code.
                    Clubs the state distinguishes (the Atléticos, the
                    Américas) are pinned in `_ALIASES` so they never hit the
                    fallback and never collide.
- `parse_date`    : tolerant parser for the ISO / ISO+time / DD-MM-YYYY
                    formats present across the files.

Keys are precomputed once at load time (see data_loader) so query-time
matching is a plain string compare.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# Trailing " - MG", "-SP" state markers and "(URU)" country markers, for the
# DISPLAY name only. The matching key (canonical) handles states differently.
_STATE_SUFFIX = re.compile(r"\s*-\s*[A-Za-z]{2}\s*$")
_PAREN_SUFFIX = re.compile(r"\s*\([^)]*\)\s*$")

# The 26 Brazilian states + Distrito Federal. Used to recognise a trailing
# 2-letter token as a (usually redundant) state code in the canonical key.
_UF = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}

# Curated alias table: normalised spelling -> canonical club key.
#
# Two jobs:
#   1. Pin clubs the state code *discriminates* so the redundant-suffix
#      fallback never merges them (the Atléticos; América-MG vs América-RN).
#   2. Unify spelling variants the fallback can't (prefix words like "EC",
#      "FC", sponsor names) onto one key.
# Every entry's key is the output of `_normkey` (accent-folded, lowercased,
# punctuation collapsed to single spaces). Clubs whose only variation is a
# redundant trailing state code (Flamengo-RJ, Palmeiras-SP, ...) need no
# entry - the fallback strips the code and they converge automatically.
_ALIASES: dict[str, str] = {
    # --- Atlético clubs: state code is the discriminator -----------------
    "atletico mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "atletico mineiro mg": "atletico mineiro",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "athletico paranaense": "athletico paranaense",
    # --- América clubs: keep MG and RN distinct (block suffix fallback) --
    "america mg": "america mg",
    "america rn": "america rn",
    # --- variants the fallback can't unify -------------------------------
    "vasco": "vasco da gama",
    "vasco da gama": "vasco da gama",
    "sport": "sport recife",
    "sport recife": "sport recife",
    "ec bahia": "bahia",
    "ec juventude": "juventude",
    "santa cruz fc": "santa cruz",
    "fortaleza fc": "fortaleza",
    "red bull bragantino": "bragantino",
}


def _strip_accents(text: str) -> str:
    """Fold accented characters to ASCII (São -> Sao, Grêmio -> Gremio)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def strip_affixes(name: str) -> str:
    """Return a clean DISPLAY name with trailing state/country markers removed.

    "Palmeiras-SP"   -> "Palmeiras"
    "América - MG"   -> "América"
    "Nacional (URU)" -> "Nacional"

    Accents and capitalisation are preserved for display.
    """
    if not isinstance(name, str):
        return ""
    out = name.strip()
    changed = True
    while changed:
        changed = False
        new = _PAREN_SUFFIX.sub("", out)
        if new != out:
            out, changed = new, True
        new = _STATE_SUFFIX.sub("", out)
        if new != out:
            out, changed = new, True
        # Also drop a trailing *space*-separated state code ("Botafogo RJ"),
        # but only when it is a real UF so we never eat a club's last word.
        parts = out.split()
        if len(parts) > 1 and parts[-1].lower() in _UF:
            out, changed = " ".join(parts[:-1]), True
    return out.strip(" -")


def _normkey(name: str) -> str:
    """Fold to a bare lowercase ascii key: punctuation -> single spaces."""
    base = _strip_accents(name).lower()
    return re.sub(r"[^a-z0-9]+", " ", base).strip()


def canonical(name: str) -> str:
    """Matching/dedup key for a club name (see module docstring).

        "Palmeiras-SP"       -> "palmeiras"
        "Botafogo RJ"        -> "botafogo"
        "Atletico-MG"        -> "atletico mineiro"
        "Atletico-GO"        -> "atletico goianiense"
        "Vasco"              -> "vasco da gama"
        "Sport Club Recife"  -> "sport recife"
    """
    if not isinstance(name, str):
        return ""
    key = _normkey(name)
    if not key:
        return ""
    # 1. Exact alias (handles state-discriminated and prefixed spellings).
    if key in _ALIASES:
        return _ALIASES[key]
    # 2. Redundant trailing state code: drop it, then re-check aliases.
    tokens = key.split()
    if len(tokens) > 1 and tokens[-1] in _UF:
        stripped = " ".join(tokens[:-1])
        return _ALIASES.get(stripped, stripped)
    return key


def names_match(query: str, candidate: str) -> bool:
    """True if `query` refers to `candidate` (canonical substring match).

    Substring (not just equality) so "Atletico" loosely finds the Atléticos
    and "Palmeiras" finds "Palmeiras". Either side may be the substring.
    """
    q = canonical(query)
    c = canonical(candidate)
    if not q or not c:
        return False
    return q == c or q in c or c in q


_BR_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def parse_date(value: object) -> date | None:
    """Parse the date formats found across the datasets.

    Handles:
      "2023-09-24"            ISO
      "2012-05-19 18:30:00"   ISO + time
      "29/03/2003"            Brazilian DD/MM/YYYY
    Returns a `datetime.date`, or None when unparseable / missing.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None

    m = _BR_DATE.match(text)
    if m:
        day, month, year = (int(g) for g in m.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    head = text.split(" ")[0].split("T")[0]
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None
