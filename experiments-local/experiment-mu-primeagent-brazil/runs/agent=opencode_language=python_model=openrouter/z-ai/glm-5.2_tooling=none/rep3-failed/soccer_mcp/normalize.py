"""
Context
=======
Brazilian Soccer MCP Server - normalization utilities.

Part of the ``soccer_mcp`` package.  These helpers convert the heterogeneous
raw values found in the six Kaggle CSV sources (Brasileirao_Matches.csv,
Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv,
novo_campeonato_brasileiro.csv and fifa_data.csv) into a single canonical form
so that matches coming from different files can be joined consistently.

Design notes
------------
* Team names:
    - Parenthetical country codes are stripped and kept as the region:
      "Nacional (URU)" -> base "nacional", region "URU".
    - Trailing state/region suffixes are stripped and kept as the region:
      "Palmeiras-SP", "America - MG", "Barcelona-EQU" -> bases "palmeiras",
      "america", "barcelona" with regions "SP", "MG", "EQU".
    - Accents are folded (NFKD) so "Sao Paulo" and "Sao Paulo" match.
    - An alias table maps FIFA full names ("Atletico Mineiro") and spelling
      variants ("Athletico" -> "Atletico") to a canonical (base, region).
    - Stateless names (e.g. "Sao Paulo" with no suffix in the BR-Football
      dataset, or "Botafogo" in the historical file) are resolved to the most
      common NON-EMPTY region observed for that base across all sources, so the
      famous clubs (Flamengo-RJ) win over minor ones (Flamengo-PI).
    - The canonical key is ``base + region.lower()`` (e.g. "flamengorj").
* Dates: ISO datetime ("2012-05-19 18:30:00"), ISO date ("2023-09-24") and
  Brazilian format ("29/03/2003") are all normalized to ISO 8601 date strings
  ("YYYY-MM-DD").  Unparseable values become None.
* Goals: stored as strings ("3"), floats ("3.0") or numeric - all normalized
  to int.  Missing/invalid values become None.

The module exposes a :class:`TeamNormalizer` that must first observe every team
name (``observe``) and then be queried (``canonical`` / ``display``), plus the
standalone helpers :func:`parse_date`, :func:`to_int_goal` and
:func:`strip_accents`.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional, Tuple

__all__ = [
    "strip_accents",
    "parse_date",
    "to_int_goal",
    "TeamNormalizer",
]


def strip_accents(value: str) -> str:
    """Fold accented characters to their ASCII base (NFKD, drop combining marks)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch)
    )


# Aliases that map a full FIFA club name (or a spelling variant) -- after the
# state/region suffix has been removed -- to a canonical (base, region) tuple.
# The region is only injected when no explicit region was detected on the name,
# i.e. plain "Atletico Mineiro" -> ("atletico", "MG").
ALIASES: dict[str, Tuple[str, str]] = {
    "atleticomineiro": ("atletico", "MG"),
    "atleticoparanaense": ("atletico", "PR"),
    "athleticoparanaense": ("atletico", "PR"),
    "atleticogoianiense": ("atletico", "GO"),
    "sportrecife": ("sport", "PE"),
    "sportclubdorecife": ("sport", "PE"),
    "cearasportingclub": ("ceara", "CE"),
    "vascodagamarj": ("vascodagama", "RJ"),
    "vascodagama": ("vascodagama", "RJ"),
    "sccorinthianspaulista": ("corinthians", "SP"),
    "sportclubcorinthianspaulista": ("corinthians", "SP"),
}

# Spelling normalisation applied to the base key before alias lookup and before
# region counting.  "Athletico-PR" (post-2019 rename) is treated as the same
# base as "Atletico-PR".
BASE_FIXES: dict[str, str] = {"athletico": "atletico"}

# Curated display names with correct Portuguese accents / capitalisation for
# the most prominent clubs.  Keys are canonical keys (base + region.lower()).
# Anything not listed falls back to the most common raw variant observed.
DISPLAY_OVERRIDES: dict[str, str] = {
    "flamengorj": "Flamengo",
    "palmeirassp": "Palmeiras",
    "corinthianssp": "Corinthians",
    "saopaulosp": "Sao Paulo",
    "santossp": "Santos",
    "gremiors": "Gremio",
    "internacionalrs": "Internacional",
    "cruzeiromg": "Cruzeiro",
    "atleticomg": "Atletico-MG",
    "atleticopr": "Athletico-PR",
    "fluminenserj": "Fluminense",
    "botafogorj": "Botafogo",
    "vascodagamarj": "Vasco da Gama",
    "coritibapr": "Coritiba",
    "sportpe": "Sport",
    "cearace": "Ceara",
    "fortalezace": "Fortaleza",
    "bahiaba": "Bahia",
    "vitoriaba": "Vitoria",
    "goiasgo": "Goias",
    "avaisc": "Avai",
    "cuiabamt": "Cuiaba",
    "juventuders": "Juventude",
    "chapecoensesc": "Chapecoense",
    "figueirense": "Figueirense",
    "criciumasc": "Criciuma",
    "paranapr": "Parana",
    "bragantinio": "Bragantino",
    "redbullbragantinosp": "Red Bull Bragantino",
    "americamg": "America-MG",
    "americarn": "America-RN",
    "atleticogo": "Atletico-GO",
    "joinvillesc": "Joinville",
    "londrinapr": "Londrina",
    "paysandupa": "Paysandu",
    "remopa": "Remo",
    "csaal": "CSA",
    "crbal": "CRB",
    "nauticope": "Nautico",
    "saobentosp": "Sao Bento",
    "santoandresp": "Santo Andre",
    "portuguesasp": "Portuguesa",
    "guaranisp": "Guarani",
    "pontepretasp": "Ponte Preta",
    "ituanosp": "Ituano",
    "mirassolsp": "Mirassol",
    "novorizontinosp": "Novorizontino",
    "santacruzpe": "Santa Cruz",
    "abc": "ABC",
    "vitoria": "Vitoria",
    "operariopr": "Operario-PR",
    "athletico": "Athletico-PR",
}

_PAREN_RE = re.compile(r"\(\s*([A-Za-z]{2,3})\s*\)\s*$")
_SUFFIX_RE = re.compile(r"[\s\-]+([A-Za-z]{2,3})$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y")


def parse_date(value: Optional[str]) -> Optional[str]:
    """Parse a date/datetime string into an ISO ``YYYY-MM-DD`` string.

    Handles ISO datetime, ISO date and Brazilian ``DD/MM/YYYY`` formats.
    Returns ``None`` when the value is empty or cannot be parsed.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def to_int_goal(value) -> Optional[int]:
    """Coerce a goal value (str/int/float) to int, returning None if invalid."""
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


class TeamNormalizer:
    """Stateful normaliser for team/club names.

    Two phases:
      1. ``observe(name)`` is called for every team name across every source,
         accumulating region counts (non-empty regions only) and the raw
         display variants seen for each canonical key.
      2. ``canonical(name)`` / ``display(key)`` resolve names and render
         pretty display names.
    """

    def __init__(self) -> None:
        # base -> Counter(region -> count) for NON-EMPTY regions only.
        self.region_counts: dict[str, Counter] = defaultdict(Counter)
        # canonical_key -> Counter(raw_display_name -> count)
        self.display_names: dict[str, Counter] = defaultdict(Counter)
        self._finalized = False

    # ------------------------------------------------------------------ parse
    @staticmethod
    def parse(name: str) -> Tuple[str, str]:
        """Split a raw team name into ``(base_key, region)``.

        ``region`` is the empty string when none is detected.  Aliases that
        inject a region (e.g. "Atletico Mineiro" -> MG) are applied only when
        no explicit region was found on the name.
        """
        if not name:
            return "", ""
        text = name.strip()
        region = ""
        m = _PAREN_RE.search(text)
        if m:
            region = m.group(1).upper()
            text = text[: m.start()].strip()
        m = _SUFFIX_RE.search(text)
        if m and m.group(1).isupper():
            region = region or m.group(1).upper()
            text = text[: m.start()].strip()
        base = _NON_ALNUM_RE.sub("", strip_accents(text.lower()))
        base = BASE_FIXES.get(base, base)
        if not region and base in ALIASES:
            base, region = ALIASES[base]
        return base, region

    # --------------------------------------------------------------- observe
    def observe(self, name: str) -> str:
        """Record a team name occurrence and return its canonical key.

        Must be called for every team name before :meth:`canonical` can resolve
        stateless names via prominence.
        """
        base, region = self.parse(name or "")
        if not base:
            return ""
        if region:
            self.region_counts[base][region] += 1
        canonical_key = base + region.lower()
        self.display_names[canonical_key][name.strip()] += 1
        return canonical_key

    def finalize(self) -> None:
        """Lock in prominence tables so subsequent ``canonical`` calls resolve
        stateless names deterministically."""
        self._finalized = True

    # -------------------------------------------------------------- resolve
    def canonical(self, name: str) -> str:
        """Return the canonical key for ``name``.

        Stateless names resolve to the most common non-empty region observed
        for that base.  Unknown bases (e.g. foreign FIFA clubs not in the match
        data) are returned as ``base`` with no region.
        """
        base, region = self.parse(name or "")
        if not base:
            return ""
        if not region:
            regions = self.region_counts.get(base)
            if regions:
                region = regions.most_common(1)[0][0]
        return base + region.lower()

    def display(self, canonical_key: str) -> str:
        """Render a canonical key as a human-friendly display name."""
        if not canonical_key:
            return ""
        if canonical_key in DISPLAY_OVERRIDES:
            return DISPLAY_OVERRIDES[canonical_key]
        variants = self.display_names.get(canonical_key)
        if variants:
            # Most common raw variant; ties broken alphabetically for stability.
            return variants.most_common(1)[0][0]
        return canonical_key
