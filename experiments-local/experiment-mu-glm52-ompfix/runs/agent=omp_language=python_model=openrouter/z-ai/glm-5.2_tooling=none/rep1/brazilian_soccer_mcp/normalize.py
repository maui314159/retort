"""
brazilian_soccer_mcp.normalize
==============================

Team-name normalisation for the Brazilian Soccer MCP server.

Context / problem
-----------------
The bundled datasets spell the *same* club in many incompatible ways:

* with a state suffix      -> "Palmeiras-SP", "América - MG", "Athletico-PR"
* without a suffix         -> "Palmeiras", "Flamengo"
* full official name       -> "Atlético Mineiro", "Athletico Paranaense"
* with / without accents    -> "São Paulo" vs "Sao Paulo", "Grêmio" vs "Gremio"
* with / without the "h"    -> "Athletico-PR" (novo) vs "Atletico-PR" (Brasileirão)
  (these are the SAME club: Athletico Paranaense)

Worse, *different* clubs share the same base name and are disambiguated ONLY by
their state suffix, e.g. "Atlético-MG", "Athletico-PR", "Atlético-GO",
"Atlético-ES". A naive "strip the suffix" strategy merges four distinct clubs
into one and corrupts standings.

Strategy
--------
``TeamNormalizer`` resolves every raw spelling to one canonical display name
using two layers:

1. **Manual alias table** (``MANUAL_CLUBS``). Covers the handful of major
   Brazilian clubs whose full FIFA names ("Atlético Mineiro",
   "América FC (Minas Gerais)", ...) or whose 'h'/accent inconsistency
   ("Atletico-PR" vs "Athletico-PR") cannot be merged algorithmically without
   falsely collapsing distinct clubs. Aliases are matched on an accent- and
   case-insensitive *full key* (base key + state) computed by the same
   ``parse``/``key`` logic used everywhere else, so manual and automatic paths
   can never disagree on keying.

2. **Automatic collision resolution**. For every base key we collect the set of
   state suffixes observed across all datasets. If a base key maps to more than
   one state, the suffix is *kept* as a disambiguator
   (e.g. "Atlético-MG" stays "Atlético-MG"); otherwise the suffix is dropped
   (e.g. "Palmeiras-SP" -> "Palmeiras"). The displayed base form prefers the
   most richly-accented variant seen (so "São Paulo" wins over "Sao Paulo").

The normaliser is built once from the full universe of raw team strings, then
reused for every lookup (matches *and* FIFA clubs).
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Optional

# ---------------------------------------------------------------------------
# Brazilian state codes (UFs)
# ---------------------------------------------------------------------------

STATES: frozenset[str] = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)


def _strip_accents(value: str) -> str:
    """Return the ASCII-folded form of ``value`` (accents removed)."""
    nfkd = unicodedata.normalize("NFKD", value)
    return nfkd.encode("ascii", "ignore").decode("ascii")


def make_key(value: str) -> str:
    """Normalise a string to a stable comparison key.

    Accent-folded, lower-cased, non-alphanumeric characters removed.
    "São Paulo", "Sao Paulo" and "SAO PAULO" all -> "saopaulo".
    """
    return re.sub(r"[^a-z0-9]", "", _strip_accents(str(value)).lower())


# ---------------------------------------------------------------------------
# Manual alias table for tricky / collision-prone major clubs.
# Each canonical name lists every spelling variant we have observed (or expect)
# across the datasets. The normaliser keys every alias with ``make_key`` of its
# parsed (base + state) form, so this table also handles FIFA full names such
# as "Atlético Mineiro" -> canonical "Atlético-MG".
# ---------------------------------------------------------------------------

MANUAL_CLUBS: dict[str, list[str]] = {
    # --- Clubs whose base name collides across states (must keep suffix) ---
    # Atlético Mineiro (MG) — FIFA spells it "Atlético Mineiro"
    "Atlético-MG": [
        "Atlético-MG", "Atletico-MG", "Atlético - MG", "Atletico - MG",
        "Atlético Mineiro", "Atletico Mineiro", "Atlético Mineiro - MG",
        "Atletico Mineiro - MG",
    ],
    # Athletico Paranaense (PR) — Brasileirão spells it "Atletico-PR" (no 'h'),
    # novo spells it "Athletico-PR", BR-Football uses the full name.
    "Athletico-PR": [
        "Athletico-PR", "Atletico-PR", "Athletico - PR", "Atletico - PR",
        "Atlético - PR",
        "Athletico Paranaense", "Atletico Paranaense",
        "Athletico Paranaense - PR", "Atletico Paranaense - PR",
        "Atlético Paranaense", "Atlético Paranaense - PR",
    ],
    # Atlético Goianiense (GO)
    "Atlético-GO": [
        "Atlético-GO", "Atletico-GO", "Atlético - GO", "Atletico - GO",
        "Atletico Goianiense", "Atlético Goianiense",
        "Atletico Goianiense - GO", "Atlético Goianiense - GO",
    ],
    # América Mineiro (MG) — FIFA spells it "América FC (Minas Gerais)"
    "América-MG": [
        "América-MG", "America-MG", "América - MG", "America - MG",
        "América Mineiro", "America Mineiro",
        "América FC (Minas Gerais)", "America FC (Minas Gerais)",
        "América Fc (Minas Gerais)",
    ],
    # América de Natal (RN)
    "América-RN": [
        "América-RN", "America-RN", "América - RN", "America - RN",
        "América de Natal", "America de Natal",
        "América de Natal - RN", "America de Natal - RN",
    ],
    # Botafogo (RJ) — disambiguate from Botafogo-PB; bare "Botafogo" (FIFA) is RJ
    "Botafogo-RJ": [
        "Botafogo-RJ", "Botafogo - RJ", "Botafogo",
    ],
    "Botafogo-PB": [
        "Botafogo-PB", "Botafogo - PB",
    ],
    # --- Major clubs with unique base names — canonical form is bare (no suffix) ---
    # These override the automatic collision logic so "Flamengo-RJ" displays as
    # "Flamengo" while the minor "Flamengo-PI" still keeps its suffix.
    "Flamengo": [
        "Flamengo-RJ", "Flamengo - RJ", "Flamengo",
    ],
    "Fluminense": [
        "Fluminense-RJ", "Fluminense - RJ", "Fluminense",
    ],
    "Vasco da Gama": [
        "Vasco-RJ", "Vasco - RJ", "Vasco", "Vasco da Gama-RJ", "Vasco da Gama - RJ",
        "Vasco da Gama",
    ],
    "Santos": [
        "Santos-SP", "Santos - SP", "Santos",
    ],
    "Corinthians": [
        "Corinthians-SP", "Corinthians - SP", "Corinthians",
        "Sport Club Corinthians Paulista",
    ],
    "Palmeiras": [
        "Palmeiras-SP", "Palmeiras - SP", "Palmeiras",
        "Sociedade Esportiva Palmeiras",
    ],
    "São Paulo": [
        "São Paulo-SP", "São Paulo - SP", "Sao Paulo-SP", "Sao Paulo - SP",
        "São Paulo", "Sao Paulo",
    ],
    "Grêmio": [
        "Grêmio-RS", "Grêmio - RS", "Gremio-RS", "Gremio - RS",
        "Grêmio", "Gremio",
    ],
    "Internacional": [
        "Internacional-RS", "Internacional - RS", "Internacional",
        "Internacional Sm",
    ],
    "Cruzeiro": [
        "Cruzeiro-MG", "Cruzeiro - MG", "Cruzeiro",
    ],
    "Bahia": [
        "Bahia-BA", "Bahia - BA", "Bahia",
        "Esporte Clube Bahia",
    ],
    "Fortaleza": [
        "Fortaleza-CE", "Fortaleza - CE", "Fortaleza",
    ],
    "Ceará": [
        "Ceará-CE", "Ceará - CE", "Ceara-CE", "Ceara - CE",
        "Ceará", "Ceara",
    ],
    "Sport": [
        "Sport-PE", "Sport - PE", "Sport Recife", "Sport",
    ],
    "Vitória": [
        "Vitória-ES", "Vitória - ES", "Vitoria-ES", "Vitoria - ES",
        "Vitória", "Vitoria",
        "Vitória-BA", "Vitória - BA", "Vitoria-BA", "Vitoria - BA",
    ],
    "Coritiba": [
        "Coritiba-PR", "Coritiba - PR", "Coritiba",
    ],
    "Goiás": [
        "Goiás-GO", "Goiás - GO", "Goias-GO", "Goias - GO",
        "Goiás", "Goias",
    ],
    "Avaí": [
        "Avaí-SC", "Avaí - SC", "Avai-SC", "Avai - SC",
        "Avaí", "Avai",
    ],
    "Criciúma": [
        "Criciúma-SC", "Criciúma - SC", "Criciuma-SC", "Criciuma - SC",
        "Criciúma", "Criciuma",
    ],
    "Chapecoense": [
        "Chapecoense-SC", "Chapecoense - SC", "Chapecoense",
    ],
    "Ponte Preta": [
        "Ponte Preta-SP", "Ponte Preta - SP", "Ponte Preta",
    ],
    "Figueirense": [
        "Figueirense-SC", "Figueirense - SC", "Figueirense",
    ],
    "Juventude": [
        "Juventude-RS", "Juventude - RS", "Juventude",
    ],
    "CSA": [
        "CSA-AL", "CSA - AL", "CSA",
    ],
    "Brasiliense": [
        "Brasiliense-DF", "Brasiliense - DF", "Brasiliense",
    ],
}

# Bare (no-suffix) base keys that are ambiguous and must default to a specific
# club. Applied only when the raw name carries no state suffix.
BARE_DEFAULTS: dict[str, str] = {
    "atletico": "Atlético-MG",     # bare "Atlético" -> the biggest Atlético
    "america": "América-MG",       # bare "América"  -> the biggest América
    "athletico": "Athletico-PR",   # bare "Athletico" (Libertadores) -> PR club
    "botafogo": "Botafogo-RJ",
}


# ---------------------------------------------------------------------------
# Parsing a raw team string into (base, state)
# ---------------------------------------------------------------------------


def _parse(raw: str) -> tuple[str, Optional[str]]:
    """Split a raw team string into ``(base, state)``.

    * Strips parentheticals such as "(URU)", "(Minas Gerais)".
    * Strips a trailing 2-letter Brazilian state suffix ("Palmeiras-SP",
      "América - MG") and records it as ``state``.
    * Strips a trailing 3-letter country code ("Barcelona-EQU") as ``state``.
    """
    s = str(raw).strip()
    # remove all parenthetical groups
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()
    state: Optional[str] = None

    # trailing 2-letter state suffix, with optional spaces around the dash
    m = re.search(r"\s*-\s*([A-Z]{2})\s*$", s)
    if m and m.group(1) in STATES:
        state = m.group(1)
        s = (s[: m.start()] + s[m.end():]).strip()
    else:
        # trailing 3-letter country code (Libertadores foreign teams)
        m2 = re.search(r"\s*-\s*([A-Z]{3})\s*$", s)
        if m2:
            state = m2.group(1)
            s = (s[: m2.start()] + s[m2.end():]).strip()

    # collapse internal whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s, state


def _full_key(base: str, state: Optional[str]) -> str:
    return make_key(base) + (state.lower() if state else "")


# ---------------------------------------------------------------------------
# Normaliser
# ---------------------------------------------------------------------------


class TeamNormalizer:
    """Resolves raw team-name spellings to canonical display names.

    Build once with the universe of raw names, then call :meth:`canonical`
    for every lookup. Two-layer resolution: manual alias table first, then
    automatic collision resolution on the (base key -> states) index.
    """

    def __init__(self, raw_names: list[str]) -> None:
        # base_key -> set of states seen (None included for bare names)
        self._states_by_base: dict[str, set[Optional[str]]] = defaultdict(set)
        # base_key -> preferred (most-accented, then shortest) display base
        self._display_base: dict[str, str] = {}
        # manual lookup tables keyed by full key and by bare base key
        self._manual_full: dict[str, str] = {}
        self._manual_bare: dict[str, str] = {}

        self._build_manual_index()
        self._build_auto_index(raw_names)

    # -- building ----------------------------------------------------------

    def _build_manual_index(self) -> None:
        for canonical, aliases in MANUAL_CLUBS.items():
            for alias in aliases:
                base, state = _parse(alias)
                self._manual_full[_full_key(base, state)] = canonical
                if state is None:
                    # bare alias also registered under its base key
                    self._manual_bare.setdefault(make_key(base), canonical)
        # explicit bare-name defaults for ambiguous clubs (e.g. bare "Athletico"
        # in the Libertadores file -> Athletico-PR). These win over the
        # automatic collision resolution only when no state suffix is present.
        for base_key, canonical in BARE_DEFAULTS.items():
            self._manual_bare.setdefault(base_key, canonical)

    def _build_auto_index(self, raw_names: list[str]) -> None:
        for raw in raw_names:
            base, state = _parse(raw)
            bk = make_key(base)
            if not bk:
                continue
            self._states_by_base[bk].add(state)
            self._maybe_promote_display(bk, base)

    def _maybe_promote_display(self, base_key: str, candidate: str) -> None:
        """Keep the richest-accented, then shortest, base form for display."""
        current = self._display_base.get(base_key)
        if current is None:
            self._display_base[base_key] = candidate
            return

        def accent_count(s: str) -> int:
            return sum(1 for ch in s if unicodedata.category(ch).startswith("M"))

        ca, pa = accent_count(candidate), accent_count(current)
        if ca > pa or (ca == pa and len(candidate) < len(current)):
            self._display_base[base_key] = candidate

    # -- querying ----------------------------------------------------------

    def canonical(self, raw: str) -> str:
        """Return the canonical display name for a raw team string."""
        base, state = _parse(raw)
        if not base:
            return str(raw).strip()

        fk = _full_key(base, state)
        bk = make_key(base)

        # 1) manual override on the full (base+state) key
        if fk in self._manual_full:
            return self._manual_full[fk]

        # 2) manual override on the bare base key, only when no state present
        if state is None and bk in self._manual_bare:
            return self._manual_bare[bk]

        # 3) automatic collision resolution
        states = self._states_by_base.get(bk, set())
        display = self._display_base.get(bk, base)
        if len({s for s in states if s is not None}) > 1 and state is not None:
            return f"{display}-{state}"
        return display

    # -- introspection (used by tests / graph building) --------------------

    def is_ambiguous_base(self, base_key: str) -> bool:
        states = self._states_by_base.get(base_key, set())
        return len({s for s in states if s is not None}) > 1
