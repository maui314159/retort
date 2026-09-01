"""Team-name and date normalization for Brazilian soccer datasets.

The six source CSV files spell the same club in many ways:
  "Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Atletico Mineiro",
  "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Botafogo RJ".

This module turns every raw spelling into a stable canonical team key
("palmeiras-sp", "atletico-mg", ...) plus a pretty display name, and can
resolve user queries ("Athletico", "Flamengo", "atletico-pr") to keys.

It also parses the three date formats found in the datasets:
  "2012-05-19 18:30:00" (ISO + time), "2023-09-24" (ISO), "29/03/2003" (BR).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Basic folding
# ---------------------------------------------------------------------------

# "Athletico-PR" (post-2019 spelling) and "Atlético-PR" are the same club.
_ORTHOGRAPHIC_FIXES = (("athletico", "atletico"),)


def fold(value: str) -> str:
    """Fold a name to a canonical comparison key.

    Accent-insensitive, case-insensitive, punctuation-insensitive, and
    tolerant of the Athletico/Atlético spelling change.
    """
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    for old, new in _ORTHOGRAPHIC_FIXES:
        text = text.replace(old, new)
    return re.sub(r"[^a-z0-9]", "", text)


# ---------------------------------------------------------------------------
# Suffix detection (states / countries)
# ---------------------------------------------------------------------------

BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Parenthetical or dashed country tags used by the Libertadores file.
COUNTRY_CODES = {
    "ARG", "BOL", "CHI", "COL", "ECU", "EQU", "PAR", "PER", "URU", "VEN",
    "MEX", "USA", "CRC", "GUA", "HON", "SAL", "PAN", "JAM",
}

_SUFFIX_PATTERNS = (
    re.compile(r"\s*-\s*([A-Z]{2})\s*$"),   # "América - MG" / "América-MG"
    re.compile(r"\s+([A-Z]{2})\s*$"),       # "Botafogo RJ" (BR-Football file)
)
_COUNTRY_PATTERNS = (
    re.compile(r"\s*-\s*([A-Z]{3})\s*$"),   # "Barcelona-EQU"
    re.compile(r"\s*\(\s*([A-Z]{2,3})\s*\)\s*$"),  # "Nacional (URU)" / "River (PI)"
)
_ANTIGO_RE = re.compile(r"\s*\(antigo[^)]*\)\s*", re.IGNORECASE)


def has_diacritics(text: str) -> bool:
    """True when the text carries accents (ç, ã, é, ...) - precomposed
    characters need NFD decomposition before unicodedata.combining sees
    their combining marks."""
    return any(
        unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", text)
    )

# Decorative tokens that carry no identity ("Fortaleza FC" -> "fortaleza").
_DECORATIVE_TOKENS = {"fc", "ec", "sc", "ac"}


@dataclass
class ParsedName:
    """A raw team name split into identity components."""

    base: str            # folded base, e.g. "atleticomg"... no: "atletico"
    state: str | None    # "MG" if the name carried a state suffix
    country: str | None  # "URU" for "(URU)"/"-EQU" style tags
    pretty: str          # human-readable base, e.g. "Atlético"


def _strip_decorative(base_pretty: str) -> str:
    tokens = base_pretty.split()
    while tokens and tokens[-1].lower() in _DECORATIVE_TOKENS:
        tokens.pop()
    while tokens and tokens[0].lower() in _DECORATIVE_TOKENS:
        tokens.pop(0)
    return " ".join(tokens) if tokens else base_pretty


def parse_name(raw: str) -> ParsedName:
    """Split a raw team name into (base, state, country, pretty base)."""
    name = (raw or "").strip()
    name = _ANTIGO_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()

    state: str | None = None
    country: str | None = None

    # A 2-letter tag can be a state (RJ) or a country (URU is 3 letters, but
    # "(PI)" is a state), so check states first, then country codes.
    for pattern in _SUFFIX_PATTERNS:
        match = pattern.search(name)
        if match and match.group(1) in BRAZILIAN_STATES:
            state = match.group(1)
            name = name[: match.start()].strip()
            break
    if state is None:
        for pattern in _COUNTRY_PATTERNS:
            match = pattern.search(name)
            if match:
                tag = match.group(1)
                if tag in BRAZILIAN_STATES and pattern is _COUNTRY_PATTERNS[1]:
                    state = tag          # "River (PI)"
                elif tag in COUNTRY_CODES:
                    country = tag        # "Nacional (URU)"
                else:
                    continue
                name = name[: match.start()].strip()
                break

    pretty = _strip_decorative(name) or (raw or "").strip()
    stripped = _strip_decorative(name)
    base = fold(stripped) if stripped else fold(name)
    return ParsedName(base=base, state=state, country=country, pretty=pretty)


# ---------------------------------------------------------------------------
# Curated aliases: full historical names -> canonical suffixed keys
# ---------------------------------------------------------------------------

ALIASES: dict[str, str] = {
    # fold(full name) -> canonical key
    fold("Atlético Mineiro"): "atleticomg",
    fold("Atletico Mineiro"): "atleticomg",
    fold("Clube Atlético Mineiro"): "atleticomg",
    fold("Atlético Paranaense"): "atleticopr",
    fold("Athletico Paranaense"): "atleticopr",
    fold("Atlético-PR"): "atleticopr",
    fold("Atlético Goianiense"): "atleticogo",
    fold("Atletico Goianiense"): "atleticogo",
    fold("Vasco"): "vascodagamarj",
    fold("Vasco da Gama"): "vascodagamarj",
    fold("Sport Club do Recife"): "sportpe",
    fold("Sport Recife"): "sportpe",
    fold("Ceará Sporting Club"): "cearace",
    fold("América FC (Minas Gerais)"): "americamg",
    fold("América Mineiro"): "americamg",
    fold("São Paulo FC"): "saopaulosp",
    fold("Grêmio Foot-Ball Porto Alegrense"): "gremiors",
    fold("Sport Club Corinthians Paulista"): "corinthianssp",
    fold("Red Bull Bragantino"): "redbullbragantinosp",
    # Full historical names used by the extended-stats file for clubs that
    # other files spell in short form.
    fold("Náutico Capibaribe"): "nauticope",
    fold("AD Confiança"): "confiancase",
    fold("Clube do Remo"): "remopa",
    fold("Portuguesa de Desportos"): "portuguesasp",
    fold("AE Altos"): "altospi",
    fold("Atlético Acreano"): "atleticoac",
    fold("Campinense Clube"): "campinensepb",
    fold("Moto Club de São Luís"): "motoclubma",
    fold("Moto Clube"): "motoclubma",
    fold("Grêmio Novorizontino"): "novorizontinosp",
}

# Suffix-aware aliases for clubs whose base name changed over time while
# another club kept the old name: (folded base, state) -> canonical key.
SUFFIX_ALIASES: dict[tuple[str, str], str] = {
    # CA Bragantino (SP) was renamed Red Bull Bragantino in 2019; the tiny
    # Pará club Bragantino-PA must stay separate.
    ("bragantino", "sp"): "redbullbragantinosp",
    # The historical file writes bare "Vasco" + RJ state column; the other
    # files write the full "Vasco da Gama-RJ".
    ("vasco", "rj"): "vascodagamarj",
    # Both the historical file (home rows) and the extended-stats file
    # mislabel Vitória (Salvador, Bahia) with state ES instead of BA.
    ("vitoria", "es"): "vitoriaba",
    # The cup file writes full names for clubs other files spell shortly.
    ("atleticomineiro", "mg"): "atleticomg",
    ("atleticoparanaense", "pr"): "atleticopr",
    ("operarioferroviarioesportec", "pr"): "operariopr",
}


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y")


def parse_date(value: str | None) -> date | None:
    """Parse the date formats used across the datasets; None if unknown."""
    if not value:
        return None
    text = value.strip()
    if text.upper() in {"NA", "N/A", "-", ""}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(value: str | None) -> str | None:
    """Extract a "HH:MM" kick-off time from a datetime or time column."""
    if not value:
        return None
    text = value.strip()
    if text.upper() in {"NA", "N/A", "-", ""}:
        return None
    match = re.match(r"(\d{2}:\d{2})", text)
    return match.group(1) if match else None


def to_int(value: str | None) -> int | None:
    """Best-effort integer parse; NA/'-'/'' become None."""
    if value is None:
        return None
    text = str(value).strip()
    if text.upper() in {"NA", "N/A", "-", ""}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Team registry
# ---------------------------------------------------------------------------


@dataclass
class Team:
    """A canonical team entity in the knowledge graph."""

    key: str                  # e.g. "atletico-mg", "bocajuniors", "nacional-uru"
    base: str                 # folded base, e.g. "atletico"
    display: str              # pretty name shown to users, e.g. "Atlético-MG"
    state: str | None         # Brazilian state code, if known
    country: str | None       # foreign country tag, if known
    appearances: int = 0      # match participations (suffixed sources count)
    _variants: dict[str, int] = field(default_factory=dict)

    def note_variant(self, raw: str) -> None:
        self._variants[raw] = self._variants.get(raw, 0) + 1

    def refresh_display(self) -> None:
        """Pick the prettiest variant: prefer accented, suffixed spellings."""
        if not self._variants:
            return
        def score(variant: str) -> tuple[int, int, int]:
            has_accent = has_diacritics(variant)
            has_state = self.state is not None and self.state.lower() in fold(variant)[-2:]
            length = len(variant)
            return (1 if has_accent else 0, 1 if has_state else 0, -length)
        self.display = max(self._variants, key=score)


@dataclass
class TeamResolution:
    """Result of resolving a user-supplied team name."""

    key: str | None                 # single resolved key, if any
    matched: bool                   # True when a single key was resolved
    ambiguous: list[Team] = field(default_factory=list)   # candidates to disambiguate
    suggestions: list[str] = field(default_factory=list)  # close spellings


class TeamRegistry:
    """Registry of canonical team identities built from every source file."""

    DOMINANCE = 0.75  # bare base auto-resolves when one state has >=75% share

    def __init__(self) -> None:
        self.teams: dict[str, Team] = {}
        self._by_base: dict[str, set[str]] = {}
        self._alias_keys: dict[str, str] = {}

    # -- registration ------------------------------------------------------

    def register(
        self,
        raw: str,
        *,
        state_hint: str | None = None,
        count_appearance: bool = True,
    ) -> str:
        """Register a raw name and return its canonical key.

        ``state_hint`` lets sources with a separate state column (the
        historical Brasileirão file) supply identity for stateless names.
        ``count_appearance`` is False for the unsuffixed extended-stats file
        so that its duplicate fixtures do not skew the dominance ranking.

        Stateless names resolve, in order: curated alias -> unique base ->
        dominant state share (e.g. bare "Flamengo" is Flamengo-RJ) -> new
        standalone entity.
        """
        parsed = parse_name(raw)
        state = parsed.state or (
            state_hint if state_hint in BRAZILIAN_STATES else None
        )
        suffix = (state or parsed.country) if (state or parsed.country) else None
        key: str | None = None

        if suffix:
            key = f"{parsed.base}{suffix.lower()}"
            if state:
                # Clubs renamed while another club kept the old base name.
                key = SUFFIX_ALIASES.get((parsed.base, state.lower()), key)
        else:
            alias_target = ALIASES.get(parsed.base)
            if alias_target and alias_target in self.teams:
                key = alias_target
            elif not parsed.base:
                key = fold(raw)
            else:
                key = self._dominant(self._by_base.get(parsed.base, set()))
                if key is None:
                    # unique candidate, or genuinely ambiguous base
                    candidates = self._by_base.get(parsed.base, set())
                    key = next(iter(candidates)) if len(candidates) == 1 else parsed.base

        team = self.teams.get(key)
        if team is None:
            team = Team(
                key=key,
                base=parsed.base,
                display=parsed.pretty,
                state=state,
                country=parsed.country,
            )
            self.teams[key] = team
        # Track every base spelling that points at this entity, even when
        # the entity was first created through an alias or another source.
        if parsed.base:
            self._by_base.setdefault(parsed.base, set()).add(key)

        if state and not team.state:
            team.state = state
        team.note_variant(raw if raw.strip() else parsed.pretty)
        team.refresh_display()
        if count_appearance:
            team.appearances += 1
        return key

    def keys_for_base(self, base: str) -> list[str]:
        return sorted(self._by_base.get(base, ()))

    def _dominant(self, candidates: set[str]) -> str | None:
        """The candidate holding >= DOMINANCE of the bucket's appearances."""
        known = {k for k in candidates if k in self.teams}
        if not known:
            return None
        total = sum(self.teams[k].appearances for k in known)
        if not total:
            return None
        best = max(known, key=lambda k: self.teams[k].appearances)
        if self.teams[best].appearances / total >= self.DOMINANCE:
            return best
        return None

    def finalize_displays(self) -> None:
        """Shorten displays for unambiguous/dominant clubs.

        "Flamengo-RJ" becomes "Flamengo" when it owns >= DOMINANCE of its
        base's appearances (the tiny Flamengo-PI keeps its suffix), while
        genuinely shared bases like "Atlético-MG"/"Atlético-PR" keep the
        state suffix. Foreign clubs keep their country tag.
        """
        for team in self.teams.values():
            if not team.state or team.country:
                continue
            if self.base_share(team.key) < self.DOMINANCE:
                continue
            bare = team._variants and self._bare_variant(team)
            if bare:
                team.display = bare

    def _bare_variant(self, team: Team) -> str | None:
        """Prettiest known spelling of this team without the state suffix."""
        best: tuple[tuple[int, int, int], str] | None = None
        for variant in team._variants:
            parsed = parse_name(variant)
            if parsed.state or parsed.country:
                continue  # variant carries a state/country suffix
            score = (
                1 if has_diacritics(variant) else 0,
                -len(variant),
                -variant.count(" "),
            )
            if best is None or score > best[0]:
                best = (score, variant)
        if best is not None:
            return best[1]
        # every variant carries the suffix: strip it from the prettiest one
        return parse_name(team.display).pretty or team.display

    def base_share(self, key: str) -> float:
        """Share of the base's appearances held by this key (0..1)."""
        team = self.teams.get(key)
        if team is None:
            return 0.0
        total = sum(
            self.teams[k].appearances for k in self._by_base.get(team.base, ())
        )
        return team.appearances / total if total else 0.0

    # -- resolution --------------------------------------------------------

    def resolve(self, query: str) -> TeamResolution:
        """Resolve a user query to one team key (or a disambiguation list)."""
        text = (query or "").strip()
        if not text:
            return TeamResolution(key=None, matched=False)

        key_try = fold(text)
        parsed = parse_name(text)

        # 1. Exact canonical key ("atletico-mg", "flamengo-pi").
        if key_try in self.teams:
            return TeamResolution(key=key_try, matched=True)

        # 2. Curated alias ("Atletico Mineiro" -> atletico-mg).
        alias = ALIASES.get(parsed.base)
        if alias and alias in self.teams:
            return TeamResolution(key=alias, matched=True)

        # 3. Unique base ("palmeiras" -> palmeiras-sp).
        candidates = self.keys_for_base(parsed.base)
        if len(candidates) == 1:
            return TeamResolution(key=candidates[0], matched=True)

        # 4. Dominant base state ("flamengo" -> flamengo-rj, not -pi).
        if len(candidates) > 1:
            best = self._dominant(set(candidates))
            if best is not None:
                return TeamResolution(key=best, matched=True)
            return TeamResolution(
                key=None,
                matched=False,
                ambiguous=[self.teams[k] for k in candidates],
            )

        # 5. Substring match against display/base ("corinthianspaulista").
        lowered = fold(text)
        substring_hits = {
            key
            for key, team in self.teams.items()
            if lowered and (lowered in team.base or team.base in lowered)
            and len(team.base) >= 3
        }
        if len(substring_hits) == 1:
            key = next(iter(substring_hits))
            return TeamResolution(key=key, matched=True)
        if len(substring_hits) > 1:
            best = self._dominant(substring_hits)
            if best is not None:
                return TeamResolution(key=best, matched=True)
            ranked = sorted(
                substring_hits,
                key=lambda k: self.teams[k].appearances,
                reverse=True,
            )
            return TeamResolution(
                key=None,
                matched=False,
                ambiguous=[self.teams[k] for k in ranked[:8]],
            )

        # 6. Fuzzy suggestions.
        import difflib

        close = difflib.get_close_matches(
            lowered, list(self.teams.keys()), n=3, cutoff=0.6
        )
        return TeamResolution(
            key=None,
            matched=False,
            suggestions=[self.teams[k].display for k in close],
        )

    def display(self, key: str) -> str:
        team = self.teams.get(key)
        return team.display if team else key
