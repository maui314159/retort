"""
Context
=======
Module: brazilian_soccer_mcp.normalize
Purpose: Canonicalize the wildly inconsistent team-name strings found across the
         five Brazilian-soccer match CSVs so that the same club always maps to a
         single key regardless of source spelling.

Why this exists
---------------
The datasets encode the same club many different ways:
  - state suffix variants:   "Palmeiras-SP", "Palmeiras - SP", "Palmeiras"
  - country suffix variants: "Nacional (URU)", "Nacional-URU"
  - accent variants:         "Grêmio" vs "Gremio", "São Paulo" vs "Sao Paulo"
  - case variants:           "ABC - RN" vs "Abc - RN"
A naive equality match would treat these as distinct teams and shatter every
head-to-head / standings calculation. We therefore reduce each raw name to a
deaccented, lowercased *base key* (suffix stripped) plus a separately retained
*state/region* token used only to disambiguate genuine collisions
(e.g. Atlético-MG vs Atlético-PR).

Design notes
------------
- Pure functions, no I/O, no pandas dependency: cheap to call per-row and trivial
  to unit-test.
- We avoid regex compilation per call by hoisting the compiled patterns to module
  scope. No per-call allocation beyond the result string.
"""

from __future__ import annotations

import re
import unicodedata

# A trailing region/state/country marker. Captures things like:
#   "-SP"  " - SP"  " (URU)"  "-URU"  " - MG"
# Two-or-three-letter uppercase token after a dash or inside parens at end.
_SUFFIX_RE = re.compile(
    r"\s*(?:[-(\u2013]\s*|\(\s*)([A-Za-z]{2,3})\s*\)?\s*$"
)

# Collapse internal whitespace runs.
_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Return *text* with combining accent marks removed (NFKD fold)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def split_suffix(raw: str) -> tuple[str, str | None]:
    """Split a raw team name into ``(base, region)``.

    ``region`` is the uppercased 2-3 letter state/country token when present,
    else ``None``. The base retains original accents/case (callers decide how to
    fold it). Examples::

        "Palmeiras-SP"        -> ("Palmeiras", "SP")
        "Nacional (URU)"      -> ("Nacional", "URU")
        "América - MG"        -> ("América", "MG")
        "Flamengo"            -> ("Flamengo", None)
    """
    s = raw.strip().strip('"').strip()
    m = _SUFFIX_RE.search(s)
    if m:
        region = m.group(1).upper()
        base = s[: m.start()].strip()
        # Guard against eating a real word that merely *looks* like a token,
        # e.g. a one-token name shorter than the match leaving an empty base.
        if base:
            return base, region
    return s, None


def base_key(raw: str) -> str:
    """Suffix-stripped, deaccented, lowercased, whitespace-collapsed base name.

    This is the *display-agnostic* base WITHOUT the state/country token, used for
    tolerant user-query matching. NOTE: distinct clubs sharing a base
    (Atlético-MG vs Atlético-PR) collapse here — use :func:`team_key` for
    identity/grouping. Examples::

        "Grêmio-RS"    -> "gremio"
        "Sao Paulo-SP" -> "sao paulo"
        "São Paulo"    -> "sao paulo"
    """
    base, _ = split_suffix(raw)
    folded = strip_accents(base).lower()
    folded = folded.replace(".", " ").replace("/", " ")
    return _WS_RE.sub(" ", folded).strip()


def team_key(raw: str) -> str:
    """Canonical *identity* key: base plus state/country token when present.

    Unlike :func:`base_key`, this keeps distinct same-base clubs separate, so it
    is the correct key for deduplication and standings/head-to-head grouping.
    Examples::

        "Atletico-MG"  -> "atletico|mg"
        "Atletico-PR"  -> "atletico|pr"
        "Flamengo-RJ"  -> "flamengo|rj"
        "Flamengo"     -> "flamengo"   (no suffix -> base only)
    """
    base, region = split_suffix(raw)
    bkey = base_key(raw)
    return f"{bkey}|{region.lower()}" if region else bkey


def query_key(raw: str) -> str:
    """Canonical key for a *user query* term. Identical folding to ``base_key``
    but tolerant of a bare name with no suffix (the common case for questions
    like "Flamengo")."""
    return base_key(raw)


def matches(query: str, team_raw: str) -> bool:
    """True when a user *query* term refers to the given raw team name.

    Matching is bidirectional-substring on the folded base key so that
    "Palmeiras" matches "Palmeiras-SP" and "Atletico Mineiro" matches
    "Atlético - MG". Exact key match always wins; substring is the fallback for
    partial names. Empty queries never match.
    """
    q = query_key(query)
    if not q:
        return False
    t = base_key(team_raw)
    if q == t:
        return True
    return q in t or t in q
