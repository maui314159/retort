"""Name and date normalization helpers for the Brazilian Soccer MCP server.

Context
-------
The six provided Kaggle CSV files use wildly different conventions for the
same real-world entities, and several conventions are *lossy*:

* Team names appear with a state suffix ("Palmeiras-SP"), without a suffix
  ("Palmeiras"), with full accented Portuguese spelling ("Grêmio", "São
  Paulo") and with ASCII-only spelling ("Gremio", "Sao Paulo").
* Crucially, the state suffix is sometimes the *only* disambiguator between
  two different clubs: "Atletico-MG" is Atlético Mineiro while
  "Atletico-PR" is Athletico Paranaense and "Atletico-GO" is Atlético
  Goianiense.  Naïvely stripping the suffix merges three distinct clubs into
  one.  The FIFA dataset even uses long forms ("Atletico Mineiro",
  "América FC (Minas Gerais)") that must collapse onto the same canonical
  club as the short "-MG" spelling.

To answer questions consistently we therefore maintain a **curated alias
dictionary** that maps every known spelling of a Série A club to a single
canonical display name.  Long forms, short forms, accented and ASCII
spellings and state-suffixed variants all resolve to one canonical name, and
the disambiguating state is preserved for the genuinely ambiguous bases
(Atlético/América/Bahia/Vitória/Sport/Ceará).  Names not in the curated
set (lower-division clubs in Série B/C) fall back to an accent-aware
best-spelling rule keyed on the de-accented, suffix-stripped surface form.

Dates are parsed into ``datetime.date`` objects regardless of the source
format (ISO, Brazilian DD/MM/YYYY, or ISO-with-time).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Regex matching a two-letter Brazilian state suffix at end of a team name,
# e.g. "Palmeiras-SP" or "América - MG" (with optional spaces around dash).
_STATE_SUFFIX = re.compile(r"\s*-\s*([A-Z]{2})\s*$")


def strip_state_suffix(name: str) -> str:
    """Remove a trailing ``-XX`` state abbreviation from a team name."""

    if not isinstance(name, str):
        return name
    return _STATE_SUFFIX.sub("", name).strip()


def extract_state(name: str) -> tuple[str, Optional[str]]:
    """Split a team name into ``(base, state)`` if a ``-XX`` suffix exists."""

    if not isinstance(name, str):
        return "", None
    m = _STATE_SUFFIX.search(name)
    if m:
        return _STATE_SUFFIX.sub("", name).strip(), m.group(1)
    return name.strip(), None


def deaccent(text: str) -> str:
    """Return ``text`` with accents/diacritics removed (NFKD decomposition)."""

    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _fold(text: str) -> str:
    """Lower-case, de-accent, collapse whitespace — the comparison base."""

    if text is None:
        return ""
    cleaned = deaccent(str(text)).lower()
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# Filler tokens that appear in long club names and should be ignored when
# matching, e.g. "Sport Club Corinthians Paulista" -> "corinthians".
_FILLERS = {
    "sport", "club", "clube", "de", "regatas", "esporte", "ec", "sc", "fc",
    "futebol", "associcao", "associacao", "sociedade", "esportiva",
    "centro", "sportivo", "da", "do", "fr", "rj", "mg", "pr", "go", "rs",
    "sp", "ba", "pe", "ce", "sc", "rn", "al", "mt", "df", "to",
}


def _strip_fillers(folded: str) -> str:
    """Remove filler words ("sport club", "ec", "fc", ...) from a folded name."""

    tokens = [t for t in folded.split() if t not in _FILLERS]
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Curated canonical team dictionary
# ---------------------------------------------------------------------------

# Canonical display name for every Série A club we expect to see.  These are
# the *stable* identifiers surfaced to the LLM.  Disambiguating state info is
# baked into the name where the base is ambiguous (Atlético, América, ...).
_CANONICAL_TEAMS = [
    "Atlético Mineiro", "Athletico Paranaense", "Atlético Goianiense",
    "América Mineiro", "América RN",
    "Flamengo", "Fluminense", "Vasco da Gama", "Botafogo",
    "Palmeiras", "Corinthians", "São Paulo", "Santos", "Ponte Preta",
    "Portuguesa", "Red Bull Bragantino", "Bragantino",
    "Grêmio", "Internacional",
    "Figueirense", "Avaí", "Chapecoense", "Joinville", "Criciúma",
    "Bahia", "Vitória",
    "Sport", "Náutico", "Santa Cruz",
    "Ceará", "Fortaleza",
    "Goiás", "CSA", "Cuiabá", "Paraná", "Cuiabá EC",
    "Cruzeiro", "Coritiba", "Juventude", "Brasiliense",
]

# Long-form spellings (already folded) mapped to a canonical name.  This is
# what lets "Atletico Mineiro", "America FC Minas Gerais" and "Atletico-MG"
# all collapse onto "Atlético Mineiro".
_LONG_FORMS: dict[str, str] = {
    "atletico mineiro": "Atlético Mineiro",
    "america fc minas gerais": "América Mineiro",
    "america mineiro": "América Mineiro",
    "america mg": "América Mineiro",
    "atletico paranaense": "Athletico Paranaense",
    "athletico paranaense": "Athletico Paranaense",
    "coritiba paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense",
    "atletico goias": "Atlético Goianiense",
    "america fc natal": "América RN",
    "america rn": "América RN",
    "sport club do recife": "Sport",
    "sport recife": "Sport",
    "sport club corinthians paulista": "Corinthians",
    "sociedade esportiva palmeiras": "Palmeiras",
    "clube de regatas do flamengo": "Flamengo",
    "sao paulo fc": "São Paulo",
    "santos fc": "Santos",
    "associacao chapecoense de futebol": "Chapecoense",
    "associacao atletica ponte preta": "Ponte Preta",
    "clube nautico capibaribe": "Náutico",
    "nautico capibaribe": "Náutico",
    "santa cruz fc": "Santa Cruz",
    "ceara sporting club": "Ceará",
    "ceara sc": "Ceará",
    "fortaleza fc": "Fortaleza",
    "fortaleza ec": "Fortaleza",
    "ec bahia": "Bahia",
    "esporte clube bahia": "Bahia",
    "ec vitoria": "Vitória",
    "esporte clube vitoria": "Vitória",
    "botafogo fr": "Botafogo",
    "botafogo rj": "Botafogo",
    "vasco da gama": "Vasco da Gama",
    "vasco da gama rj": "Vasco da Gama",
    "gremio rs": "Grêmio",
    "internacional rs": "Internacional",
    "sc internacional": "Internacional",
    "red bull bragantino": "Red Bull Bragantino",
    "rb bragantino": "Red Bull Bragantino",
    "bragantino": "Bragantino",
    "ec juventude": "Juventude",
    "juventude rs": "Juventude",
    "goias ec": "Goiás",
    "goias go": "Goiás",
    "cuiaba ec": "Cuiabá",
    "cuiaba mt": "Cuiabá",
    "parana clube": "Paraná",
    "parana pr": "Paraná",
    "csa": "CSA",
    "centro sportivo alagoano": "CSA",
    "figueirense sc": "Figueirense",
    "avai sc": "Avaí",
    "avai fc": "Avaí",
    "joinville sc": "Joinville",
    "criciuma sc": "Criciúma",
    "coritiba pr": "Coritiba",
    "cruzeiro mg": "Cruzeiro",
    "cruzeiro ec": "Cruzeiro",
    "ponte preta sp": "Ponte Preta",
    "portuguesa sp": "Portuguesa",
    "brasiliense": "Brasiliense",
    "brasilia fc": "Brasiliense",
    "palmeiras sp": "Palmeiras",
    "corinthians sp": "Corinthians",
    "santos sp": "Santos",
    "sao paulo sp": "São Paulo",
    "flamengo rj": "Flamengo",
    "fluminense rj": "Fluminense",
    "bahia ba": "Bahia",
    "vitoria ba": "Vitória",
    "ceara ce": "Ceará",
    "fortaleza ce": "Fortaleza",
    "sport pe": "Sport",
    "nautico pe": "Náutico",
    "santa cruz pe": "Santa Cruz",
    "goias go": "Goiás",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "cuiaba": "Cuiabá",
    "parana": "Paraná",
    "csa": "CSA",
    "avai": "Avaí",
    "ceara": "Ceará",
    "vitoria": "Vitória",
    "bahia": "Bahia",
    "sao paulo": "São Paulo",
    "criciuma": "Criciúma",
    "figueirense": "Figueirense",
    "joinville": "Joinville",
    "chapecoense": "Chapecoense",
    "coritiba": "Coritiba",
    "cruzeiro": "Cruzeiro",
    "palmeiras": "Palmeiras",
    "corinthians": "Corinthians",
    "santos": "Santos",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "botafogo": "Botafogo",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "ponte preta": "Ponte Preta",
    "portuguesa": "Portuguesa",
    "juventude": "Juventude",
    "america": "América Mineiro",  # default América -> Mineiro (most common)
    "atletico": "Atlético Mineiro",  # default Atlético -> Mineiro (most common)
    "athletico": "Athletico Paranaense",
}

# Bases that are ambiguous and *must* carry their state to disambiguate.
# Maps (folded_base, state) -> canonical name.  When a name with one of these
# bases arrives without a state, the bare-base entry in _LONG_FORMS provides
# the default (the most prominent club for that base).  When it arrives with
# a state that is NOT in this map (e.g. a tiny Série-C "Atlético-ES"), we
# deliberately do NOT fall back to the prominent-club default — the fallback
# keeps the state so the small club stays distinct (see AMBIGUOUS_BASES).
_AMBIGUOUS_BY_STATE: dict[tuple[str, str], str] = {
    ("atletico", "mg"): "Atlético Mineiro",
    ("atletico", "pr"): "Athletico Paranaense",
    ("atletico", "go"): "Atlético Goianiense",
    ("athletico", "pr"): "Athletico Paranaense",
    ("america", "mg"): "América Mineiro",
    ("america", "rn"): "América RN",
    ("bahia", "ba"): "Bahia",
    ("vitoria", "ba"): "Vitória",
    ("sport", "pe"): "Sport",
    ("ceara", "ce"): "Ceará",
    ("santa cruz", "pe"): "Santa Cruz",
    ("nautico", "pe"): "Náutico",
    ("juventude", "rs"): "Juventude",
}

# Bases shared by multiple distinct clubs.  When such a base arrives with a
# state we don't recognise, we must NOT collapse it onto the prominent
# default — instead the fallback (register) keeps the state suffix so the
# unknown club remains its own node.
_AMBIGUOUS_BASES = {
    "atletico", "athletico", "america", "bahia", "vitoria", "sport",
    "ceara", "santa cruz", "nautico", "juventude",
}


class TeamNameNormalizer:
    """Collapses many spellings of a team into one canonical display name.

    Resolution order for a raw spelling ``r``:

    1. Fold (de-accent + lower + drop punctuation) then look up the
       filler-stripped long form in :data:`_LONG_FORMS`.
    2. If a state suffix is present and ``(base, state)`` is in
       :data:`_AMBIGUOUS_BY_STATE`, use that.
    3. Otherwise look up the bare folded base in :data:`_LONG_FORMS`
       (covers "Gremio" -> "Grêmio", "Sao Paulo" -> "São Paulo").
    4. Fall back to the registered best-spelling for uncurated (mostly
       lower-division) clubs, keyed on the folded suffix-stripped name.
    """

    def __init__(self) -> None:
        # canonical name -> set of raw spellings seen (for introspection)
        self._raw_by_canon: dict[str, set[str]] = {}
        # Fallback store for uncurated clubs: folded_key -> best display
        self._fallback_display: dict[str, str] = {}

    # -- public API ------------------------------------------------------

    def canonical(self, name: str) -> Optional[str]:
        """Return the canonical display name for any spelling, or None."""

        if name is None:
            return None
        raw = str(name).strip()
        if not raw:
            return None
        curated = self._curated(raw)
        if curated is not None:
            return curated
        # Fallback path for uncurated clubs — use the same state-aware key
        # that ``register`` uses so a query spelling resolves correctly.
        base, state = extract_state(raw)
        key = _fold(base) + (f"-{state.lower()}" if state else "")
        return self._fallback_display.get(key)

    def register(self, name: str) -> str:
        """Register a raw team name and return its canonical display form."""

        if name is None:
            return ""
        raw = str(name).strip()
        if not raw:
            return ""
        curated = self._curated(raw)
        if curated is not None:
            self._raw_by_canon.setdefault(curated, set()).add(raw)
            return curated
        # Uncurated club (mostly lower-division).  Keep the state suffix in
        # BOTH the comparison key and the display name so that clubs sharing
        # a base but in different states (e.g. a Série-C "Atlético-ES" vs
        # "Atlético-AC") stay distinct instead of collapsing together.
        base, state = extract_state(raw)
        base_display = base
        key = _fold(base) + (f"-{state.lower()}" if state else "")
        if not _fold(base):
            return raw
        display = base_display + (f"-{state}" if state else "")
        current = self._fallback_display.get(key)
        if current is None or _accent_count(base_display) > _accent_count(current.split("-")[0] if "-" in current else current):
            self._fallback_display[key] = display
        else:
            display = current
        self._raw_by_canon.setdefault(display, set()).add(raw)
        return display

    def known(self) -> list[str]:
        """All canonical display names known to the normalizer."""

        return sorted(
            set(self._raw_by_canon.keys()) | set(self._fallback_display.values())
            | set(_CANONICAL_TEAMS)
        )

    def raw_spellings(self, name: str) -> list[str]:
        """Return the raw spellings seen for the team matching *name*."""

        canon = self.canonical(name)
        if canon is None:
            return []
        return sorted(self._raw_by_canon.get(canon, set()))

    # -- internal --------------------------------------------------------

    def _curated(self, raw: str) -> Optional[str]:
        folded_full = _fold(raw)
        # Exact long-form match first (handles "Atletico Mineiro", "Sport
        # Club do Recife", "América FC (Minas Gerais)" -> one folded form).
        if folded_full in _LONG_FORMS:
            return _LONG_FORMS[folded_full]
        # State-aware ambiguous lookup.  MUST run before filler-stripping,
        # because _strip_fillers drops state tokens ("pr", "go", ...) and
        # would otherwise collapse "Atletico-PR" onto the bare base
        # "atletico" -> "Atlético Mineiro" (wrong club).
        base, state = extract_state(raw)
        if state is not None:
            base_folded = _fold(base)
            key = (base_folded, state.lower())
            if key in _AMBIGUOUS_BY_STATE:
                return _AMBIGUOUS_BY_STATE[key]
            # An ambiguous base with an UNRECOGNISED state is a different,
            # lower-division club (e.g. "Atlético-ES").  Do NOT collapse it
            # onto the prominent default — defer to the fallback, which
            # preserves the state so the club stays distinct.
            if base_folded in _AMBIGUOUS_BASES:
                return None
        # Filler-stripped long form (drops "ec", "fc", "sc", state tokens).
        stripped_fillers = _strip_fillers(folded_full)
        if stripped_fillers and stripped_fillers in _LONG_FORMS:
            return _LONG_FORMS[stripped_fillers]
        if state is not None:
            base_no_fillers = _strip_fillers(_fold(base))
            # Same guard: don't let an ambiguous bare base pull an unknown
            # state onto the prominent club.
            if base_no_fillers in _LONG_FORMS and base_no_fillers not in _AMBIGUOUS_BASES:
                return _LONG_FORMS[base_no_fillers]
        # Bare base lookup (covers "Gremio", "Sao Paulo", "Atletico").
        bare = _strip_fillers(folded_full)
        if bare in _LONG_FORMS:
            return _LONG_FORMS[bare]
        return None

    # Backwards-compatible alias.
    def resolve(self, name: str) -> Optional[str]:
        return self.canonical(name)

    def key(self, name: str) -> str:
        """A stable comparison key derived from the canonical name."""

        canon = self.canonical(name) or name
        return _fold(canon)


def _accent_count(text: str) -> int:
    nfkd = unicodedata.normalize("NFKD", text)
    return sum(1 for ch in nfkd if unicodedata.combining(ch))


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------


def parse_date(value) -> Optional[date]:
    """Parse a date from ISO, Brazilian, or ISO-with-time strings.

    Accepts:
        "2023-09-24"
        "2012-05-19 18:30:00"
        "29/03/2003"
        a ``datetime``/``date`` object
        ``None``/``NaN`` -> ``None``
    """

    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def to_int(value) -> Optional[int]:
    """Best-effort conversion of a goal/score column to ``int``."""

    if value is None:
        return None
    try:
        if isinstance(value, str):
            if not value.strip() or value.strip().lower() == "nan":
                return None
            return int(float(value))
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Module-level convenience kept for backwards compatibility with code that
# pre-dates the curated dictionary.  Prefer ``TeamNameNormalizer.canonical``.
# ---------------------------------------------------------------------------


def team_match_key(name: str) -> str:
    """Legacy suffix-stripped, de-accented, lower-cased key (fallback only).

    New code should use :meth:`TeamNameNormalizer.key` which respects the
    curated alias dictionary.  This helper is kept so that older call sites
    (and the dataclass ``MatchRecord.result_for``) keep working for the
    uncurated, unambiguous case.
    """

    if name is None:
        return ""
    cleaned = strip_state_suffix(str(name))
    return _fold(cleaned)
