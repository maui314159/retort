"""Team-name normalization for Brazilian soccer datasets.

Why this module exists
----------------------
The six provided CSV files write the same club in many different ways:

* with a state suffix:          "Palmeiras-SP", "América - MG", "America MG"
* with the full legal name:     "Sport Club Corinthians Paulista"
* with a country qualifier:     "Nacional (URU)", "Barcelona-EQU", "Guaraní-PAR"
* with or without accents:      "São Paulo" vs "Sao Paulo", "Grêmio" vs "Gremio"
* with spelling drift:          "Athletico Paranaense" vs "Atlético Paranaense"

To answer questions across files, every raw name is folded to a single
canonical *key* (a lowercase, accent-stripped, alphanumeric-only string).

Resolution algorithm (``team_key``)
-----------------------------------
1. Compact the raw name *keeping* parentheses content and suffixes
   ("Guaraní (PAR)" -> "guaranipar") and look it up in ``ALIASES``.
2. Strip parenthetical content and any trailing 2-3 letter state/country
   code ("Palmeiras-SP" -> "Palmeiras") and compact again.
   * If the base names a canonical club (``CLUBS``) and the stripped state
     matches the club's home state (or there was no state), the canonical
     key is returned.
   * If the state differs, the club is a *namesake* (e.g. "Flamengo - PI"
     is not Rio's Flamengo) and the state is kept in the key
     ("flamengopi").
   * Unclaimed bases keep their state suffix too ("operariopr").
3. Anything unknown falls back to the compacted base name.

A ``TeamRegistry`` is built at load time from every name seen in the data;
it records the variants, source files and a human-friendly display name
for each key, and offers forgiving (substring / fuzzy) lookup for queries
like "palmeiras", "corinthians" or "sport club corinthians paulista".
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Optional

__all__ = [
    "fold",
    "compact",
    "team_key",
    "team_state",
    "Club",
    "TeamInfo",
    "TeamRegistry",
    "build_registry",
    "CLUBS",
    "ALIASES",
]

# ---------------------------------------------------------------------------
# Text folding helpers
# ---------------------------------------------------------------------------


def fold(text: str) -> str:
    """Lowercase and strip accents ("São Paulo" -> "sao paulo")."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def compact(text: str) -> str:
    """Fold and keep only alphanumerics ("Vasco da Gama - RJ" -> "vascodagamarj")."""
    return "".join(ch for ch in fold(text) if ch.isalnum())


_PAREN_RE = re.compile(r"\([^)]*\)")
# Trailing state/country code, e.g. "-SP", " - MG", " EQU", " - POA".
# The code must be upper-case in the original text so real words such as
# "Boa" or "Mixto" are never stripped.
_STATE_RE = re.compile(r"(?:[-–]|\s)\s*([A-Z]{2,3})$")


def _split_base(raw: str) -> tuple[str, Optional[str]]:
    """Remove parenthetical content and a trailing state/country code.

    Returns ``(base, state)`` where *state* is the stripped code (e.g.
    "SP", "MG", "EQU") or ``None``.
    """
    name = (raw or "").strip()
    name = _PAREN_RE.sub(" ", name).strip()
    match = _STATE_RE.search(name)
    if match:
        state = match.group(1)
        base = name[: match.start()].strip(" -–\t")
        if base:
            return base, state
    return name, None


# ---------------------------------------------------------------------------
# Canonical clubs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Club:
    """A canonical club: display name plus its home state (Brazilian clubs)."""

    key: str
    display: str
    state: Optional[str] = None


CLUBS: dict[str, Club] = {
    club.key: club
    for club in [
        # Rio de Janeiro
        Club("flamengo", "Flamengo", "RJ"),
        Club("fluminense", "Fluminense", "RJ"),
        Club("botafogo", "Botafogo", "RJ"),
        Club("vascodagama", "Vasco da Gama", "RJ"),
        # São Paulo
        Club("corinthians", "Corinthians", "SP"),
        Club("palmeiras", "Palmeiras", "SP"),
        Club("saopaulo", "São Paulo", "SP"),
        Club("santos", "Santos", "SP"),
        Club("pontepreta", "Ponte Preta", "SP"),
        Club("portuguesa", "Portuguesa", "SP"),
        Club("guarani", "Guarani", "SP"),
        Club("saocaetano", "São Caetano", "SP"),
        Club("redbullbragantino", "Red Bull Bragantino", "SP"),
        Club("santoandre", "Santo André", "SP"),
        Club("barueri", "Barueri", "SP"),
        Club("gremionovorizontino", "Grêmio Novorizontino", "SP"),
        # Rio Grande do Sul
        Club("gremio", "Grêmio", "RS"),
        Club("internacional", "Internacional", "RS"),
        Club("juventude", "Juventude", "RS"),
        Club("criciuma", "Criciúma", "SC"),  # SC, see below
        # Paraná
        Club("coritiba", "Coritiba", "PR"),
        Club("atleticoparanaense", "Athletico Paranaense", "PR"),
        Club("parana", "Paraná", "PR"),
        # Minas Gerais
        Club("atleticomineiro", "Atlético Mineiro", "MG"),
        Club("cruzeiro", "Cruzeiro", "MG"),
        Club("americamineiro", "América Mineiro", "MG"),
        Club("ipatinga", "Ipatinga", "MG"),
        # Bahia
        Club("bahia", "Bahia", "BA"),
        Club("vitoria", "Vitória", "BA"),
        # Pernambuco
        Club("sportrecife", "Sport Recife", "PE"),
        Club("nautico", "Náutico", "PE"),
        Club("santacruz", "Santa Cruz", "PE"),
        # Ceará
        Club("ceara", "Ceará", "CE"),
        Club("fortaleza", "Fortaleza", "CE"),
        # Goiás
        Club("goias", "Goiás", "GO"),
        Club("atleticogoianiense", "Atlético Goianiense", "GO"),
        Club("vilanova", "Vila Nova", "GO"),
        # Alagoas
        Club("crb", "CRB", "AL"),
        Club("csa", "CSA", "AL"),
        # Pará
        Club("paysandu", "Paysandu", "PA"),
        Club("remo", "Remo", "PA"),
        # Santa Catarina
        Club("avai", "Avaí", "SC"),
        Club("chapecoense", "Chapecoense", "SC"),
        Club("figueirense", "Figueirense", "SC"),
        Club("joinville", "Joinville", "SC"),
        # Mato Grosso
        Club("cuiaba", "Cuiabá", "MT"),
        # Distrito Federal
        Club("brasiliense", "Brasiliense", "DF"),
        # Namesake clubs that must stay distinct from their famous cousins
        Club("americarn", "América-RN", "RN"),
        Club("botafogosp", "Botafogo-SP", "SP"),
        Club("botafogopb", "Botafogo-PB", "PB"),
    ]
}

# Aliases map the *compacted full raw name* (suffixes/parentheses included)
# to a canonical key.  They are only needed where the generic base-stripping
# rules cannot succeed: bare short names ("Vasco"), full legal names from
# the FIFA file, spelling drift ("Athletico" vs "Atlético"), state-abbreviated
# giants ("Atletico-MG") and Libertadores clubs carrying country codes.
ALIASES: dict[str, str] = {
    # Bare / short forms
    "vasco": "vascodagama",
    "sport": "sportrecife",
    "bragantino": "redbullbragantino",
    "bragantinosp": "redbullbragantino",
    # FIFA-style legal names
    "sportclubcorinthianspaulista": "corinthians",
    "sportclubdorecife": "sportrecife",
    "cearasportingclub": "ceara",
    "americafcminasgerais": "americamineiro",
    # BR-Football naming quirks
    "ecjuventude": "juventude",
    "clubedoremo": "remo",
    "nauticocapibaribe": "nautico",
    "fortalezaec": "fortaleza",
    "fortalezafc": "fortaleza",
    "santacruzfc": "santacruz",
    "vitoriaec": "vitoria",
    "novorizontino": "gremionovorizontino",
    "novorizontinosp": "gremionovorizontino",
    # Athletico Paranaense spellings (2019 rebrand kept both spellings)
    "athletico": "atleticoparanaense",
    "athleticopr": "atleticoparanaense",
    "athleticoparanaense": "atleticoparanaense",
    "athleticoparanaensepr": "atleticoparanaense",
    "atleticopr": "atleticoparanaense",
    "atleticoparanaensepr": "atleticoparanaense",
    # Atlético Mineiro / Goianiense abbreviated forms
    "atleticomg": "atleticomineiro",
    "atleticogo": "atleticogoianiense",
    # América Mineiro
    "americamg": "americamineiro",
    # Dotted acronym clubs (Copa do Brasil file)
    "crbal": "crb",
    "csaal": "csa",
    # Libertadores clubs written with country qualifiers; kept distinct
    # from any Brazilian namesake (e.g. Paraguay's Guaraní vs Guarani-SP).
    "nacionaluru": "nacionaluru",
    "nacionalpar": "nacionalpar",
    "guaranipar": "guaranipar",
    "barcelonaequ": "barcelonaequ",
    "delfinequ": "delfinequ",
    "riverplateuru": "riverplateuru",
    "olimpiapar": "olimpiapar",
    "libertadpar": "libertadpar",
    "universitarioper": "universitarioper",
    "trujillanosven": "trujillanosven",
}

# Display names for the self-mapped foreign clubs above (nice output).
_FOREIGN_DISPLAY = {
    "nacionaluru": "Nacional (URU)",
    "nacionalpar": "Nacional (PAR)",
    "guaranipar": "Guaraní (PAR)",
    "barcelonaequ": "Barcelona (EQU)",
    "delfinequ": "Delfín (EQU)",
    "riverplateuru": "River Plate (URU)",
    "olimpiapar": "Olimpia (PAR)",
    "libertadpar": "Libertad (PAR)",
    "universitarioper": "Universitario (PER)",
    "trujillanosven": "Trujillanos (VEN)",
}


# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------


def team_key(raw: str) -> str:
    """Fold a raw team name to its canonical key."""
    name = (raw or "").strip()
    if not name:
        return ""
    full = compact(name)
    if full in ALIASES:
        return ALIASES[full]
    base, state = _split_base(name)
    base_key = compact(base)
    if base_key in CLUBS:
        club = CLUBS[base_key]
        if state is None or state.upper() == (club.state or ""):
            return club.key
        # Same nickname, different state: a namesake club.
        return base_key + state.lower()
    if base_key in ALIASES:
        canonical = ALIASES[base_key]
        club = CLUBS.get(canonical)
        if club and state and club.state and state.upper() != club.state:
            return base_key + state.lower()
        return canonical
    if state:
        return base_key + state.lower()
    return base_key or full


def team_state(raw: str) -> Optional[str]:
    """Extract the trailing state/country code from a raw name, if any."""
    _, state = _split_base((raw or "").strip())
    return state


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class TeamInfo:
    """Everything known about one resolved team key."""

    key: str
    display: str
    variants: list[str] = field(default_factory=list)
    states: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    match_count: int = 0

    def add_variant(self, raw: str, source: str = "") -> None:
        if raw not in self.variants:
            self.variants.append(raw)
        if source:
            self.sources.add(source)
        state = team_state(raw)
        if state:
            self.states.add(state.upper())


def build_registry(raw_names: Iterable[tuple[str, str]]) -> TeamRegistry:
    """Build a registry from ``(raw_name, source_label)`` pairs."""
    registry = TeamRegistry()
    for raw, source in raw_names:
        if not raw or not raw.strip():
            continue
        key = team_key(raw)
        if not key:
            continue
        info = registry.teams.setdefault(key, TeamInfo(key=key, display=key))
        info.add_variant(raw.strip(), source)
    # Choose the nicest display name for every key.
    for key, info in registry.teams.items():
        if key in CLUBS:
            info.display = CLUBS[key].display
        elif key in _FOREIGN_DISPLAY:
            info.display = _FOREIGN_DISPLAY[key]
        else:
            info.display = _pick_display(info.variants)
    return registry


def _pick_display(variants: list[str]) -> str:
    """Pick the prettiest raw variant for an uncurated team."""

    def score(name: str) -> tuple[int, int, int]:
        base, _ = _split_base(name)
        base = base.strip() or name.strip()
        has_accent = any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFKD", base))
        # prefer: accented forms, then shorter (suffix-stripped) names
        return (1 if has_accent else 0, -len(base), -len(name))

    return max(variants, key=score) if variants else ""


class TeamRegistry:
    """Lookup of canonical team keys with forgiving matching."""

    def __init__(self) -> None:
        self.teams: dict[str, TeamInfo] = {}

    def __contains__(self, key: str) -> bool:
        return key in self.teams

    def __len__(self) -> int:
        return len(self.teams)

    def get(self, key: str) -> Optional[TeamInfo]:
        return self.teams.get(key)

    def all(self) -> list[TeamInfo]:
        return sorted(self.teams.values(), key=lambda t: (-t.match_count, t.display))

    def find(self, query: str) -> list[TeamInfo]:
        """Return candidate teams for a user query, best matches first.

        Matching is exact-key first, then substring containment, then
        fuzzy similarity, so "palmeirass", "Sport Club Corinthians
        Paulista" and "atletico-mg" all resolve.
        """
        qc = compact(query)
        if not qc:
            return []
        exact: list[TeamInfo] = []
        starts: list[TeamInfo] = []
        contains: list[TeamInfo] = []
        fuzzy: list[tuple[float, TeamInfo]] = []
        for info in self.teams.values():
            key = info.key
            display_c = compact(info.display)
            variants_c = [compact(v) for v in info.variants]
            names = [key, display_c, *variants_c]
            if qc in (key, display_c) or qc in variants_c:
                exact.append(info)
                continue
            for n in names:
                if n.startswith(qc):
                    starts.append(info)
                    break
            else:
                for n in names:
                    if qc in n or n in qc:
                        contains.append(info)
                        break
                else:
                    best = max(
                        (SequenceMatcher(None, qc, n).ratio() for n in names),
                        default=0.0,
                    )
                    if best >= 0.75:
                        fuzzy.append((best, info))
        seen: set[str] = set()
        result: list[TeamInfo] = []
        for info in exact + starts + contains:
            if info.key not in seen:
                seen.add(info.key)
                result.append(info)
        for ratio, info in sorted(fuzzy, key=lambda p: -p[0]):
            if info.key not in seen:
                seen.add(info.key)
                result.append(info)
        # Prefer well-known teams when several candidates tie.
        result.sort(key=lambda i: (-i.match_count, i.display))
        return result[:12]

    def match_counts(self, counter: Counter) -> None:
        """Attach match counts (used to rank candidates)."""
        for key, count in counter.items():
            if key in self.teams:
                self.teams[key].match_count = count
