"""Team-name canonicalisation and the team registry.

The six source datasets spell the same club in many ways (see the spec's
"Data Quality Notes"):

* with a state suffix:        ``Palmeiras-SP``, ``Flamengo - RJ``
* without a suffix:           ``Palmeiras``, ``Flamengo``
* accented vs plain ASCII:    ``Grêmio`` vs ``Gremio-RS``
* full legal names:           ``Sport Club Corinthians Paulista``
* dotted lowercase:           ``A.b.c. - RN``
* full names + suffix:        ``Atlético Mineiro - MG``
* FIFA spellings:             ``Atlético Paranaense``, ``América FC (Minas Gerais)``

Canonicalisation pipeline (order matters):

1. lowercase, strip accents, remove dots/quotes, drop parenthesised
   segments (kept for a small special-alias check first);
2. extract a trailing Brazilian state (UF) code, e.g. ``- SP``;
3. strip club-designator tokens (``EC``, ``FC``, ``AD``) from the name
   edges;
4. resolve full-name aliases (``atletico mineiro`` -> ``atletico mg``);
5. attach the UF only when the bare base is *ambiguous* — i.e. the same
   base is used by different clubs in different states (``atletico``,
   ``america``, ``botafogo``, ``flamengo``, ``santos``, ...).  Bare
   occurrences of an ambiguous base resolve to the variant with the most
   recorded matches (so ``Santos`` -> ``santos sp``, not ``santos ap``);
6. a few bare spellings are pinned by hand where count-dominance would
   misfire (the post-2019 ``Athletico`` rename always means the Paraná
   club).

The result is a stable *canonical key* per club, e.g. ``palmeiras``,
``atletico mg``, ``santos sp``, plus a :class:`TeamRegistry` that maps
every observed raw spelling to its key and tracks pretty display names.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# ---------------------------------------------------------------- constants

#: The 27 Brazilian federative-unit (UF) codes.
UF_CODES = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

#: Club-designator tokens stripped from name edges (never the whole name).
LEADING_DESIGNATORS = frozenset({"ad", "aa", "ec", "fc"})
TRAILING_DESIGNATORS = frozenset({"ec", "fc"})

#: Checked on the *full* normalised string (before parenthetical removal),
#: for FIFA spellings that would otherwise lose their distinguishing part.
SPECIAL_FULL_ALIASES = {
    "america fc minas gerais": "america mg",  # FIFA "América FC (Minas Gerais)"
}

#: Full-name aliases -> complete canonical keys (UF included where the
#: base is ambiguous).
BASE_ALIASES = {
    "atletico mineiro": "atletico mg",
    "atletico goianiense": "atletico go",
    "atletico paranaense": "atletico pr",
    "athletico paranaense": "atletico pr",
    "sport club do recife": "sport",
    "sport recife": "sport",
    "sport club corinthians paulista": "corinthians",
    "clube de regatas do flamengo": "flamengo rj",
    "vasco da gama": "vasco",
    "flamengo do piaui": "flamengo pi",
    "nautico capibaribe": "nautico pe",
    "portuguesa desportos": "portuguesa",
    "ceara sporting club": "ceara",
    "parana clube": "parana",
    "gremio foot ball porto alegrense": "gremio",
    "botafogo de futebol e regatas": "botafogo rj",
    "red bull bragantino": "bragantino sp",
}

#: Spelling unification applied before attaching a UF (the Paraná club was
#: renamed Atlético -> Athletico in 2019; both spellings mean the same
#: club when a state suffix is present).
SPELLING_UNIFY = {
    "athletico": "atletico",
    "atletico paranaense": "atletico pr",  # redundant safety net
}

#: Bare (no UF) spellings pinned to one club because count-dominance
#: would misfire: the post-2019 rename ``Athletico`` only ever means the
#: Paraná club (e.g. Libertadores rows), while count-dominance for the
#: bare base ``atletico`` would pick Atlético-MG.
BARE_ALIASES = {
    "athletico": "atletico pr",
    "athletico paranaense": "atletico pr",
    "atletico paranaense": "atletico pr",
}

_MISSING = {"", "na", "n/a", "-", "none", "null", "tbd", "unknown"}

_Dots_RE = re.compile(r"[.\u2019'`]+")


def strip_accents(text: str) -> str:
    """Return ``text`` with accents removed (São Paulo -> Sao Paulo)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _preprocess(raw: str) -> str:
    """Lowercase, de-accent, drop punctuation noise, collapse spaces."""
    text = strip_accents(raw).lower()
    text = _Dots_RE.sub("", text)  # "A.b.c." -> "abc"
    text = re.sub(r"[\"']", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_parenthetical(text: str) -> tuple[str, str]:
    """Split ``"x (y)"`` into ``("x", "x y")`` (content kept for aliases)."""
    match = re.search(r"\(([^)]*)\)", text)
    if not match:
        return text, text
    plain = (text[: match.start()] + " " + text[match.end() :]).strip()
    with_content = re.sub(r"[()]", " ", text)
    return _collapse(plain), _collapse(with_content)


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_designators(base: str) -> str:
    tokens = base.split()
    while len(tokens) > 1 and tokens[0] in LEADING_DESIGNATORS:
        tokens.pop(0)
    while len(tokens) > 1 and tokens[-1] in TRAILING_DESIGNATORS:
        tokens.pop()
    return " ".join(tokens)


def _extract_uf(base: str) -> tuple[str, str | None]:
    """Split a trailing UF code: ``"flamengo - rj"`` -> ``("flamengo", "RJ")``."""
    match = re.search(r"(.*?)[\s]*[-\u2013]\s*([a-z]{2})$", base)
    if match and match.group(2).upper() in UF_CODES:
        return _collapse(match.group(1)), match.group(2).upper()
    tokens = base.split()
    if len(tokens) > 1 and tokens[-1].upper() in UF_CODES and len(tokens[-1]) == 2:
        return " ".join(tokens[:-1]), tokens[-1].upper()
    return base, None


# ---------------------------------------------------------------- registry


@dataclass
class TeamEntry:
    """A canonical club: key, display name, raw variants, competitions."""

    key: str
    display: str = ""
    variants: dict[str, int] = field(default_factory=dict)  # raw -> count
    uf: str | None = None
    match_count: int = 0
    competitions: set[str] = field(default_factory=set)
    seasons: set[int] = field(default_factory=set)

    def add_variant(self, raw: str, count: int = 1) -> None:
        self.variants[raw] = self.variants.get(raw, 0) + count


@dataclass(frozen=True)
class Resolution:
    """A candidate team for a user query."""

    key: str
    display: str
    match_count: int
    exact: bool

    def __str__(self) -> str:  # pragma: no cover - convenience
        return f"{self.display} ({self.match_count} matches)"


class TeamRegistry:
    """Two-pass registry: ingest raw names, then finalise canonical keys.

    Pass 1 (:meth:`ingest`) collects raw spellings and their UF usage so
    that ambiguous bases can be detected.  :meth:`finalize` then computes
    every key, picks display names and dominance winners.
    """

    def __init__(self) -> None:
        self._raw_counts: dict[str, int] = {}
        self._base_uf_counts: dict[str, dict[str, int]] = {}
        self.entries: dict[str, TeamEntry] = {}
        self._finalized = False

    # -- pass 1 ---------------------------------------------------------

    def ingest(self, raw: str, count: int = 1) -> None:
        """Record a raw team spelling (call once per occurrence or bulk)."""
        if self._finalized:  # pragma: no cover - misuse guard
            raise RuntimeError("registry already finalized")
        key = _preprocess(raw)
        if not key or key in _MISSING:
            return
        self._raw_counts[raw] = self._raw_counts.get(raw, 0) + count
        plain, with_paren = _split_parenthetical(key)
        if plain in SPECIAL_FULL_ALIASES or with_paren in SPECIAL_FULL_ALIASES:
            return  # special aliases carry their own UF info
        base, uf = _extract_uf(plain)
        base = _strip_designators(base)
        if uf:
            self._base_uf_counts.setdefault(base, {}).setdefault(uf, 0)
            self._base_uf_counts[base][uf] += count

    # -- pass 2 ---------------------------------------------------------

    def finalize(self) -> "TeamRegistry":
        """Compute ambiguity/dominance and build all canonical entries."""
        for raw, count in self._raw_counts.items():
            key = self.key_of(raw)
            entry = self.entries.setdefault(key, TeamEntry(key=key))
            entry.add_variant(raw, count)
        for entry in self.entries.values():
            entry.display = self._pick_display(entry)
            entry.match_count = sum(entry.variants.values())
        self._finalized = True
        return self

    # -- key computation -------------------------------------------------

    def ambiguous_bases(self) -> dict[str, dict[str, int]]:
        """Bases used by different clubs in different states, with counts."""
        return {b: ufs for b, ufs in self._base_uf_counts.items() if len(ufs) > 1}

    def _dominant_uf(self, base: str) -> str | None:
        ufs = self._base_uf_counts.get(base)
        if not ufs:
            return None
        # Most recorded occurrences wins; ties broken alphabetically.
        return max(sorted(ufs), key=lambda uf: ufs[uf])

    def key_of(self, raw: str) -> str:
        """Canonical key for a raw team/user string (deterministic)."""
        key = _preprocess(raw)
        if not key or key in _MISSING:
            return ""
        plain, with_paren = _split_parenthetical(key)
        for candidate in (plain, with_paren):
            if candidate in SPECIAL_FULL_ALIASES:
                return SPECIAL_FULL_ALIASES[candidate]

        base, uf = _extract_uf(plain)
        base = _strip_designators(base)
        if not base:
            return key

        if base in BASE_ALIASES:
            return BASE_ALIASES[base]
        if base in SPELLING_UNIFY and SPELLING_UNIFY[base] != base and uf:
            base = SPELLING_UNIFY[base]
            if base in BASE_ALIASES:  # e.g. "athletico paranaense - PR"
                return BASE_ALIASES[base]
            uf = None if not self._is_ambiguous(base) else uf
            return f"{base} {uf.lower()}" if uf else base

        ambiguous = self._is_ambiguous(base)
        if uf:
            return f"{base} {uf.lower()}" if ambiguous else base

        # Bare form of an ambiguous base.
        if base in BARE_ALIASES:
            return BARE_ALIASES[base]
        if ambiguous:
            dominant = self._dominant_uf(base)
            if dominant:
                return f"{base} {dominant.lower()}"
        return base

    def _is_ambiguous(self, base: str) -> bool:
        return len(self._base_uf_counts.get(base, {})) > 1

    # -- lookups ---------------------------------------------------------

    def entry_of(self, key: str) -> TeamEntry | None:
        return self.entries.get(key)

    def display_of(self, key: str) -> str:
        entry = self.entries.get(key)
        return entry.display if entry and entry.display else key

    def _pick_display(self, entry: TeamEntry) -> str:
        def has_accent(raw: str) -> bool:
            return any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", raw))

        # Prefer the proper Portuguese spelling (accents) when it is at
        # least half as frequent as the plain-ASCII winner, so "Avaí" and
        # "Vitória" beat "Avai"/"Vitoria" but a one-off accented typo
        # cannot displace a dominant spelling.
        best_plain = max((c for raw, c in entry.variants.items() if not has_accent(raw)), default=0)

        def quality(raw: str) -> tuple:
            count = entry.variants[raw]
            accent_qualifies = has_accent(raw) and count * 2 >= best_plain
            return (accent_qualifies, count, len(raw))

        best = max(entry.variants, key=quality)
        # Drop noisy parentheticals; tidy "Name - SP" into "Name-SP".
        display = _split_parenthetical(best)[0].strip(" -") or best
        display = re.sub(r"\s*[-\u2013]\s*", "-", display)
        # Cosmetic: strip designator tokens from the edges ("EC Bahia" -> "Bahia").
        tokens = display.split()
        while len(tokens) > 1 and tokens[0].lower() in LEADING_DESIGNATORS:
            tokens.pop(0)
        while len(tokens) > 1 and tokens[-1].lower() in TRAILING_DESIGNATORS:
            tokens.pop()
        return " ".join(tokens)

    def resolve(self, query: str, limit: int = 8) -> list[Resolution]:
        """Rank canonical teams matching a user query.

        Exact key match first; then clubs sharing the query's base (for
        ambiguous bases like ``Atlético``); then containment matches.
        """
        if not query or not query.strip():
            return []
        key = self.key_of(query)
        exact = self.entries.get(key)
        results: list[Resolution] = []
        if exact:
            results.append(Resolution(key, exact.display, exact.match_count, True))
        query_norm = _preprocess(query)
        plain, _ = _split_parenthetical(query_norm)
        base, _ = _extract_uf(plain)
        base = _strip_designators(base)
        for entry_key, entry in self.entries.items():
            if entry_key == key:
                continue
            if base and (entry_key == base or entry_key.startswith(base + " ")):
                results.append(Resolution(entry_key, entry.display, entry.match_count, False))
        if not results:
            # Containment fallback for partial names ("palmeiras" style).
            for entry_key, entry in self.entries.items():
                if query_norm and query_norm in entry_key:
                    results.append(Resolution(entry_key, entry.display, entry.match_count, False))
        results.sort(key=lambda r: (not r.exact, -r.match_count, r.key))
        return results[:limit]

    def resolve_one(self, query: str) -> Resolution | None:
        """Best single resolution for a query (top of :meth:`resolve`)."""
        results = self.resolve(query)
        return results[0] if results else None

    def alternatives_note(self, query: str) -> str:
        """Helper text listing other teams that also matched a query."""
        results = self.resolve(query)
        if len(results) <= 1:
            return ""
        others = ", ".join(f"{r.display} ({r.match_count})" for r in results[1:5])
        return f"Note: other matching teams: {others}"


__all__ = [
    "TeamRegistry",
    "TeamEntry",
    "Resolution",
    "UF_CODES",
    "strip_accents",
]
