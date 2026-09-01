"""Team name normalisation and the canonical team registry.

The datasets name the same club in many shapes:

* with a state suffix:        ``Palmeiras-SP``, ``América - MG``
* without a suffix:           ``Palmeiras``, ``América``
* full/official names:        ``Sport Club Corinthians Paulista``
* accented vs plain:          ``Grêmio`` vs ``Gremio``
* foreign clubs with country: ``Nacional (URU)``, ``Olimpia-PAR``

This module turns every raw spelling into a canonical team id such as
``"palmeiras-sp"`` or ``"nacional-uru"`` and provides a registry that can
resolve user queries ("Flamengo", "atletico", "Athletico Paranaense") to a
canonical team, disambiguating by prominence when the base name is shared
by several clubs (``Atlético-MG`` vs ``Atlético-GO`` vs ``Atlético-PR``).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Brazilian state (UF) abbreviations used as team-name suffixes.
BRAZILIAN_UFS = frozenset(
    {
        "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt",
        "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro",
        "rr", "sc", "sp", "se", "to",
    }
)

#: Country markers used in the Libertadores dataset, e.g. "Nacional (URU)".
FOREIGN_MARKERS = frozenset(
    {
        "uru", "par", "equ", "arg", "chi", "col", "per", "bol", "ven",
        "mex", "usa", "jpn", "kor", "crc", "gtm", "hon", "slv", "pan",
        "can", "dom",
    }
)

#: Filler tokens dropped from names ("Boavista Sport Club (antigo ...)").
_FILLER = frozenset({"antigo"})

#: Club legal-form tokens stripped from the ends of names ("EC Bahia" -> "Bahia").
_FORM_TOKENS = frozenset({"fc", "ec", "sc", "ac", "cbf"})

#: Curated key merges: keys produced by :func:`team_key` that refer to the
#: same club under a structurally different spelling.  Most cross-file
#: unification is automatic (bare name + state-suffixed twin); this table
#: handles full names such as "Atletico Mineiro" == "Atlético-MG" and the
#: historical "Atlético-PR" == "Athletico-PR" spellings.
ALIASES: dict[str, str] = {
    "atletico-mineiro": "atletico-mg",
    "atletico-mineiro-mg": "atletico-mg",
    "atletico-paranaense": "athletico-pr",
    "atletico-paranaense-pr": "athletico-pr",
    "atletico-pr": "athletico-pr",
    "athletico-paranaense": "athletico-pr",
    "athletico-paranaense-pr": "athletico-pr",
    "atletico-goianiense": "atletico-go",
    "atletico-goianiense-go": "atletico-go",
    "atletico-goianiense-go-go": "atletico-go",
    "sport-recife": "sport-pe",
    "sport-recife-pe": "sport-pe",
    "sport-club-do-recife": "sport-pe",
    "nautico-capibaribe": "nautico-pe",
    "nautico-capibaribe-pe": "nautico-pe",
    "nautico": "nautico-pe",
    "ceara-sporting-club": "ceara-ce",
    "ceara-sporting-club-ce": "ceara-ce",
    "america-fc-minas-gerais": "america-mg",
    "corinthians-paulista": "corinthians-sp",
    "sport-club-corinthians-paulista": "corinthians-sp",
    "rb-bragantino": "red-bull-bragantino-sp",
    "bragantino-sp": "red-bull-bragantino-sp",
    # bare "Bragantino" (BR-Football) is the São Paulo club, whose official
    # name became "Red Bull Bragantino"; the explicit "-PA" spelling is a
    # different, tiny Pará club and stays separate
    "bragantino": "red-bull-bragantino-sp",
    "operario-ferroviario-esporte-c-pr": "operario-pr",
    "operario-ferroviario": "operario-pr",
    # "Vasco" + state-hint (novo file) vs "Vasco da Gama" elsewhere
    "vasco": "vasco-da-gama-rj",
    "vasco-rj": "vasco-da-gama-rj",
    # BR-Football spellings for clubs named elsewhere with a suffix
    "ca-parana": "parana-pr",
    "america-fc-natal": "america-rn",
    "cs-alagoano": "csa-al",
    "cs-sergipe": "sergipe-se",
    "atletico-acreano": "atletico-ac",
    "clube-do-remo": "remo-pa",
}


#: Display names for prominent clubs (accents restored; the state suffix is
#: kept only where the bare base name would be ambiguous).
_DISPLAY_OVERRIDES = {
    "flamengo-rj": "Flamengo",
    "fluminense-rj": "Fluminense",
    "vasco-da-gama-rj": "Vasco da Gama",
    "botafogo-rj": "Botafogo",
    "palmeiras-sp": "Palmeiras",
    "corinthians-sp": "Corinthians",
    "sao-paulo-sp": "São Paulo",
    "santos-sp": "Santos",
    "portuguesa-sp": "Portuguesa",
    "ponte-preta-sp": "Ponte Preta",
    "red-bull-bragantino-sp": "Red Bull Bragantino",
    "guarani-sp": "Guarani",
    "santo-andre-sp": "Santo André",
    "sao-caetano-sp": "São Caetano",
    "gremio-rs": "Grêmio",
    "internacional-rs": "Internacional",
    "juventude-rs": "Juventude",
    "caxias-rs": "Caxias",
    "atletico-mg": "Atlético-MG",
    "america-mg": "América-MG",
    "cruzeiro-mg": "Cruzeiro",
    "athletico-pr": "Athletico-PR",
    "coritiba-pr": "Coritiba",
    "parana-pr": "Paraná",
    "sport-pe": "Sport",
    "santa-cruz-pe": "Santa Cruz",
    "nautico-pe": "Náutico",
    "bahia-ba": "Bahia",
    "vitoria-ba": "Vitória-BA",
    "ceara-ce": "Ceará",
    "fortaleza-ce": "Fortaleza",
    "goias-go": "Goiás",
    "vila-nova-go": "Vila Nova",
    "atletico-go": "Atlético-GO",
    "avai-sc": "Avaí",
    "chapecoense-sc": "Chapecoense",
    "figueirense-sc": "Figueirense",
    "criciuma-sc": "Criciúma",
    "csa-al": "CSA",
    "crb-al": "CRB",
    "remo-pa": "Remo",
    "paysandu-pa": "Paysandu",
    "ipatinga-mg": "Ipatinga",
    "barueri-sp": "Barueri",
    "sao-jose-rs": "São José",
    "sao-luiz-rs": "São Luiz",
    "sao-bento-sp": "São Bento",
    "sao-bernardo-sp": "São Bernardo",
    "vitoria-da-conquista-ba": "Vitória da Conquista",
    "novo-hamburgo-rs": "Novo Hamburgo",
    "brasil-de-pelotas-rs": "Brasil de Pelotas",
    "cuiaba-mt": "Cuiabá",
    "atletico-ba": "Atlético-BA",
    "4-de-julho-pi": "4 de Julho-PI",
    "river-plate-uru": "River Plate (URU)",
}


# --------------------------------------------------------------------------- #
# Name cleaning
# --------------------------------------------------------------------------- #


def strip_accents(text: str) -> str:
    """Return ``text`` with accents removed (São Paulo -> Sao Paulo)."""
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )


def _clean_tokens(raw: str) -> list[str]:
    """Lower-case, de-accent, drop parentheses/filler and club-form tokens."""
    text = strip_accents(raw).lower()
    text = re.sub(r"\([^)]*\)", " ", text)  # drop parenthetical remarks
    text = re.sub(r"[^a-z0-9]+", " ", text)  # punctuation -> spaces
    tokens = [t for t in text.split() if t not in _FILLER]
    # Strip a single leading/trailing club-form token ("EC Bahia", "Fortaleza FC").
    if len(tokens) > 1:
        if tokens[0] in _FORM_TOKENS:
            tokens = tokens[1:]
        elif tokens[-1] in _FORM_TOKENS:
            tokens = tokens[:-1]
    return tokens


def team_key(raw: str, uf_hint: str | None = None) -> str:
    """Compute the canonical team id for a raw name.

    ``uf_hint`` is the state column value some datasets provide next to the
    team name; it is only consulted when the name itself carries no
    recognisable suffix.
    """
    tokens = _clean_tokens(raw)
    if not tokens:
        return ""

    uf = None
    country = None
    if tokens[-1] in BRAZILIAN_UFS:
        uf = tokens[-1]
        tokens = tokens[:-1]
    elif tokens[-1] in FOREIGN_MARKERS and len(tokens) > 1:
        country = tokens[-1]
        tokens = tokens[:-1]
    elif uf_hint:
        hint = strip_accents(uf_hint).lower().strip()
        if hint in BRAZILIAN_UFS:
            uf = hint

    if not tokens:  # the name was only a suffix
        return (uf or country or "")

    key = "-".join(tokens)
    if uf:
        key += f"-{uf}"
    elif country:
        key += f"-{country}"

    return ALIASES.get(key, key)


def base_name(canonical: str) -> str:
    """Return the base name of a canonical id without its suffix, if any."""
    tokens = canonical.split("-")
    while len(tokens) > 1 and (
        tokens[-1] in BRAZILIAN_UFS or tokens[-1] in FOREIGN_MARKERS
    ):
        tokens = tokens[:-1]
    return "-".join(tokens)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


class TeamNotFound(LookupError):
    """Raised when a team name cannot be resolved to any known club."""


class ResolveResult:
    """Outcome of resolving a user-provided team name."""

    def __init__(self, canonical: str, display: str, alternatives: list[str]):
        self.canonical = canonical
        self.display = display
        self.alternatives = alternatives

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"<ResolveResult {self.canonical!r} alternatives={self.alternatives}>"


class TeamRegistry:
    """Registry of every team seen in the datasets.

    Built dynamically while loading: every raw spelling is converted to a
    canonical key, then :meth:`merge_bare_keys` folds bare keys (no state
    suffix) into their state-suffixed twin -- automatically when unique,
    otherwise by prominence (match appearances).
    """

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()  # canonical -> appearances
        self._redirects: dict[str, str] = {}  # folded key -> final key
        self._canonical_cache: dict[tuple[str, str], str] = {}
        self._merged = False

    # -- building ---------------------------------------------------------- #

    def note(self, raw: str, uf_hint: str | None = None) -> None:
        """Record one appearance of a raw team name."""
        self._counts[team_key(raw, uf_hint)] += 1

    def merge_bare_keys(self) -> None:
        """Fold bare keys (no state suffix) into state-suffixed twins.

        ``"palmeiras"`` becomes ``"palmeiras-sp"`` because that is the only
        club with that base; for ambiguous bases like ``"santos"`` the most
        prominent twin wins (Santos FC of São Paulo, not Santos-AP).
        """
        if self._merged:
            return

        # Apply curated aliases first so the folds operate on post-alias keys.
        for key in list(self._counts):
            target = ALIASES.get(key)
            if target is not None and target != key:
                self._counts[target] += self._counts.pop(key)
                self._redirects[key] = target

        bases: dict[str, list[str]] = {}
        for canonical in self._counts:
            bases.setdefault(base_name(canonical), []).append(canonical)

        for base, twins in bases.items():
            if len(twins) <= 1:
                continue
            bare = base  # the bare key form equals its own base name
            suffixed = [t for t in twins if t != base_name(t)]
            if not suffixed or bare in suffixed:
                continue
            if len(suffixed) == 1:
                target = suffixed[0]
            else:
                target = max(suffixed, key=lambda t: self._counts[t])
            if bare in self._counts:
                self._counts[target] += self._counts.pop(bare)
                self._redirects[bare] = target

        # Chase alias redirects through to the final key.
        def _final(key: str) -> str:
            seen = set()
            while key in self._redirects and key not in seen:
                seen.add(key)
                key = self._redirects[key]
            return key

        self._redirects = {k: _final(v) for k, v in self._redirects.items()}
        self._canonical_cache.clear()
        self._merged = True

    # -- canonicalisation --------------------------------------------------- #

    def canonical(self, raw: str, uf_hint: str | None = None) -> str:
        """Final canonical id for a raw name (memoised).

        Applies :func:`team_key`, curated aliases, merge redirects, and a
        final base-name fold so bare spellings ("Grêmio") land on the
        state-suffixed club actually present in the data ("gremio-rs").
        Unknown/foreign names are returned unchanged.
        """
        cache_key = (raw.strip().lower(), uf_hint or "")
        if cache_key in self._canonical_cache:
            return self._canonical_cache[cache_key]

        def _alias(key: str) -> str:
            return ALIASES.get(key, key)

        key = _alias(team_key(raw, uf_hint))
        key = self._redirects.get(key, key)
        if key not in self._counts:
            base = base_name(key)
            twins = [
                c for c in self._counts
                if base_name(c) == base and c != key
            ]
            if len(twins) == 1:
                key = twins[0]
            elif twins:
                key = max(twins, key=lambda t: self._counts[t])
            key = self._redirects.get(_alias(key), key)

        self._canonical_cache[cache_key] = key
        return key

    def display(self, canonical: str) -> str:
        """Human-readable display name for a canonical id."""
        if canonical in _DISPLAY_OVERRIDES:
            return _DISPLAY_OVERRIDES[canonical]
        return canonical.replace("-", " ").title()

    # -- querying ----------------------------------------------------------- #

    def __contains__(self, canonical: str) -> bool:
        return canonical in self._counts

    def __len__(self) -> int:
        return len(self._counts)

    def known_teams(self) -> list[str]:
        return sorted(self._counts)

    def match_count(self, canonical: str) -> int:
        return self._counts.get(canonical, 0)

    def _base_index(self) -> dict[str, set[str]]:
        bases: dict[str, set[str]] = {}
        for canonical in self._counts:
            bases.setdefault(base_name(canonical), set()).add(canonical)
        return bases

    def _alternatives_for(self, canonical: str) -> list[str]:
        base = base_name(canonical)
        return [
            self.display(other)
            for other in self._counts
            if other != canonical and base_name(other) == base
        ][:4]

    def resolve(self, query: str) -> ResolveResult:
        """Resolve a user-supplied team name to a canonical team.

        Strategy (in order): exact canonical key -> unique base match ->
        most prominent base match -> fuzzy substring / similarity match.
        Raises :class:`TeamNotFound` when nothing is close enough.
        """
        if not query or not query.strip():
            raise TeamNotFound("Empty team name")

        key = self.canonical(query)
        if key in self._counts:
            return ResolveResult(key, self.display(key), self._alternatives_for(key))

        q_base = base_name(key) if key else strip_accents(query).lower()
        bases = self._base_index()
        if q_base in bases:
            twins = bases[q_base]
            if len(twins) == 1:
                canonical = next(iter(twins))
                return ResolveResult(canonical, self.display(canonical), [])
            ranked = sorted(twins, key=lambda t: -self._counts[t])
            return ResolveResult(ranked[0], self.display(ranked[0]), ranked[1:5])

        # Fuzzy: containment on base names, then similarity ranking.
        candidates = {
            canonical
            for canonical in self._counts
            if q_base in base_name(canonical) or base_name(canonical) in q_base
        }
        if not candidates:
            lowered = strip_accents(query).lower()
            candidates = {
                canonical
                for canonical in self._counts
                if lowered in base_name(canonical) or base_name(canonical) in lowered
            }
        if not candidates:
            matches = difflib.get_close_matches(
                q_base, [base_name(c) for c in self._counts], n=5, cutoff=0.6
            )
            candidates = {c for c in self._counts if base_name(c) in matches}
        if not candidates:
            raise TeamNotFound(f"No team matching {query!r} in the dataset")

        ranked = sorted(candidates, key=lambda t: (-self._counts[t], base_name(t)))
        return ResolveResult(ranked[0], self.display(ranked[0]), ranked[1:5])

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search teams by name; returns display info for tooling/LLMs."""
        q_key = team_key(query)
        q_base = base_name(q_key) if q_key else strip_accents(query).lower()
        q_lower = strip_accents(query).lower()

        scored: list[tuple[int, int, str]] = []
        for canonical, count in self._counts.items():
            base = base_name(canonical)
            if base == q_base:
                score = 100
            elif q_base in base or base in q_base:
                score = 60
            elif q_lower in base or base in q_lower:
                score = 40
            else:
                continue
            scored.append((score, count, canonical))
        scored.sort(key=lambda t: (-t[0], -t[1]))
        return [
            {
                "id": canonical,
                "name": self.display(canonical),
                "matches_in_dataset": count,
            }
            for _score, count, canonical in scored[:limit]
        ]
