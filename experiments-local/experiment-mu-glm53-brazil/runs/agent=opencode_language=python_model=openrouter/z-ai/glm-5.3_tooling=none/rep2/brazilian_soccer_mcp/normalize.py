"""Team-name canonicalization and date/value parsing utilities.

The source datasets name the same club in many different ways
("Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista",
"Atletico Mineiro", "Athletico" ...).  This module normalizes every team
mention to a stable canonical key so that matches, players and queries can
be joined across files.

The registry is built in two phases:

1. ``observe()`` is called once per team mention in every match file and
   records the parsed (bare-name, state, country) state and the raw display
   variant.
2. ``finalize()`` assigns canonical keys:

   - a bare name used by exactly one state keeps the bare name as key
     (e.g. ``palmeiras``);
   - a bare name shared by several states is split into ``<name>-<uf>``
     keys (e.g. ``atletico-mg``, ``atletico-go``, ``atletico-pr``);
   - mentions without a state are merged into the most frequently seen
     state variant (so the bare "Flamengo" of the Copa do Brasil file joins
     "Flamengo-RJ" of the Brasileirão file);
   - foreign clubs carrying a country code (e.g. "Nacional-URU") keep it
     as part of their key.

Queries are resolved through :meth:`TeamRegistry.resolve`, which applies the
same parsing, a curated alias table, and a token-subset fallback that maps
long official names ("Sport Club Corinthians Paulista") onto the registered
short names.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

BRAZILIAN_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

COUNTRY_CODES = {
    "ARG", "BOL", "CHI", "COL", "EQU", "GUA", "JPN", "MEX", "PAR", "PER",
    "URU", "VEN",
}

STATE_NAMES = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM",
    "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
    "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
    "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
    "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE",
    "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR",
    "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO",
}

NOISE_TOKENS = {
    "aa", "ac", "ad", "ae", "ca", "ce", "clube", "club", "cs", "ec",
    "esporte", "fc", "ge", "sc",
}

ALIASES = {
    "america mineiro": "america-mg",
    "atletico goianiense": "atletico-go",
    "atletico mineiro": "atletico-mg",
    "atletico paranaense": "atletico-pr",
    "athletico": "atletico-pr",
    "athletico-pr": "atletico-pr",
    "athletico paranaense": "atletico-pr",
    "bragantino-sp": "red bull bragantino",
    "ceara sporting": "ceara",
    "cs alagoano": "csa",
    "libertad": "libertad-par",
    "ponte pretta": "ponte preta",
    "sport club do recife": "sport",
    "sport do recife": "sport",
    "sport recife": "sport",
    "vasco": "vasco da gama",
}

_INVALID_VALUES = {"", "-", "--", "na", "n/a", "none", "null", "?"}


def strip_accents(value: str) -> str:
    """Return *value* with accented characters folded to their ASCII form."""
    decomposed = unicodedata.normalize("NFKD", value)
    return decomposed.encode("ascii", "ignore").decode("ascii")


def base_norm(value: str) -> str:
    """Lowercase, drop accents and non-alphanumerics from *value*."""
    text = strip_accents(value).lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


@dataclass(frozen=True)
class ParsedName:
    """Result of parsing a raw team mention."""

    bare: str
    uf: str | None = None
    country: str | None = None


def parse_team_name(name: str, uf_hint: str | None = None) -> ParsedName:
    """Parse a raw team mention into bare name, state and country code."""
    raw = base_norm(name)
    if not raw:
        return ParsedName(bare="")
    tokens = raw.split()

    country = None
    if len(tokens) > 1 and tokens[-1].upper() in COUNTRY_CODES:
        country = tokens[-1].upper()
        tokens = tokens[:-1]

    uf = uf_hint.upper() if uf_hint else None
    if len(tokens) > 1 and tokens[-1].upper() in BRAZILIAN_UFS:
        uf = tokens[-1].upper()
        tokens = tokens[:-1]

    for part in re.findall(r"\(([^)]*)\)", name):
        key = base_norm(part).upper()
        if key in COUNTRY_CODES and country is None:
            country = key
        elif base_norm(part) in STATE_NAMES and uf is None:
            uf = STATE_NAMES[base_norm(part)]

    bare_tokens = [t for t in tokens if t not in NOISE_TOKENS]
    if not bare_tokens:
        bare_tokens = tokens
    return ParsedName(bare=" ".join(bare_tokens), uf=uf, country=country)


@dataclass
class TeamResolution:
    """Outcome of resolving a user-supplied team name."""

    key: str | None = None
    display: str | None = None
    matched_by: str = "not_found"
    alternatives: list[dict] = field(default_factory=list)
    suggestions: list[dict] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.key is not None


State = tuple[str, str | None, str | None]


class TeamRegistry:
    """Registry mapping every observed team mention to a canonical key."""

    def __init__(self) -> None:
        self._state_counts: dict[State, int] = {}
        self._state_displays: dict[State, dict[str, int]] = {}
        self._key_of_state: dict[State, str] = {}
        self._displays: dict[str, str] = {}
        self._key_counts: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Phase 1: observation
    # ------------------------------------------------------------------
    def observe(self, display: str, uf_hint: str | None = None) -> None:
        """Record one team mention."""
        parsed = parse_team_name(display, uf_hint)
        if not parsed.bare:
            return
        state = (parsed.bare, parsed.uf, parsed.country)
        self._state_counts[state] = self._state_counts.get(state, 0) + 1
        variants = self._state_displays.setdefault(state, {})
        cleaned = re.sub(r"\s+", " ", display).strip()
        variants[cleaned] = variants.get(cleaned, 0) + 1

    # ------------------------------------------------------------------
    # Phase 2: finalize
    # ------------------------------------------------------------------
    def finalize(self) -> None:
        """Assign canonical keys and pick display names."""
        bare_states: dict[str, list[State]] = {}
        for state in self._state_counts:
            bare_states.setdefault(state[0], []).append(state)

        for bare, states in bare_states.items():
            domestic_ufs = {
                state[1] for state in states
                if state[2] is None and state[1] is not None
            }
            for state in states:
                name, uf, country = state
                alias_key = self._alias_for_state(name, uf)
                if alias_key is not None:
                    self._key_of_state[state] = alias_key
                elif country is not None:
                    self._key_of_state[state] = f"{name}-{country.lower()}"
                elif len(domestic_ufs) <= 1:
                    self._key_of_state[state] = name
                elif uf is not None:
                    self._key_of_state[state] = f"{name}-{uf.lower()}"
                else:
                    counts = {
                        candidate: self._state_counts.get((bare, candidate, None), 0)
                        for candidate in domestic_ufs
                    }
                    major = max(counts, key=lambda uf: (counts[uf], uf))
                    self._key_of_state[state] = f"{name}-{major.lower()}"

        key_counts: dict[str, int] = {}
        key_displays: dict[str, dict[str, int]] = {}
        for state, count in self._state_counts.items():
            key = self._key_of_state[state]
            key_counts[key] = key_counts.get(key, 0) + count
            merged = key_displays.setdefault(key, {})
            for display, display_count in self._state_displays[state].items():
                merged[display] = merged.get(display, 0) + display_count

        for key in set(ALIASES.values()):
            key_counts.setdefault(key, 0)

        self._key_counts = {k: v for k, v in key_counts.items() if v > 0}
        self._displays = {
            key: self._pick_display(displays)
            for key, displays in key_displays.items()
        }
        for key in self._key_counts:
            self._displays.setdefault(key, key)

    def _pick_display(self, displays: dict[str, int]) -> str:
        def score(name: str) -> tuple[int, int, int]:
            count = displays[name]
            simple = int("-" not in name and "(" not in name)
            return (simple, count, -len(name))

        return max(displays, key=score)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def canonical(self, display: str, uf_hint: str | None = None) -> str:
        """Return the canonical key for a team mention."""
        parsed = parse_team_name(display, uf_hint)
        if not parsed.bare:
            return ""
        for alias_key in self._alias_candidates(parsed):
            if alias_key in ALIASES:
                return ALIASES[alias_key]
        state = (parsed.bare, parsed.uf, parsed.country)
        return self._key_of_state.get(state, self._fallback_key(parsed))

    def _alias_candidates(self, parsed: ParsedName) -> list[str]:
        candidates = []
        if parsed.uf:
            candidates.append(f"{parsed.bare}-{parsed.uf.lower()}")
        candidates.append(parsed.bare)
        return candidates

    @staticmethod
    def _alias_for_state(bare: str, uf: str | None) -> str | None:
        candidates = []
        if uf:
            candidates.append(f"{bare}-{uf.lower()}")
        candidates.append(bare)
        for candidate in candidates:
            if candidate in ALIASES:
                return ALIASES[candidate]
        return None

    def _fallback_key(self, parsed: ParsedName) -> str:
        if parsed.country:
            return f"{parsed.bare}-{parsed.country.lower()}"
        if parsed.uf:
            return f"{parsed.bare}-{parsed.uf.lower()}"
        return parsed.bare

    def display(self, key: str) -> str:
        """Return the best display name for a canonical key."""
        return self._displays.get(key, key)

    def keys(self) -> list[str]:
        return sorted(self._key_counts)

    def match_count(self, key: str) -> int:
        return self._key_counts.get(key, 0)

    def all_teams(self) -> list[dict]:
        return [
            {"key": key, "display": self.display(key), "matches": self._key_counts[key]}
            for key in self.keys()
        ]

    def is_known(self, key: str) -> bool:
        return key in self._key_counts

    def _candidates_for_bare(self, bare: str) -> list[str]:
        candidates = {
            key for (name, _uf, country), key in self._key_of_state.items()
            if name == bare and country is None
        }
        if not candidates:
            candidates = {
                key for key in self._key_counts
                if key == bare or key.startswith(bare + "-")
            }
        return sorted(
            candidates,
            key=lambda key: (self._key_counts.get(key, 0), key),
            reverse=True,
        )

    def resolve(self, query: str) -> TeamResolution:
        """Resolve a user-supplied team name to a canonical team."""
        if not query or not query.strip():
            return TeamResolution()
        parsed = parse_team_name(query)
        if not parsed.bare:
            return TeamResolution()

        for alias_key in self._alias_candidates(parsed):
            if alias_key in ALIASES and self.is_known(ALIASES[alias_key]):
                key = ALIASES[alias_key]
                return TeamResolution(
                    key=key, display=self.display(key), matched_by="alias"
                )

        if parsed.country:
            key = f"{parsed.bare}-{parsed.country.lower()}"
            if self.is_known(key):
                return TeamResolution(key=key, display=self.display(key),
                                      matched_by="country")
            return TeamResolution(
                suggestions=self._team_refs(self._candidates_for_bare(parsed.bare)[:5])
            )

        if parsed.uf:
            key = f"{parsed.bare}-{parsed.uf.lower()}"
            if self.is_known(key):
                return TeamResolution(key=key, display=self.display(key),
                                      matched_by="state")

        if self.is_known(parsed.bare):
            return TeamResolution(
                key=parsed.bare, display=self.display(parsed.bare),
                matched_by="exact",
            )

        candidates = self._candidates_for_bare(parsed.bare)
        if len(candidates) == 1:
            return TeamResolution(key=candidates[0],
                                  display=self.display(candidates[0]),
                                  matched_by="prefix")
        if len(candidates) > 1:
            return TeamResolution(
                key=candidates[0],
                display=self.display(candidates[0]),
                matched_by="frequency",
                alternatives=self._team_refs(candidates[1:5]),
            )

        query_tokens = set(parsed.bare.split())
        subset_matches = []
        for key in self._key_counts:
            key_bare = key.rsplit("-", 1)[0] if "-" in key else key
            key_tokens = set(key_bare.split())
            if key_tokens and key_tokens <= query_tokens:
                subset_matches.append(key)
        ranked = sorted(
            subset_matches,
            key=lambda key: (self._key_counts.get(key, 0), key),
            reverse=True,
        )
        if ranked:
            return TeamResolution(
                key=ranked[0],
                display=self.display(ranked[0]),
                matched_by="subset",
                alternatives=self._team_refs(ranked[1:5]),
            )

        contains = [
            key for key in self._key_counts
            if parsed.bare in key
            or (key.rsplit("-", 1)[0] and key.rsplit("-", 1)[0] in parsed.bare)
        ]
        ranked_contains = sorted(
            contains, key=lambda key: self._key_counts.get(key, 0), reverse=True
        )
        if ranked_contains:
            return TeamResolution(
                key=ranked_contains[0],
                display=self.display(ranked_contains[0]),
                matched_by="fuzzy",
                alternatives=self._team_refs(ranked_contains[1:5]),
            )
        return TeamResolution()

    def _team_refs(self, keys: list[str]) -> list[dict]:
        return [{"key": key, "display": self.display(key)} for key in keys]


# ----------------------------------------------------------------------
# Date and numeric parsing
# ----------------------------------------------------------------------
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_date(value) -> date | None:
    """Parse the date formats used across the datasets."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _INVALID_VALUES:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})", text)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None
    return None


def parse_int(value) -> int | None:
    """Parse integers accepting empty markers and float-formatted values."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _INVALID_VALUES:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def norm_text(value: str) -> str:
    """Accent- and case-insensitive comparison form of a free-text value."""
    return base_norm(value)
