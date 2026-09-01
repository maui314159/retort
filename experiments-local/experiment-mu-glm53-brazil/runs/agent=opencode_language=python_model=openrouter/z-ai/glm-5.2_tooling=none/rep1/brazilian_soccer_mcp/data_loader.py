"""
Data loading and normalization for the Brazilian Soccer MCP server.

Context block
=============
Purpose: Load every CSV under ``data/kaggle/`` into a uniform in-memory
representation and expose normalization helpers that reconcile the many
team-name and date variations present across the datasets.

Datasets handled
----------------
1. ``Brasileirao_Matches.csv``        - Brasileirao Serie A (2012-2022)
2. ``Brazilian_Cup_Matches.csv``      - Copa do Brasil (2012-2021)
3. ``Libertadores_Matches.csv``       - Copa Libertadores (2013-2022)
4. ``BR-Football-Dataset.csv``        - extended match statistics
5. ``novo_campeonato_brasileiro.csv`` - historical Brasileirao (2003-2019)
6. ``fifa_data.csv``                  - FIFA player database

Normalization strategy
----------------------
Team names: a canonical key is produced by lower-casing, stripping accents,
removing a trailing two-letter state suffix (``-SP``, ``-RJ``, `` - MG`` …)
and collapsing non-alphanumeric characters. This lets ``Palmeiras-SP``,
``Palmeiras`` and ``PALMEIRAS`` match the same team.

Dates: the loader accepts ISO (``2023-09-24``), ISO with time
(``2012-05-19 18:30:00``) and Brazilian format (``29/03/2003``) and emits a
``datetime.date`` object plus an ISO string for downstream comparison.
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


# ---------------------------------------------------------------------------
# Canonical team-name normalization
# ---------------------------------------------------------------------------

# Matches a trailing two-letter Brazilian state suffix, e.g. "-SP", " - MG".
_STATE_SUFFIX_RE = re.compile(r"\s*[-\u2013]\s*([A-Z]{2})\s*$")


def _strip_accents(text: str) -> str:
    """Return *text* with combining accents removed (NFKD decomposition)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _bare_key(name: str) -> str:
    """Lowercase alphanumeric key with the state suffix removed."""
    if name is None:
        return ""
    s = str(name).strip()
    s = _STATE_SUFFIX_RE.sub("", s)
    s = _strip_accents(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def extract_state(name: str, fallback_state: str = "") -> str:
    """Extract a two-letter state suffix from a team name, else return fallback."""
    if name:
        m = _STATE_SUFFIX_RE.search(str(name).strip())
        if m:
            return m.group(1)
    return (fallback_state or "").strip().upper()


def normalize_team_name(name: str, state: str = "") -> str:
    """Return a canonical lowercase key for a team name.

    When *state* is provided (or embedded in *name* as a ``-XX`` suffix) it is
    appended to the key so that distinct same-name clubs from different states
    (e.g. Atlético-MG vs Atletico-PR) are not merged. When the bare name is
    globally unique the state is redundant and the bare key alone is returned
    by the :class:`TeamResolver`; this function is the low-level primitive.

    Examples
    --------
    >>> normalize_team_name("Palmeiras-SP")
    'palmeiras|SP'
    >>> normalize_team_name("Palmeiras")
    'palmeiras'
    >>> normalize_team_name("Atlético-MG")
    'atletico|MG'
    """
    if name is None:
        return ""
    bare = _bare_key(name)
    st = extract_state(name, state)
    if st:
        return f"{bare}|{st}"
    return bare


def display_team_name(name: str) -> str:
    """Return a human-friendly team name with the state suffix removed."""
    if name is None:
        return ""
    s = str(name).strip()
    s = _STATE_SUFFIX_RE.sub("", s)
    return s.strip()


class TeamResolver:
    """Resolve raw team names to canonical keys.

    Two-phase strategy:
    1. Observe every (bare_key, state) pair seen across the datasets.
    2. A bare_key that maps to more than one state is *ambiguous* and the
       state becomes part of the canonical key (``bare|SP``). A bare_key seen
       with at most one state resolves to the bare_key alone, so
       ``Palmeiras-SP`` and ``Palmeiras`` collapse to ``palmeiras``.
    """

    def __init__(self) -> None:
        self._bare_states: dict[str, set[str]] = {}
        self._locked = False

    def observe(self, bare_key: str, state: str) -> None:
        if self._locked:
            return
        st = (state or "").strip().upper()
        if not bare_key:
            return
        self._bare_states.setdefault(bare_key, set())
        if st:
            self._bare_states[bare_key].add(st)

    def lock(self) -> None:
        self._locked = True

    def resolve(self, bare_key: str, state: str = "") -> str:
        """Return the canonical key for an observed (bare, state) pair."""
        if not bare_key:
            return ""
        st = (state or "").strip().upper()
        states = self._bare_states.get(bare_key, set())
        # Ambiguous bare name: state is required to disambiguate.
        if len(states) > 1:
            return f"{bare_key}|{st}" if st else bare_key
        # Unambiguous: collapse to bare key (state is redundant).
        return bare_key

    def resolve_query_keys(self, name: str) -> list[str]:
        """Return all canonical keys matching a user-supplied team name.

        A bare name with no state that is ambiguous (e.g. "Atletico") expands
        to every state variant so the query surfaces all matching teams.
        """
        if not name:
            return []
        bare = _bare_key(name)
        st = extract_state(name)
        states = self._bare_states.get(bare, set())
        if st:
            return [self.resolve(bare, st)]
        if len(states) > 1:
            return [f"{bare}|{s}" for s in sorted(states)]
        return [bare]


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M")


def parse_date(value: str):
    """Parse a date/datetime string from any of the supported formats.

    Returns a ``datetime`` (with time when present) or ``None`` when the value
    is empty / unparseable. The special sentinel ``"NA"`` (used by the
    Libertadores dataset for unknown seasons) yields ``None``.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() == "NA":
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # Last resort: try fromisoformat (handles "2012-05-19 18:30:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _to_int(value, default=None):
    if value is None:
        return default
    s = str(value).strip()
    if not s or s.upper() == "NA":
        return default
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default


def _to_float(value, default=None):
    if value is None:
        return default
    s = str(value).strip()
    if not s or s.upper() == "NA":
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Match record
# ---------------------------------------------------------------------------

@dataclass
class Match:
    """A single match record, normalized across all source files."""

    competition: str
    season: str            # ISO date string (YYYY-MM-DD) or ""
    date: str              # ISO date string (YYYY-MM-DD) or ""
    datetime: object       # datetime or None
    home_team: str         # display name (state suffix stripped)
    away_team: str
    home_team_raw: str
    away_team_raw: str
    home_team_key: str     # canonical key (resolver-applied)
    away_team_key: str
    home_state: str
    away_state: str
    home_goal: int
    away_goal: int
    round: str
    stage: str
    stadium: str
    extra: dict = field(default_factory=dict)  # extended stats (corners, shots ...)

    @property
    def winner_key(self) -> str | None:
        if self.home_goal > self.away_goal:
            return self.home_team_key
        if self.away_goal > self.home_goal:
            return self.away_team_key
        return None

    @property
    def is_draw(self) -> bool:
        return self.home_goal == self.away_goal

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
        }


# ---------------------------------------------------------------------------
# Player record
# ---------------------------------------------------------------------------

@dataclass
class Player:
    id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    club_key: str
    position: str
    jersey_number: str
    height: str
    weight: str
    preferred_foot: str
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
        }


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class DataLoader:
    """Load and index all Brazilian soccer datasets from a data directory."""

    DEFAULT_DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"
    )

    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or self.DEFAULT_DATA_DIR
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.resolver = TeamResolver()
        # Indexes
        self._team_index: dict[str, list[Match]] = {}
        self._club_index: dict[str, list[Player]] = {}
        self._nationality_index: dict[str, list[Player]] = {}
        self._competition_seasons: dict[str, set[str]] = {}
        self._loaded = False

    # -- public API --------------------------------------------------------

    def load(self) -> "DataLoader":
        """Load every dataset. Idempotent."""
        if self._loaded:
            return self
        self._load_brasileirao()
        self._load_copa_brasil()
        self._load_libertadores()
        self._load_extended_stats()
        self._load_historical()
        # First pass: observe all (bare, state) pairs to detect ambiguity.
        for m in self.matches:
            self.resolver.observe(_bare_key(m.home_team_raw), m.home_state)
            self.resolver.observe(_bare_key(m.away_team_raw), m.away_state)
        self.resolver.lock()
        # Second pass: assign canonical keys now that ambiguity is known.
        for m in self.matches:
            m.home_team_key = self.resolver.resolve(_bare_key(m.home_team_raw), m.home_state)
            m.away_team_key = self.resolver.resolve(_bare_key(m.away_team_raw), m.away_state)
        self._load_fifa()
        self._build_indexes()
        self._loaded = True
        return self

    def matches_for_team(self, team_key: str) -> list[Match]:
        return self._team_index.get(team_key, [])

    def players_for_club(self, club_key: str) -> list[Player]:
        return self._club_index.get(club_key, [])

    def players_for_nationality(self, nationality: str) -> list[Player]:
        key = _strip_accents(nationality).lower().strip()
        return self._nationality_index.get(key, [])

    def all_team_keys(self) -> list[str]:
        return sorted(self._team_index.keys())

    # -- loaders -----------------------------------------------------------

    def _load_brasileirao(self) -> None:
        path = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        for row in self._read_csv(path):
            self.matches.append(self._make_match(
                competition="Brasileirao",
                season=str(row.get("season", "")),
                datetime_raw=row.get("datetime", ""),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_state=row.get("home_team_state", ""),
                away_state=row.get("away_team_state", ""),
                home_goal=row.get("home_goal"),
                away_goal=row.get("away_goal"),
                round_no=row.get("round", ""),
                stage="",
                stadium="",
            ))

    def _load_copa_brasil(self) -> None:
        path = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        for row in self._read_csv(path):
            self.matches.append(self._make_match(
                competition="Copa do Brasil",
                season=str(row.get("season", "")),
                datetime_raw=row.get("datetime", ""),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_state="",
                away_state="",
                home_goal=row.get("home_goal"),
                away_goal=row.get("away_goal"),
                round_no=row.get("round", ""),
                stage="",
                stadium="",
            ))

    def _load_libertadores(self) -> None:
        path = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        for row in self._read_csv(path):
            self.matches.append(self._make_match(
                competition="Copa Libertadores",
                season=str(row.get("season", "")),
                datetime_raw=row.get("datetime", ""),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_state="",
                away_state="",
                home_goal=row.get("home_goal"),
                away_goal=row.get("away_goal"),
                round_no="",
                stage=row.get("stage", ""),
                stadium="",
            ))

    def _load_extended_stats(self) -> None:
        path = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        stat_fields = (
            "home_corner", "away_corner", "home_attack", "away_attack",
            "home_shots", "away_shots", "ht_result", "at_result",
            "total_corners",
        )
        for row in self._read_csv(path):
            tournament = row.get("tournament", "").strip()
            comp = {
                "Serie A": "Brasileirao Serie A",
                "Serie B": "Brasileirao Serie B",
                "Serie C": "Brasileirao Serie C",
                "Copa do Brasil": "Copa do Brasil",
            }.get(tournament, tournament or "Unknown")
            extra = {k: row.get(k, "") for k in stat_fields if row.get(k) not in (None, "")}
            self.matches.append(self._make_match(
                competition=comp,
                season=self._season_from_date(row.get("date", "")),
                datetime_raw=row.get("date", ""),
                home_raw=row.get("home", ""),
                away_raw=row.get("away", ""),
                home_state="",
                away_state="",
                home_goal=row.get("home_goal"),
                away_goal=row.get("away_goal"),
                round_no="",
                stage="",
                stadium="",
                extra=extra,
            ))

    def _load_historical(self) -> None:
        path = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        for row in self._read_csv(path):
            self.matches.append(self._make_match(
                competition="Brasileirao (Historical)",
                season=str(row.get("Ano", "")),
                datetime_raw=row.get("Data", ""),
                home_raw=row.get("Equipe_mandante", ""),
                away_raw=row.get("Equipe_visitante", ""),
                home_state=row.get("Mandante_UF", ""),
                away_state=row.get("Visitante_UF", ""),
                home_goal=row.get("Gols_mandante"),
                away_goal=row.get("Gols_visitante"),
                round_no=row.get("Rodada", ""),
                stage="",
                stadium=row.get("Arena", ""),
            ))

    def _load_fifa(self) -> None:
        path = os.path.join(self.data_dir, "fifa_data.csv")
        # A curated set of attribute columns we surface.
        attr_cols = (
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
            "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
            "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
            "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
            "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
            "Composure", "Marking", "StandingTackle", "SlidingTackle",
            "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
        )
        for row in self._read_csv(path):
            club = (row.get("Club") or "").strip()
            attrs = {c: _to_int(row.get(c)) for c in attr_cols if row.get(c) not in (None, "")}
            self.players.append(Player(
                id=str(row.get("ID", "")),
                name=(row.get("Name") or "").strip(),
                age=_to_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=club,
                club_key=_bare_key(club),
                position=(row.get("Position") or "").strip(),
                jersey_number=str(row.get("Jersey Number") or "").strip(),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                preferred_foot=(row.get("Preferred Foot") or "").strip(),
                attributes=attrs,
            ))

    # -- helpers -----------------------------------------------------------

    def _make_match(
        self, *, competition, season, datetime_raw, home_raw, away_raw,
        home_state, away_state, home_goal, away_goal, round_no, stage,
        stadium, extra=None,
    ) -> Match:
        dt = parse_date(datetime_raw)
        home_disp = display_team_name(home_raw)
        away_disp = display_team_name(away_raw)
        # State: prefer an explicit state column, else extract from the raw name.
        h_state = extract_state(home_raw, home_state)
        a_state = extract_state(away_raw, away_state)
        return Match(
            competition=competition,
            season=str(season) if season is not None else "",
            date=dt.date().isoformat() if dt else "",
            datetime=dt,
            home_team=home_disp,
            away_team=away_disp,
            home_team_raw=home_raw,
            away_team_raw=away_raw,
            # Canonical keys are assigned in the second pass by the resolver.
            home_team_key="",
            away_team_key="",
            home_state=h_state,
            away_state=a_state,
            home_goal=_to_int(home_goal, 0) or 0,
            away_goal=_to_int(away_goal, 0) or 0,
            round=str(round_no) if round_no is not None else "",
            stage=stage or "",
            stadium=stadium or "",
            extra=extra or {},
        )

    def _season_from_date(self, date_raw: str) -> str:
        dt = parse_date(date_raw)
        return str(dt.year) if dt else ""

    @staticmethod
    def _read_csv(path: str) -> Iterable[dict]:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            yield from csv.DictReader(fh)

    def _build_indexes(self) -> None:
        self._team_index.clear()
        for m in self.matches:
            self._team_index.setdefault(m.home_team_key, []).append(m)
            if m.away_team_key and m.away_team_key != m.home_team_key:
                self._team_index.setdefault(m.away_team_key, []).append(m)
        for m in self.matches:
            self._competition_seasons.setdefault(m.competition, set()).add(m.season)

        self._club_index.clear()
        self._nationality_index.clear()
        for p in self.players:
            if p.club_key:
                self._club_index.setdefault(p.club_key, []).append(p)
            nkey = _strip_accents(p.nationality).lower().strip()
            if nkey:
                self._nationality_index.setdefault(nkey, []).append(p)
