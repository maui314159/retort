"""Team name normalization for Brazilian soccer datasets.

The six source datasets name teams inconsistently:

* with a state suffix:        "Palmeiras-SP", "Flamengo - RJ", "Botafogo RJ"
* without a suffix:           "Palmeiras", "Flamengo"
* full legal names:           "Sport Club Corinthians Paulista"
* with foreign country codes: "Barcelona-EQU", "Nacional (URU)"
* with accents or without:    "Grêmio" vs "Gremio"

This module maps every variant onto a stable canonical key.  The key keeps
the state/country discriminator only when the bare base name is ambiguous
across the whole dataset (e.g. "atletico" -> "atletico-mg" / "atletico-pr" /
"atletico-go", but "palmeiras" stays "palmeiras").  Stateless names of
ambiguous clubs are resolved to the variant with the most recorded matches
(Botafogo -> Botafogo-RJ, Santos -> Santos-SP, ...).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Optional

BRAZILIAN_STATES = frozenset(
    {
        "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt",
        "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro",
        "rr", "sc", "sp", "se", "to",
    }
)

FOREIGN_COUNTRY_CODES = frozenset(
    {"arg", "bol", "bra", "chi", "col", "ecu", "equ", "mex", "par", "per", "uru", "ven"}
)

TEAM_ALIASES = {
    "atletico mineiro": ("atletico", "mg"),
    "clube atletico mineiro": ("atletico", "mg"),
    "atletico paranaense": ("atletico", "pr"),
    "athletico paranaense": ("atletico", "pr"),
    "athletico": ("atletico", "pr"),
    "atletico goianiense": ("atletico", "go"),
    "america fc minas gerais": ("america", "mg"),
    "america fc": ("america", "mg"),
    "ceara sporting club": ("ceara", "ce"),
    "sport club do recife": ("sport", "pe"),
    "sport recife": ("sport", "pe"),
    "esporte clube bahia": ("bahia", "ba"),
    "esporte clube vitoria": ("vitoria", "ba"),
    "vasco": ("vasco da gama", None),
    "cr vasco da gama": ("vasco da gama", None),
    "club de regatas vasco da gama": ("vasco da gama", None),
    "portuguesa desportos": ("portuguesa", None),
    "parana clube": ("parana", None),
    "boavista sport club": ("boavista", None),
    "sao paulo fc": ("sao paulo", None),
    "sc corinthians paulista": ("corinthians", None),
    "sport club corinthians paulista": ("corinthians", None),
    "sociedade esportiva palmeiras": ("palmeiras", None),
    "se palmeiras": ("palmeiras", None),
    "clube de regatas do flamengo": ("flamengo", "rj"),
    "cr flamengo": ("flamengo", "rj"),
    "fluminense football club": ("fluminense", "rj"),
    "santos fc": ("santos", "sp"),
    "gremio foot ball porto alegrense": ("gremio", None),
    "sc internacional": ("internacional", "rs"),
    "sport club internacional": ("internacional", "rs"),
}

BASE_ALIASES = {
    "bragantino": ("red bull bragantino", frozenset({"sp", None})),
    "vasco": ("vasco da gama", frozenset({"rj", None})),
    "novorizontino": ("gremio novorizontino", frozenset({"sp", None})),
}

NICKNAMES = {
    "fla": ("flamengo", "rj"),
    "mengao": ("flamengo", "rj"),
    "flu": ("fluminense", "rj"),
    "timao": ("corinthians", None),
    "verdao": ("palmeiras", None),
    "peixe": ("santos", "sp"),
    "galo": ("atletico", "mg"),
    "raposa": ("cruzeiro", None),
    "furacao": ("atletico", "pr"),
    "leao da ilha": ("sport", None),
}

_STATE_SUFFIX_RE = re.compile(r"^(?P<base>.+?)[\s\-]+(?P<state>[a-z]{2})$")
_COUNTRY_DASH_RE = re.compile(r"^(?P<base>.+?)[\s\-]+(?P<country>[a-z]{3})$")
_COUNTRY_PAREN_RE = re.compile(r"^(?P<base>.+?)\s*\((?P<country>[a-z]{2,3})\)$")


class TeamNotFoundError(ValueError):
    """Raised when a team name cannot be resolved to a known team."""

    def __init__(self, query: str, suggestions: list[str]):
        self.query = query
        self.suggestions = suggestions
        super().__init__(
            f"Team not found: {query!r}"
            + (f". Did you mean: {', '.join(suggestions)}?" if suggestions else "")
        )


def strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def clean_name(raw: str) -> str:
    """Lowercase, de-accent and lightly punctuate a team name.

    Parenthetical qualifiers containing spaces (e.g. "(antigo Esporte Clube
    Barreira)", "(Minas Gerais)") are dropped; short country qualifiers such
    as "(URU)" are kept for suffix detection.
    """
    name = strip_accents(str(raw)).lower()
    name = re.sub(r"\s*\([^)]*\s[^)]*\)", " ", name)
    name = name.replace("'", "").replace(".", " ")
    name = re.sub(r"[\s\-]+", " ", name).strip()
    return name


def _strip_ec_fc(base: str) -> str:
    stripped = base
    if stripped.startswith("ec "):
        stripped = stripped[3:].strip()
    if stripped.endswith(" ec") or stripped.endswith(" fc"):
        stripped = stripped[:-3].strip()
    return stripped


def _split_suffix(cleaned: str) -> tuple[str, Optional[str], Optional[str]]:
    """Split a cleaned name into (base, state, country)."""
    paren = _COUNTRY_PAREN_RE.match(cleaned)
    if paren and paren.group("country") in FOREIGN_COUNTRY_CODES:
        return paren.group("base").strip(), None, paren.group("country")
    state = _STATE_SUFFIX_RE.match(cleaned)
    if state and state.group("state") in BRAZILIAN_STATES:
        return state.group("base").strip(), state.group("state"), None
    country = _COUNTRY_DASH_RE.match(cleaned)
    if country and country.group("country") in FOREIGN_COUNTRY_CODES:
        return country.group("base").strip(), None, country.group("country")
    return cleaned, None, None


class TeamNameRegistry:
    """Two-pass registry that maps raw team names to canonical keys.

    Pass one (`observe`) records every name seen in the match data.  Pass two
    (`canonical_key`, `resolve`) maps names and user queries onto canonical
    keys, keeping state/country suffixes only where they disambiguate.
    """

    def __init__(self) -> None:
        self._suffix_counts: dict[str, Counter] = defaultdict(Counter)
        self._display_counts: dict[str, Counter] = defaultdict(Counter)
        self._variant_counts: dict[str, Counter] = defaultdict(Counter)
        self._match_counts: Counter = Counter()
        self._known_keys: set[str] = set()

    def _decompose(self, raw: str, context: str) -> tuple[str, Optional[str], Optional[str]]:
        cleaned = clean_name(raw)
        if not cleaned:
            return "", None, None
        if cleaned in TEAM_ALIASES:
            base, state = TEAM_ALIASES[cleaned]
            return base, state, None
        base, state, country = _split_suffix(cleaned)
        if base in TEAM_ALIASES:
            alias_base, alias_state = TEAM_ALIASES[base]
            base = alias_base
            state = state or alias_state
        if context == "matches":
            stripped = _strip_ec_fc(base)
            if stripped and stripped != base:
                if stripped in TEAM_ALIASES:
                    alias_base, alias_state = TEAM_ALIASES[stripped]
                    base = alias_base
                    state = state or alias_state
                else:
                    base = stripped
        if base in BASE_ALIASES:
            target, allowed = BASE_ALIASES[base]
            if state is None or state in allowed:
                base = target
                state = None
        return base, state, country

    def observe(self, raw: str) -> None:
        """Record one occurrence of a team name from the match data."""
        base, state, country = self._decompose(raw, context="matches")
        if not base:
            return
        suffix = state or country
        self._suffix_counts[base][suffix] += 1
        self._variant_counts[base][str(raw).strip()] += 1

    def finalize(self) -> None:
        self._known_keys = set(self.iter_keys())

    def _default_suffix(self, base: str) -> Optional[str]:
        counts = self._suffix_counts.get(base)
        if not counts:
            return None
        for suffix, _ in counts.most_common():
            if suffix is not None:
                return suffix
        return None

    def _key_from_parts(self, base: str, suffix: Optional[str]) -> str:
        counts = self._suffix_counts.get(base)
        if not counts:
            return base
        distinct = {s for s in counts if s is not None}
        if len(distinct) <= 1:
            return base
        if suffix is None:
            suffix = self._default_suffix(base)
        if suffix is None:
            return base
        return f"{base}-{suffix}"

    def iter_keys(self):
        for base, counts in self._suffix_counts.items():
            distinct = {s for s in counts if s is not None}
            if len(distinct) <= 1:
                yield base
            else:
                for suffix in distinct:
                    yield f"{base}-{suffix}"

    def canonical_key(self, raw: str, context: str = "matches") -> str:
        """Canonical key for a name appearing in the datasets."""
        base, state, country = self._decompose(raw, context)
        if not base:
            return ""
        return self._key_from_parts(base, state or country)

    def register_display(self, key: str, display: str) -> None:
        self._display_counts[key][display] += 1
        self._match_counts[key] += 1

    def display_name(self, key: str) -> str:
        counts = self._display_counts.get(key)
        if counts:
            return counts.most_common(1)[0][0]
        return key

    def match_count(self, key: str) -> int:
        return self._match_counts.get(key, 0)

    def variants(self, key: str) -> list[str]:
        base = key.rsplit("-", 1)[0] if key not in self._suffix_counts else key
        counts = self._variant_counts.get(base)
        if not counts:
            return []
        return [name for name, _ in counts.most_common()]

    def sibling_keys(self, key: str) -> list[str]:
        base, _, suffix = key.rpartition("-")
        if not suffix or base not in self._suffix_counts:
            return []
        distinct = {s for s in self._suffix_counts[base] if s is not None}
        if len(distinct) <= 1:
            return []
        return sorted(f"{base}-{s}" for s in distinct if f"{base}-{s}" != key)

    def known_keys(self) -> set[str]:
        return self._known_keys

    def _fuzzy_candidates(self) -> dict[str, str]:
        candidates: dict[str, str] = {}
        for key in self._known_keys:
            candidates.setdefault(key, key)
        for base, counts in self._variant_counts.items():
            for variant in counts:
                candidates.setdefault(clean_name(variant), self.canonical_key(variant))
        for key, counts in self._display_counts.items():
            for display in counts:
                candidates.setdefault(clean_name(display), key)
        return candidates

    def resolve(self, query: str) -> tuple[str, str]:
        """Resolve a user-supplied team name to (canonical key, display name).

        Raises TeamNotFoundError with suggestions when nothing matches.
        """
        cleaned = clean_name(query)
        if not cleaned:
            raise TeamNotFoundError(query, [])
        if cleaned in NICKNAMES:
            base, state = NICKNAMES[cleaned]
            key = self._key_from_parts(base, state)
            if key in self._known_keys:
                return key, self.display_name(key)
        if cleaned in TEAM_ALIASES:
            base, state = TEAM_ALIASES[cleaned]
            key = self._key_from_parts(base, state)
            if key in self._known_keys:
                return key, self.display_name(key)
        base, state, country = _split_suffix(cleaned)
        if base in BASE_ALIASES and (state is None or state in BASE_ALIASES[base][1]):
            base = BASE_ALIASES[base][0]
            state = None
        key = self._key_from_parts(base, state or country)
        if key in self._known_keys:
            return key, self.display_name(key)
        if base in self._suffix_counts and state is None:
            suffix = self._default_suffix(base)
            if suffix:
                key = f"{base}-{suffix}"
                if key in self._known_keys:
                    return key, self.display_name(key)
        candidates = self._fuzzy_candidates()
        lowered = {c.lower(): k for c, k in candidates.items()}
        if cleaned in lowered:
            return lowered[cleaned], self.display_name(lowered[cleaned])
        starts = [(c, k) for c, k in lowered.items() if c.startswith(cleaned) and len(cleaned) >= 4]
        if len(starts) == 1:
            return starts[0][1], self.display_name(starts[0][1])
        contains = [(c, k) for c, k in lowered.items() if cleaned in c and len(cleaned) >= 4]
        ranked = sorted(contains, key=lambda ck: (len(ck[0]), -self.match_count(ck[1])))
        if ranked:
            return ranked[0][1], self.display_name(ranked[0][1])
        if len(starts) > 1:
            best = sorted(starts, key=lambda ck: -self.match_count(ck[1]))
            return best[0][1], self.display_name(best[0][1])
        known = list(lowered.keys())
        close = difflib.get_close_matches(cleaned, known, n=3, cutoff=0.6)
        if close:
            close_keys = {lowered[c] for c in close}
            if len(close_keys) == 1:
                key = close_keys.pop()
                return key, self.display_name(key)
            ranked = sorted(
                close,
                key=lambda c: difflib.SequenceMatcher(None, cleaned, c).ratio(),
                reverse=True,
            )
            best = ranked[0]
            if difflib.SequenceMatcher(None, cleaned, best).ratio() >= 0.85:
                return lowered[best], self.display_name(lowered[best])
        raise TeamNotFoundError(query, [lowered[c] for c in close] or sorted(known)[:5])
