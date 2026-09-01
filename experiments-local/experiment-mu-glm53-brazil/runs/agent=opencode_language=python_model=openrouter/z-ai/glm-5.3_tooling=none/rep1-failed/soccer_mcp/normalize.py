"""Team-name normalization and team registry for Brazilian soccer data.

CONTEXT
-------
The six Kaggle CSV files use wildly different conventions for the same
clubs ("Palmeiras-SP", "Palmeiras", "Red Bull Bragantino-SP", "Atletico
Mineiro", "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", ...).
This module turns every raw spelling into a stable *entity key*
``"<base>|<REGION>"`` (e.g. ``"atletico|MG"``) so that matches, players and
statistics can be joined across files.

Layers of normalization
    1. unicode folding  - accents stripped (Grêmio -> gremio)
    2. suffix parsing   - trailing "-SP" / " - SP" / " SP" Brazilian state
                          codes and "-PAR" / "(URU)" country codes become
                          the entity *region*
    3. alias table      - full club names ("Atletico Mineiro") and era
                          renames ("Athletico Paranaense" 2019+ ==
                          "Atletico-PR") map onto canonical keys
    4. stateless merge  - a name without a region ("Grêmio") merges into
                          the most prominent region entity with the same
                          base ("Grêmio-RS")
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: 27 Brazilian federative-unit abbreviations (incl. DF).
BRAZILIAN_STATES = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

#: South-American (plus Mexico) country codes used as team suffixes in the
#: Libertadores dataset, e.g. "Barcelona-EQU", "Nacional (URU)".
COUNTRY_CODES = frozenset("ARG BOL CHI COL ECU EQU PAR PER URU VEN MEX".split())

# Patterns for a trailing state/country suffix:
#   "Palmeiras-SP", "Palmeiras - SP", "Palmeiras SP", "Barcelona-EQU",
#   "América - MG" ...
_SUFFIX_RE = re.compile(r"(?:\s*[-–]\s*|\s+)([A-Za-z]{2,3})$")
# Trailing parenthesized country, e.g. "Nacional (URU)".
_PAREN_COUNTRY_RE = re.compile(r"\s*\(([A-Za-z]{2,3})\)\s*$")

#: Alias table applied to the *collapsed* full name (accent-stripped,
#: lower-cased, punctuation removed) AND to the parsed base name.
#: Maps variant spellings onto their canonical ``(base, region)`` key.
BASE_ALIASES: dict[str, tuple[str, str | None]] = {
    # -- Atlético Mineiro -------------------------------------------------
    "atletico mineiro": ("atletico", "MG"),
    "clube atletico mineiro": ("atletico", "MG"),
    "gallo csa": ("csa", "AL"),  # defensive; not expected in data
    # -- Athletico Paranaense (renamed from Atlético in 2019) --------------
    "atletico paranaense": ("atletico", "PR"),
    "athletico paranaense": ("atletico", "PR"),
    "athletico": ("atletico", "PR"),
    "clube atletico paranaense": ("atletico", "PR"),
    # -- Atlético Goianiense -----------------------------------------------
    "atletico goianiense": ("atletico", "GO"),
    "atlético goianiense": ("atletico", "GO"),
    # -- Paraná Clube (NOT Athletico!) --------------------------------------
    "ca parana": ("parana", "PR"),
    # -- Sport Recife --------------------------------------------------------
    "sport recife": ("sport", "PE"),
    "sport club do recife": ("sport", "PE"),
    # -- Vasco ---------------------------------------------------------------
    "vasco da gama": ("vasco", "RJ"),
    "cr vasco da gama": ("vasco", "RJ"),
    # -- América (MG / RN) ---------------------------------------------------
    "america fc minas gerais": ("america", "MG"),
    "america fc natal": ("america", "RN"),
    "america de natal": ("america", "RN"),
    # -- Vitória-BA ----------------------------------------------------------
    "vitoria ec": ("vitoria", "BA"),
    "ec vitoria": ("vitoria", "BA"),
    # -- Bahia ----------------------------------------------------------------
    "ec bahia": ("bahia", "BA"),
    # -- Fortaleza -------------------------------------------------------------
    "fortaleza ec": ("fortaleza", "CE"),
    "fortaleza fc": ("fortaleza", "CE"),
    # -- Macaé -----------------------------------------------------------------
    "macae esporte": ("macae", "RJ"),
    # -- Portuguesa --------------------------------------------------------------
    "portuguesa desportos": ("portuguesa", "SP"),
    # -- Náutico ------------------------------------------------------------------
    "nautico capibaribe": ("nautico", "PE"),
    # -- Grêmio Barueri / Grêmio Prudente (same club, renamed 2010) ---------------
    "gremio barueri": ("barueri", "SP"),
    "gremio prudente": ("barueri", "SP"),
    # -- Red Bull Bragantino -------------------------------------------------------
    "red bull bragantino": ("bragantino", "SP"),
    "ca bragantino": ("bragantino", "SP"),
    # -- Copa do Brasil long names ---------------------------------------------------
    "boavista sport club antigo esporte clube barreira": ("boavista", "RJ"),
    "operario ferroviario esporte c": ("operario", "PR"),
    "esportivo bento goncalves": ("esportivo", "RS"),
    # -- FIFA full club names ---------------------------------------------------------
    "ceara sporting club": ("ceara", "CE"),
    "santa cruz fc": ("santa cruz", "PE"),
    "ec internacional": ("internacional", "SC"),
    "inter de lages": ("internacional", "SC"),
    # -- BR-Football prefix/suffix variants (same clubs, different spellings) ---------
    "ec juventude": ("juventude", "RS"),
    "madureira ec": ("madureira", "RJ"),
    "macae esporte fc": ("macae", "RJ"),
    "floresta ec": ("floresta", None),
    "cordino ec": ("cordino", None),
    "nova mutum ec": ("nova mutum", None),
    "tocantinopolis ec": ("tocantinopolis", None),
    "campinense clube": ("campinense", None),
    "moto clube": ("moto club de sao luis", None),
    "duque de caxias fc": ("duque de caxias", "RJ"),
    "se gama": ("gama", None),
    "clube do remo": ("remo", None),
    "sao jose poa": ("sao jose", "RS"),
    "villa nova": ("vila nova", None),
    "retro fc brasil": ("retro", None),
    "cs alagoano": ("csa", "AL"),
    "ad confianca": ("confianca", None),
    "novorizontino": ("gremio novorizontino", None),
}

#: Curated display names for well-known entities (keyed by ``(base, region)``).
_DISPLAY_NAMES: dict[tuple[str, str | None], str] = {
    ("flamengo", "RJ"): "Flamengo",
    ("fluminense", "RJ"): "Fluminense",
    ("botafogo", "RJ"): "Botafogo",
    ("vasco", "RJ"): "Vasco da Gama",
    ("sao paulo", "SP"): "São Paulo",
    ("corinthians", "SP"): "Corinthians",
    ("palmeiras", "SP"): "Palmeiras",
    ("santos", "SP"): "Santos",
    ("gremio", "RS"): "Grêmio",
    ("internacional", "RS"): "Internacional",
    ("cruzeiro", "MG"): "Cruzeiro",
    ("atletico", "MG"): "Atlético-MG",
    ("atletico", "PR"): "Athletico-PR",
    ("atletico", "GO"): "Atlético-GO",
    ("bahia", "BA"): "Bahia",
    ("vitoria", "BA"): "Vitória",
    ("sport", "PE"): "Sport",
    ("nautico", "PE"): "Náutico",
    ("santa cruz", "PE"): "Santa Cruz",
    ("ceara", "CE"): "Ceará",
    ("fortaleza", "CE"): "Fortaleza",
    ("america", "MG"): "América-MG",
    ("america", "RN"): "América-RN",
    ("chapecoense", "SC"): "Chapecoense",
    ("avai", "SC"): "Avaí",
    ("figueirense", "SC"): "Figueirense",
    ("criciuma", "SC"): "Criciúma",
    ("coritiba", "PR"): "Coritiba",
    ("parana", "PR"): "Paraná",
    ("goias", "GO"): "Goiás",
    ("cuiaba", "MT"): "Cuiabá",
    ("juventude", "RS"): "Juventude",
    ("portuguesa", "SP"): "Portuguesa",
    ("ponte preta", "SP"): "Ponte Preta",
    ("bragantino", "SP"): "Red Bull Bragantino",
    ("csa", "AL"): "CSA",
    ("barueri", "SP"): "Grêmio Prudente",
    ("botafogo", "PB"): "Botafogo-PB",
    ("botafogo", "SP"): "Botafogo-SP",
    ("bahia de feira", "BA"): "Bahia de Feira",
    ("fluminense de feira", "BA"): "Fluminense de Feira",
    ("guarani", "SP"): "Guarani",
    ("vitoria da conquista", "BA"): "Vitória da Conquista",
    ("ipatinga", None): "Ipatinga",
    ("joinville", None): "Joinville",
    ("brasiliense", None): "Brasiliense",
}

# --------------------------------------------------------------------------
# Core text helpers
# --------------------------------------------------------------------------


def strip_accents(text: str) -> str:
    """Return *text* with accented characters folded to ASCII (Grêmio -> Gremio)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def collapse(text: str) -> str:
    """Accent-fold, lowercase and collapse all punctuation/spaces.

    Periods are removed outright so dotted abbreviations equal their plain
    forms ("A.s.a." -> "asa" == "ASA").  Other punctuation becomes spaces::

        collapse("São Paulo FC (Brasil)") -> "sao paulo fc brasil"
    """
    folded = strip_accents(text).lower().replace(".", "")
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return folded.strip()


def _squash(text: str) -> str:
    """Space-free form used for tolerant substring matching ("saopaulo")."""
    return collapse(text).replace(" ", "")


# --------------------------------------------------------------------------
# Name parsing
# --------------------------------------------------------------------------


def parse_team_name(raw: str) -> tuple[str, str | None]:
    """Split a raw team name into ``(base, region)``.

    The region is a Brazilian state code ("MG"), a country code ("URU") or
    ``None``.  Suffix and parenthesized markers are removed from the base::

        parse_team_name("Palmeiras-SP")     -> ("palmeiras", "SP")
        parse_team_name("América - MG")     -> ("america", "MG")
        parse_team_name("Nacional (URU)")   -> ("nacional", "URU")
        parse_team_name("Botafogo SP")      -> ("botafogo", "SP")
        parse_team_name("Atletico Mineiro") -> ("atletico mineiro", None)
    """
    name = raw.strip()
    region: str | None = None

    m = _PAREN_COUNTRY_RE.search(name)
    if m and m.group(1).upper() in COUNTRY_CODES:
        region = m.group(1).upper()
        name = name[: m.start()].strip()

    m = _SUFFIX_RE.search(name)
    if m:
        code = m.group(1).upper()
        if len(code) == 2 and code in BRAZILIAN_STATES:
            region = code
            name = name[: m.start()].strip()
        elif len(code) == 3 and code in COUNTRY_CODES:
            region = code
            name = name[: m.start()].strip()

    base = collapse(name)
    # Re-apply aliases on the parsed base (e.g. "Vasco da Gama - RJ" ->
    # base "vasco da gama" -> canonical ("vasco", "RJ")).
    if base in BASE_ALIASES:
        base, alias_region = BASE_ALIASES[base]
        if region is None or region == alias_region:
            region = alias_region
    return base, region


def canonical_key(raw: str) -> tuple[str, str | None]:
    """Full normalization of a raw team name to its ``(base, region)`` key.

    Applies whole-string aliases first ("Atletico Mineiro" would otherwise
    keep its own base), then suffix parsing.
    """
    collapsed = collapse(raw)
    if collapsed in BASE_ALIASES:
        return BASE_ALIASES[collapsed]
    return parse_team_name(raw)


def _default_display(base: str, region: str | None, grouped: dict) -> str:
    """Human-readable fallback: title-cased base, region only when ambiguous."""
    title = base.title()
    if region is None:
        return title
    ambiguous = sum(1 for (b, _r) in grouped if b == base) > 1
    return f"{title}-{region}" if ambiguous else title


# --------------------------------------------------------------------------
# Team registry
# --------------------------------------------------------------------------


@dataclass
class Team:
    """One real-world club, e.g. Clube de Regatas do Flamengo."""

    base: str
    region: str | None
    display: str = ""
    raw_names: set[str] = field(default_factory=set)
    match_count: int = 0
    player_count: int = 0

    @property
    def key(self) -> str:
        return f"{self.base}|{self.region}" if self.region else f"{self.base}|"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.display


class TeamRegistry:
    """Registry of every team entity encountered in the datasets.

    Built in two phases:

    1. :meth:`add_name` feeds raw names (with the number of occurrences)
       from every match file; :meth:`finalize` groups them into entities,
       merging stateless spellings into the most prominent region variant.
    2. :meth:`resolve` answers user queries, returning candidate teams
       ordered by prominence (match count).
    """

    def __init__(self) -> None:
        self._raw: dict[str, int] = {}  # raw name -> occurrence count
        self._teams: dict[tuple[str, str | None], Team] = {}
        self._finalized = False

    # -- phase 1 ------------------------------------------------------------

    def add_name(self, raw: str, count: int = 1) -> None:
        if self._finalized:  # pragma: no cover - defensive
            raise RuntimeError("registry already finalized")
        raw = raw.strip()
        if raw:
            self._raw[raw] = self._raw.get(raw, 0) + count

    # -- phase 2 ------------------------------------------------------------

    def finalize(self) -> "TeamRegistry":
        """Group raw names into entities and compute display names."""
        if self._finalized:
            return self

        # (base, region) -> {raw: count}
        grouped: dict[tuple[str, str | None], dict[str, int]] = {}
        for raw, count in self._raw.items():
            base, region = canonical_key(raw)
            grouped.setdefault((base, region), {})[raw] = count

        # Stateless merge: fold every "(base, None)" group into the most
        # prominent regional entity with the same base.
        stateless = [k for k in grouped if k[1] is None]
        for base, _none in stateless:
            regions = [(k, c) for k, c in grouped.items() if k[0] == base and k[1] is not None]
            if regions:
                best_key = max(regions, key=lambda kv: sum(kv[1].values()))[0]
                grouped[best_key].update(grouped.pop((base, None)))

        for (base, region), raws in grouped.items():
            team = Team(base=base, region=region)
            team.raw_names = set(raws)
            team.match_count = sum(raws.values())
            team.display = _DISPLAY_NAMES.get((base, region)) or _default_display(base, region, grouped)
            self._teams[(base, region)] = team

        self._finalized = True
        return self

    # -- lookups -------------------------------------------------------------

    @property
    def teams(self) -> list[Team]:
        return sorted(self._teams.values(), key=lambda t: (-t.match_count, t.key))

    def teams_by_key(self) -> dict[str, Team]:
        """Entity key -> Team (single lookup, no sorting)."""
        if not hasattr(self, "_by_key") or self._by_key is None:
            self._by_key = {t.key: t for t in self._teams.values()}
        return self._by_key

    def get(self, base: str, region: str | None) -> Team | None:
        return self._teams.get((base, region))

    def add_players(self, raw_club: str, count: int) -> None:
        """Attribute FIFA squad members to a registered team entity.

        Uses strict (non-substring) resolution so that e.g. the FIFA club
        "Inter" is *not* mistaken for Internacional-RS.
        """
        team = self.resolve_exact(raw_club)
        if team:
            team.player_count += count

    def resolve_exact(self, query: str) -> Team | None:
        """Strict resolution: aliases and exact base/region matches only."""
        if not self._finalized:
            self.finalize()
        query = query.strip()
        if not query:
            return None

        collapsed = collapse(query)
        if collapsed in BASE_ALIASES:
            base, region = BASE_ALIASES[collapsed]
            team = self._teams.get((base, region))
            if team:
                return team

        base, region = parse_team_name(query)
        if region is not None:
            team = self._teams.get((base, region))
            if team:
                return team
        if region is None and base in BASE_ALIASES:
            alias_base, alias_region = BASE_ALIASES[base]
            return self._teams.get((alias_base, alias_region))

        same_base = [t for t in self._teams.values() if t.base == base]
        if region is not None:
            same_base = [t for t in same_base if t.region == region] or same_base
        if len(same_base) == 1:
            return same_base[0]
        if same_base:
            return max(same_base, key=lambda t: t.match_count)
        return None

    def resolve(self, query: str) -> list[Team]:
        """Resolve a user-supplied team name to entities, most prominent first.

        Handles accented/unaccented input, state suffixes, full club names
        and fuzzy substrings ("inter" -> Internacional-RS, Internacional-SC).
        """
        if not self._finalized:
            self.finalize()
        query = query.strip()
        if not query:
            return []

        # 1. Whole-string alias ("atletico mineiro", "red bull bragantino").
        collapsed = collapse(query)
        if collapsed in BASE_ALIASES:
            base, region = BASE_ALIASES[collapsed]
            team = self._teams.get((base, region))
            if team:
                return [team]

        # 2. Exact parse incl. state suffix ("palmeiras-sp").
        base, region = parse_team_name(query)
        if region is not None:
            team = self._teams.get((base, region))
            if team:
                return [team]
        # Base alias may have rewritten (base, region) already; also try the
        # alias target when the query carried no explicit region.
        if region is None and base in BASE_ALIASES:
            alias_base, alias_region = BASE_ALIASES[base]
            team = self._teams.get((alias_base, alias_region))
            if team:
                return [team]

        # 3. Unique entity sharing the base ("palmeiras" -> Palmeiras-SP).
        same_base = [t for t in self._teams.values() if t.base == base]
        if region is not None:
            regional = [t for t in same_base if t.region == region]
            if regional:
                same_base = regional
        if same_base:
            return sorted(same_base, key=lambda t: (-t.match_count, t.key))

        # 4. Tolerant substring match against bases and raw spellings
        #    ("saopaulo", "recife", "inter").
        q_squashed = _squash(query)
        hits: list[Team] = []
        for team in self._teams.values():
            if q_squashed and q_squashed in _squash(team.base):
                hits.append(team)
                continue
            if any(q_squashed in _squash(raw) for raw in team.raw_names):
                hits.append(team)
        if hits:
            return sorted(hits, key=lambda t: (-t.match_count, t.key))

        return []

    def display_name(self, base: str, region: str | None) -> str:
        """Human-readable display name for an entity key."""
        team = self._teams.get((base, region))
        if team is not None:
            return team.display
        return base.title()

    def search(self, query: str, limit: int = 25) -> list[Team]:
        """Alias of :meth:`resolve` with a limit, for listing purposes."""
        return self.resolve(query)[:limit]


def build_registry(names: Iterable[tuple[str, int]]) -> TeamRegistry:
    """Convenience: build a finalized registry from ``(raw_name, count)`` pairs."""
    registry = TeamRegistry()
    for name, count in names:
        registry.add_name(name, count)
    return registry.finalize()
