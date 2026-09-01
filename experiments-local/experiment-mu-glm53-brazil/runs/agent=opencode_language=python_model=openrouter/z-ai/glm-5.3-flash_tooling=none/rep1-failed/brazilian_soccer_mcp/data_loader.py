"""Load and unify the six Brazilian soccer CSV datasets."""

from __future__ import annotations

import csv
import os
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .normalize import (
    identity_key,
    parse_date,
    parse_int,
    parse_money,
    parse_season,
    normalize_team,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Canonical competition labels and which raw tournament labels map onto them.
COMPETITION_ALIASES = {
    "brasileirao": "Brasileirão",
    "brasileirao serie a": "Brasileirão",
    "serie a": "Brasileirão",
    "serie b": "Serie B",
    "serie c": "Serie C",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Libertadores",
    "copa libertadores": "Libertadores",
}

# Raw label -> canonical, applied to CSV tournament/competition columns.
_TOURNAMENT_MAP = {
    "serie a": "Brasileirão",
    "serie b": "Serie B",
    "serie c": "Serie C",
    "copa do brasil": "Copa do Brasil",
}


@dataclass
class Match:
    date: str | None
    season: int | None
    competition: str
    round: str | None
    stage: str | None
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    home_state: str | None = None
    away_state: str | None = None
    arena: str | None = None
    source: str = ""

    @property
    def home_goals_int(self) -> int:
        return self.home_goals or 0

    @property
    def away_goals_int(self) -> int:
        return self.away_goals or 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Player:
    id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str
    position: str
    jersey_number: int | None
    preferred_foot: str | None
    height: str | None
    weight: str | None
    value: str | None
    value_eur: float | None
    wage: str | None
    wage_eur: float | None
    skills: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def resolve_data_dir(data_dir: str | Path | None = None) -> Path:
    """Find the data directory (env var > argument > repo default)."""
    candidate = Path(
        data_dir or os.environ.get("BRAZILIAN_SOCCER_DATA_DIR", DEFAULT_DATA_DIR)
    )
    if not candidate.is_dir():
        raise FileNotFoundError(
            f"Data directory not found: {candidate}. Set BRAZILIAN_SOCCER_DATA_DIR."
        )
    return candidate


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Dataset:
    """In-memory, normalized view of all six source files."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = resolve_data_dir(data_dir)
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._team_index: dict[str, list[int]] = {}
        self._team_index: dict[str, list[int]] = {}
        self._identity_to_display: dict[str, str] = {}
        self._load_matches()
        self._load_players()
        self._canonicalize_teams()
        self._deduplicate()
        self._build_indexes()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_matches(self) -> None:
        for source in self._SOURCES:
            {
                "novo_campeonato_brasileiro.csv": self._load_historical,
                "Brasileirao_Matches.csv": self._load_brasileirao,
                "Brazilian_Cup_Matches.csv": self._load_cup,
                "Libertadores_Matches.csv": self._load_libertadores,
                "BR-Football-Dataset.csv": self._load_br_football,
            }[source]()
        self.matches.sort(
            key=lambda m: (m.date or "9999", m.competition, m.round or "")
        )

    def _load_brasileirao(self) -> None:
        path = self.data_dir / "Brasileirao_Matches.csv"
        for row in _read_csv(path):
            self.matches.append(
                Match(
                    date=str(parse_date(row["datetime"]) or "") or None,
                    season=parse_season(row["season"]),
                    competition="Brasileirão",
                    round=row.get("round") or None,
                    stage=None,
                    home_team=normalize_team(row["home_team"]),
                    away_team=normalize_team(row["away_team"]),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    home_state=row.get("home_team_state") or None,
                    away_state=row.get("away_team_state") or None,
                    source=path.name,
                )
            )

    def _load_historical(self) -> None:
        path = self.data_dir / "novo_campeonato_brasileiro.csv"
        for row in _read_csv(path):
            self.matches.append(
                Match(
                    date=str(parse_date(row["Data"]) or "") or None,
                    season=parse_season(row["Ano"]),
                    competition="Brasileirão",
                    round=row.get("Rodada") or None,
                    stage=None,
                    home_team=normalize_team(row["Equipe_mandante"]),
                    away_team=normalize_team(row["Equipe_visitante"]),
                    home_goals=parse_int(row["Gols_mandante"]),
                    away_goals=parse_int(row["Gols_visitante"]),
                    home_state=row.get("Mandante_UF") or None,
                    away_state=row.get("Visitante_UF") or None,
                    arena=row.get("Arena") or None,
                    source=path.name,
                )
            )

    def _load_cup(self) -> None:
        path = self.data_dir / "Brazilian_Cup_Matches.csv"
        for row in _read_csv(path):
            self.matches.append(
                Match(
                    date=str(parse_date(row["datetime"]) or "") or None,
                    season=parse_season(row["season"]),
                    competition="Copa do Brasil",
                    round=row.get("round") or None,
                    stage=None,
                    home_team=normalize_team(row["home_team"]),
                    away_team=normalize_team(row["away_team"]),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    source=path.name,
                )
            )

    def _load_libertadores(self) -> None:
        path = self.data_dir / "Libertadores_Matches.csv"
        for row in _read_csv(path):
            self.matches.append(
                Match(
                    date=str(parse_date(row["datetime"]) or "") or None,
                    season=parse_season(row["season"]),
                    competition="Libertadores",
                    round=None,
                    stage=row.get("stage") or None,
                    home_team=normalize_team(row["home_team"]),
                    away_team=normalize_team(row["away_team"]),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    source=path.name,
                )
            )

    def _load_br_football(self) -> None:
        path = self.data_dir / "BR-Football-Dataset.csv"
        for row in _read_csv(path):
            competition = _TOURNAMENT_MAP.get(
                row["tournament"].strip().lower(), row["tournament"].strip()
            )
            self.matches.append(
                Match(
                    date=str(parse_date(row["date"]) or "") or None,
                    season=parse_season((row.get("date") or "")[:4]),
                    competition=competition,
                    round=None,
                    stage=None,
                    home_team=normalize_team(row["home"]),
                    away_team=normalize_team(row["away"]),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    source=path.name,
                )
            )

    def _canonicalize_teams(self) -> None:
        """Pick one display name per team identity and rewrite all matches.

        Raw spellings like "Fortaleza", "Fortaleza EC", and "Fortaleza FC"
        share an identity; the most frequent display form wins.
        """
        display_counts: Counter = Counter()
        for match in self.matches:
            display_counts[match.home_team] += 1
            display_counts[match.away_team] += 1
        identity_counts: dict[str, dict[str, int]] = {}
        for display, count in display_counts.items():
            identity = identity_key(display)
            per_identity = identity_counts.setdefault(identity, Counter())
            per_identity[display] += count
        self._identity_to_display = {
            identity: max(forms, key=lambda d: (forms[d], -len(d)))
            for identity, forms in identity_counts.items()
        }
        for match in self.matches:
            match.home_team = self._display_for(match.home_team)
            match.away_team = self._display_for(match.away_team)

    def _display_for(self, name: str) -> str:
        return self._identity_to_display.get(identity_key(name), name)

    def _deduplicate(self) -> None:
        """Drop matches repeated across sources (same comp/season/date/pair)."""
        seen: set[tuple] = set()
        kept: list[Match] = []
        for match in self.matches:
            if match.date:
                key = (
                    match.competition,
                    match.season,
                    match.date,
                    identity_key(match.home_team),
                    identity_key(match.away_team),
                )
                if key in seen:
                    continue
                seen.add(key)
            kept.append(match)
        self.matches = kept

    def _load_players(self) -> None:
        path = self.data_dir / "fifa_data.csv"
        skill_columns = (
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing",
            "Dribbling", "BallControl", "Acceleration", "SprintSpeed",
            "ShotPower", "LongShots", "Stamina", "Strength", "Vision",
            "Penalties", "Marking", "StandingTackle", "SlidingTackle",
            "GKDiving", "GKHandling", "GKKicking", "GKPositioning",
            "GKReflexes",
        )
        for row in _read_csv(path):
            skills = {}
            for col in skill_columns:
                value = parse_int(row.get(col))
                if value is not None:
                    skills[col] = value
            self.players.append(
                Player(
                    id=parse_int(row.get("ID")) or 0,
                    name=row.get("Name", "").strip(),
                    age=parse_int(row.get("Age")),
                    nationality=row.get("Nationality", "").strip(),
                    overall=parse_int(row.get("Overall")) or 0,
                    potential=parse_int(row.get("Potential")) or 0,
                    club=row.get("Club", "").strip(),
                    position=row.get("Position", "").strip(),
                    jersey_number=parse_int(row.get("Jersey Number")),
                    preferred_foot=row.get("Preferred Foot") or None,
                    height=row.get("Height") or None,
                    weight=row.get("Weight") or None,
                    value=row.get("Value") or None,
                    value_eur=parse_money(row.get("Value")),
                    wage=row.get("Wage") or None,
                    wage_eur=parse_money(row.get("Wage")),
                    skills=skills,
                )
            )

    def _build_indexes(self) -> None:
        self._team_index = {}
        for idx, match in enumerate(self.matches):
            for team in (match.home_team, match.away_team):
                self._team_index.setdefault(team, []).append(idx)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def resolve_team(self, name: str) -> str:
        """Canonical display name for a (possibly fuzzy) team name.

        Handles aliases, state suffixes, accents, and generic club-type
        suffixes ("Fortaleza FC" -> "Fortaleza").
        """
        display = self._display_for(normalize_team(name))
        return display or normalize_team(name)

    def matches_for_team(self, team: str) -> list[Match]:
        canonical = self.resolve_team(team)
        indices = self._team_index.get(canonical, [])
        return [self.matches[i] for i in indices]

    def competitions(self) -> dict[str, dict]:
        """Competition label -> match count and season range."""
        stats: dict[str, dict] = {}
        for match in self.matches:
            entry = stats.setdefault(
                match.competition,
                {"matches": 0, "seasons": set()},
            )
            entry["matches"] += 1
            if match.season:
                entry["seasons"].add(match.season)
        for entry in stats.values():
            entry["seasons"] = sorted(entry["seasons"])
        return stats

    def teams(self) -> dict[str, int]:
        """Canonical team name -> match count."""
        return {
            team: len(indices)
            for team, indices in sorted(
                self._team_index.items(), key=lambda kv: -len(kv[1])
            )
        }
