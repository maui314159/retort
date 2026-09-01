"""Brazilian Soccer MCP Server - data loader.

Context block
-------------
Purpose: Load, parse, and unify the six Kaggle CSV datasets described in
TASK.md into a single in-memory `SoccerData` object that the MCP tools
query against.

Datasets (all in data/kaggle/):
  1. Brasileirao_Matches.csv        - Brasileirão Serie A (2012-2022)
  2. Brazilian_Cup_Matches.csv      - Copa do Brasil (2012-2021)
  3. Libertadores_Matches.csv       - Copa Libertadores (2013-2023)
  4. BR-Football-Dataset.csv        - extended stats, Serie A/B/C + Cup
  5. novo_campeonato_brasileiro.csv - historical Brasileirão (2003-2019)
  6. fifa_data.csv                  - FIFA player database (18k players)

Why stdlib only: avoids a pandas dependency, keeping the server cheap to
run and easy to test. CSVs are small enough (largest ~9MB) that loading
into lists of dicts is sub-second.

What:
  - `Match` dataclass: unified record across the five match files.
  - `load_all(data_dir)` -> `SoccerData` with `.matches`, `.players`,
    and precomputed indexes by team key and season.
  - Robust date parsing for ISO ("2023-09-24"), ISO+time
    ("2012-05-19 18:30:00"), and Brazilian ("29/03/2003") formats.
  - Goal coercion tolerates the string-typed goals in Libertadores
    ("2") and the float-typed goals in BR-Football ("1.0").
  - UTF-8 handling for accented Portuguese names (Grêmio, Avaí).

Test: tests/test_data_loader.py exercises loading + date parsing +
team-name normalization across files.
"""
from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from normalizer import canonical_name, name_key

# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_ISO_FULL = "%Y-%m-%d %H:%M:%S"
_ISO_DATE = "%Y-%m-%d"
_BR_DATE = "%d/%m/%Y"


def parse_date(raw: str) -> str | None:
    """Return an ISO 'YYYY-MM-DD' string, or None if unparseable.

    Handles: '2023-09-24', '2012-05-19 18:30:00', '29/03/2003', and the
    sentinel 'NA' used in the Libertadores file for unknown seasons.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if not s or s.upper() == "NA":
        return None
    for fmt in (_ISO_FULL, _ISO_DATE, _BR_DATE):
        try:
            return datetime.strptime(s, fmt).strftime(_ISO_DATE)
        except ValueError:
            continue
    # Fallback: best-effort ISO prefix
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else None


def parse_season(raw) -> int | None:
    if raw is None or str(raw).strip().upper() == "NA":
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


def parse_goals(raw) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Unified data model
# ---------------------------------------------------------------------------

@dataclass
class Match:
    competition: str            # 'Brasileirão' | 'Copa do Brasil' | 'Libertadores' | 'Serie A' | ...
    date: str | None            # ISO 'YYYY-MM-DD'
    season: int | None
    round_label: str            # original round/stage string
    home_raw: str
    away_raw: str
    home_canonical: str
    away_canonical: str
    home_key: str
    away_key: str
    home_goals: int | None
    away_goals: int | None
    stadium: str = ""           # only populated from historical file
    source_file: str = ""

    @property
    def score_str(self) -> str:
        hg = "?" if self.home_goals is None else self.home_goals
        ag = "?" if self.away_goals is None else self.away_goals
        return f"{hg}-{ag}"

    def result(self) -> str:
        """'home' | 'away' | 'draw' | None (if goals missing)."""
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return "home"
        if self.away_goals > self.home_goals:
            return "away"
        return "draw"


@dataclass
class Player:
    id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: str
    height: str
    weight: str


@dataclass
class SoccerData:
    matches: list[Match] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    # Index: team_key -> list[Match]
    by_team: dict[str, list[Match]] = field(default_factory=lambda: defaultdict(list))
    # Index: (team_key, season) -> list[Match]
    by_team_season: dict[tuple, list[Match]] = field(default_factory=lambda: defaultdict(list))
    # Set of all team canonical names (display order preserved)
    team_names: list[str] = field(default_factory=list)
    _team_seen: set = field(default_factory=set)

    def index_match(self, m: Match) -> None:
        self.matches.append(m)
        for key, canon in ((m.home_key, m.home_canonical), (m.away_key, m.away_canonical)):
            if key and key not in self._team_seen:
                self._team_seen.add(key)
                self.team_names.append(canon)
            if key:
                self.by_team[key].append(m)
        if m.season is not None:
            self.by_team_season[(m.home_key, m.season)].append(m)
            self.by_team_season[(m.away_key, m.season)].append(m)

    def matches_for_team(self, team: str) -> list[Match]:
        key = name_key(team)
        return self.by_team.get(key, [])

    def matches_for_team_season(self, team: str, season: int) -> list[Match]:
        key = name_key(team)
        return self.by_team_season.get((key, season), [])


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def _iter_csv(path: str) -> Iterable[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def _load_brasileirao(path: str) -> list[Match]:
    out: list[Match] = []
    for row in _iter_csv(path):
        out.append(Match(
            competition="Brasileirão",
            date=parse_date(row.get("datetime", "")),
            season=parse_season(row.get("season")),
            round_label=str(row.get("round", "")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_canonical=canonical_name(row.get("home_team", "")),
            away_canonical=canonical_name(row.get("away_team", "")),
            home_key=name_key(row.get("home_team", "")),
            away_key=name_key(row.get("away_team", "")),
            home_goals=parse_goals(row.get("home_goal")),
            away_goals=parse_goals(row.get("away_goal")),
            source_file=os.path.basename(path),
        ))
    return out


def _load_cup(path: str) -> list[Match]:
    out: list[Match] = []
    for row in _iter_csv(path):
        out.append(Match(
            competition="Copa do Brasil",
            date=parse_date(row.get("datetime", "")),
            season=parse_season(row.get("season")),
            round_label=str(row.get("round", "")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_canonical=canonical_name(row.get("home_team", "")),
            away_canonical=canonical_name(row.get("away_team", "")),
            home_key=name_key(row.get("home_team", "")),
            away_key=name_key(row.get("away_team", "")),
            home_goals=parse_goals(row.get("home_goal")),
            away_goals=parse_goals(row.get("away_goal")),
            source_file=os.path.basename(path),
        ))
    return out


def _load_libertadores(path: str) -> list[Match]:
    out: list[Match] = []
    for row in _iter_csv(path):
        out.append(Match(
            competition="Libertadores",
            date=parse_date(row.get("datetime", "")),
            season=parse_season(row.get("season")),
            round_label=str(row.get("stage", "")),
            home_raw=row.get("home_team", ""),
            away_raw=row.get("away_team", ""),
            home_canonical=canonical_name(row.get("home_team", "")),
            away_canonical=canonical_name(row.get("away_team", "")),
            home_key=name_key(row.get("home_team", "")),
            away_key=name_key(row.get("away_team", "")),
            home_goals=parse_goals(row.get("home_goal")),
            away_goals=parse_goals(row.get("away_goal")),
            source_file=os.path.basename(path),
        ))
    return out


def _load_br_football(path: str) -> list[Match]:
    # Extended stats file. We map tournament names to friendly competition
    # labels but keep the original in round_label-free form (we use the
    # 'time' field only if needed).
    out: list[Match] = []
    for row in _iter_csv(path):
        comp = row.get("tournament", "").strip()
        out.append(Match(
            competition=comp,
            date=parse_date(row.get("date", "")),
            season=parse_season(_season_from_date(row.get("date", ""))),
            round_label="",
            home_raw=row.get("home", ""),
            away_raw=row.get("away", ""),
            home_canonical=canonical_name(row.get("home", "")),
            away_canonical=canonical_name(row.get("away", "")),
            home_key=name_key(row.get("home", "")),
            away_key=name_key(row.get("away", "")),
            home_goals=parse_goals(row.get("home_goal")),
            away_goals=parse_goals(row.get("away_goal")),
            source_file=os.path.basename(path),
        ))
    return out


def _season_from_date(raw: str) -> int | None:
    iso = parse_date(raw)
    if iso:
        try:
            return int(iso[:4])
        except ValueError:
            return None
    return None


def _load_historical(path: str) -> list[Match]:
    out: list[Match] = []
    for row in _iter_csv(path):
        home = row.get("Equipe_mandante", "")
        away = row.get("Equipe_visitante", "")
        out.append(Match(
            competition="Brasileirão (Histórico)",
            date=parse_date(row.get("Data", "")),
            season=parse_season(row.get("Ano")),
            round_label=str(row.get("Rodada", "")),
            home_raw=home,
            away_raw=away,
            home_canonical=canonical_name(home),
            away_canonical=canonical_name(away),
            home_key=name_key(home),
            away_key=name_key(away),
            home_goals=parse_goals(row.get("Gols_mandante")),
            away_goals=parse_goals(row.get("Gols_visitante")),
            stadium=row.get("Arena", "") or "",
            source_file=os.path.basename(path),
        ))
    return out


def _load_fifa(path: str) -> list[Player]:
    players: list[Player] = []
    for row in _iter_csv(path):
        def _int(k):
            v = row.get(k)
            try:
                return int(float(v)) if v not in (None, "") else None
            except (ValueError, TypeError):
                return None
        players.append(Player(
            id=str(row.get("ID", "")).strip(),
            name=row.get("Name", "").strip(),
            age=_int("Age"),
            nationality=row.get("Nationality", "").strip(),
            overall=_int("Overall"),
            potential=_int("Potential"),
            club=row.get("Club", "").strip(),
            position=row.get("Position", "").strip(),
            jersey_number=str(row.get("Jersey Number", "")).strip(),
            height=row.get("Height", "").strip(),
            weight=row.get("Weight", "").strip(),
        ))
    return players


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")


def load_all(data_dir: str = DEFAULT_DATA_DIR) -> SoccerData:
    """Load every dataset and return an indexed SoccerData object."""
    sd = SoccerData()

    loaders = [
        ("Brasileirao_Matches.csv", _load_brasileirao),
        ("Brazilian_Cup_Matches.csv", _load_cup),
        ("Libertadores_Matches.csv", _load_libertadores),
        ("BR-Football-Dataset.csv", _load_br_football),
        ("novo_campeonato_brasileiro.csv", _load_historical),
    ]
    for fname, fn in loaders:
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            continue
        for m in fn(path):
            sd.index_match(m)

    fifa_path = os.path.join(data_dir, "fifa_data.csv")
    if os.path.exists(fifa_path):
        sd.players = _load_fifa(fifa_path)

    return sd


# Module-level cached singleton for the MCP server.
_CACHED: SoccerData | None = None


def get_data() -> SoccerData:
    global _CACHED
    if _CACHED is None:
        _CACHED = load_all()
    return _CACHED
