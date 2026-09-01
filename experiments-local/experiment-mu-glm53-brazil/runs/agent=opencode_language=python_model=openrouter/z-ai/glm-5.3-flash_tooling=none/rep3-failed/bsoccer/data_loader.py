"""Load the six Kaggle CSV datasets into a unified in-memory model.

All match rows are converted to a common :class:`Match` record with
canonicalized team names and parsed dates, so the query layer never has to
deal with raw file quirks.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime

from .normalization import parse_date, parse_int, resolve_team

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

COMPETITION_BRASILEIRAO = "Brasileirão Série A"
COMPETITION_COPA_DO_BRASIL = "Copa do Brasil"
COMPETITION_LIBERTADORES = "Copa Libertadores"


@dataclass
class Match:
    competition: str          # canonical competition label (per source dataset)
    source_file: str          # which CSV the row came from
    date: date | None = None
    datetime: datetime | None = None
    season: int | None = None
    round: str | None = None
    stage: str | None = None
    home: str = ""            # canonical home team name
    away: str = ""            # canonical away team name
    home_raw: str = ""        # original spelling, for display fidelity
    away_raw: str = ""
    home_goal: int | None = None
    away_goal: int | None = None
    home_state: str | None = None
    away_state: str | None = None
    arena: str | None = None
    stats: dict = field(default_factory=dict)  # corners/shots/attacks (BR-Football)

    @property
    def total_goals(self) -> int | None:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal

    @property
    def margin(self) -> int | None:
        if self.home_goal is None or self.away_goal is None:
            return None
        return abs(self.home_goal - self.away_goal)

    def date_key(self) -> str:
        return self.date.isoformat() if self.date else ""

    def to_dict(self) -> dict:
        return {
            "date": self.date_key(),
            "time": self.datetime.strftime("%H:%M") if self.datetime else None,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home,
            "away_team": self.away,
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "venue": self.arena,
            "source": self.source_file,
        }


@dataclass
class Player:
    id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str                  # raw club name from FIFA dataset
    club_key: str              # canonical club key (same resolver as teams)
    position: str
    jersey_number: int | None
    preferred_foot: str
    work_rate: str
    value: str
    wage: str
    height: str
    weight: str
    contract_valid_until: str
    skills: dict = field(default_factory=dict)

    def to_dict(self, include_skills: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
        }
        if include_skills:
            data["skills"] = self.skills
        return data


# ---------------------------------------------------------------------------
# Row parsers
# ---------------------------------------------------------------------------

def _parse_season(value: str | None) -> int | None:
    season = parse_int(value)
    if season is None or season < 1900 or season > 2100:
        return None
    return season


def _load_brasileirao(path: str) -> list[Match]:
    with open(path, encoding="utf-8", newline="") as fh:
        matches = []
        for row in csv.DictReader(fh):
            match_date, match_dt = parse_date(row["datetime"])
            matches.append(Match(
                competition=COMPETITION_BRASILEIRAO,
                source_file="Brasileirao_Matches.csv",
                date=match_date,
                datetime=match_dt,
                season=_parse_season(row.get("season")),
                round=row.get("round") or None,
                home=resolve_team(row["home_team"]) or row["home_team"],
                away=resolve_team(row["away_team"]) or row["away_team"],
                home_raw=row["home_team"],
                away_raw=row["away_team"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                home_state=row.get("home_team_state") or None,
                away_state=row.get("away_team_state") or None,
            ))
    return matches


def _load_cup(path: str) -> list[Match]:
    with open(path, encoding="utf-8", newline="") as fh:
        matches = []
        for row in csv.DictReader(fh):
            match_date, match_dt = parse_date(row["datetime"])
            matches.append(Match(
                competition=COMPETITION_COPA_DO_BRASIL,
                source_file="Brazilian_Cup_Matches.csv",
                date=match_date,
                datetime=match_dt,
                season=_parse_season(row.get("season")),
                round=row.get("round") or None,
                home=resolve_team(row["home_team"]) or row["home_team"],
                away=resolve_team(row["away_team"]) or row["away_team"],
                home_raw=row["home_team"],
                away_raw=row["away_team"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
            ))
    return matches


def _load_libertadores(path: str) -> list[Match]:
    with open(path, encoding="utf-8", newline="") as fh:
        matches = []
        for row in csv.DictReader(fh):
            match_date, match_dt = parse_date(row["datetime"])
            matches.append(Match(
                competition=COMPETITION_LIBERTADORES,
                source_file="Libertadores_Matches.csv",
                date=match_date,
                datetime=match_dt,
                season=_parse_season(row.get("season")),
                stage=row.get("stage") or None,
                home=resolve_team(row["home_team"]) or row["home_team"],
                away=resolve_team(row["away_team"]) or row["away_team"],
                home_raw=row["home_team"],
                away_raw=row["away_team"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
            ))
    return matches


def _load_br_football(path: str) -> list[Match]:
    label_map = {
        "Serie A": "Série A (BR-Football)",
        "Serie B": "Série B (BR-Football)",
        "Serie C": "Série C (BR-Football)",
        "Copa do Brasil": "Copa do Brasil (BR-Football)",
    }
    with open(path, encoding="utf-8", newline="") as fh:
        matches = []
        for row in csv.DictReader(fh):
            match_date, match_dt = parse_date(row.get("date") or "")
            season = match_date.year if match_date else None
            competition = label_map.get((row.get("tournament") or "").strip(), (row.get("tournament") or "").strip())
            stats = {}
            for key in ("home_corner", "away_corner", "home_attack", "away_attack",
                        "home_shots", "away_shots", "total_corners",
                        "ht_result", "at_result"):
                if row.get(key):
                    stats[key] = row[key]
            matches.append(Match(
                competition=competition,
                source_file="BR-Football-Dataset.csv",
                date=match_date,
                datetime=match_dt,
                season=season,
                home=resolve_team(row["home"]) or row["home"],
                away=resolve_team(row["away"]) or row["away"],
                home_raw=row["home"],
                away_raw=row["away"],
                home_goal=parse_int(row.get("home_goal")),
                away_goal=parse_int(row.get("away_goal")),
                stats=stats,
            ))
    return matches


def _load_novo(path: str) -> list[Match]:
    with open(path, encoding="utf-8", newline="") as fh:
        matches = []
        for row in csv.DictReader(fh):
            match_date, match_dt = parse_date(row.get("Data") or "")
            matches.append(Match(
                competition=COMPETITION_BRASILEIRAO,
                source_file="novo_campeonato_brasileiro.csv",
                date=match_date,
                datetime=match_dt,
                season=_parse_season(row.get("Ano")),
                round=row.get("Rodada") or None,
                home=resolve_team(row["Equipe_mandante"]) or row["Equipe_mandante"],
                away=resolve_team(row["Equipe_visitante"]) or row["Equipe_visitante"],
                home_raw=row["Equipe_mandante"],
                away_raw=row["Equipe_visitante"],
                home_goal=parse_int(row.get("Gols_mandante")),
                away_goal=parse_int(row.get("Gols_visitante")),
                home_state=row.get("Mandante_UF") or None,
                away_state=row.get("Visitante_UF") or None,
                arena=row.get("Arena") or None,
            ))
    return matches


_SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def _load_players(path: str) -> list[Player]:
    with open(path, encoding="utf-8", newline="") as fh:
        players = []
        for row in csv.DictReader(fh):
            club = (row.get("Club") or "").strip()
            players.append(Player(
                id=row.get("ID", ""),
                name=row.get("Name", "").strip(),
                age=parse_int(row.get("Age")),
                nationality=row.get("Nationality", "").strip(),
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=club,
                club_key=resolve_team(club) or club.lower(),
                position=row.get("Position", "").strip(),
                jersey_number=parse_int(row.get("Jersey Number")),
                preferred_foot=row.get("Preferred Foot", "").strip(),
                work_rate=row.get("Work Rate", "").strip(),
                value=row.get("Value", "").strip(),
                wage=row.get("Wage", "").strip(),
                height=row.get("Height", "").strip(),
                weight=row.get("Weight", "").strip(),
                contract_valid_until=row.get("Contract Valid Until", "").strip(),
                skills={col: parse_int(row.get(col)) for col in _SKILL_COLUMNS},
            ))
    return players


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------

def load_all(data_dir: str = DATA_DIR) -> tuple[list[Match], list[Player]]:
    """Load every dataset. Returns ``(matches, players)``."""
    matches: list[Match] = []
    matches.extend(_load_brasileirao(os.path.join(data_dir, "Brasileirao_Matches.csv")))
    matches.extend(_load_cup(os.path.join(data_dir, "Brazilian_Cup_Matches.csv")))
    matches.extend(_load_libertadores(os.path.join(data_dir, "Libertadores_Matches.csv")))
    matches.extend(_load_br_football(os.path.join(data_dir, "BR-Football-Dataset.csv")))
    matches.extend(_load_novo(os.path.join(data_dir, "novo_campeonato_brasileiro.csv")))
    players = _load_players(os.path.join(data_dir, "fifa_data.csv"))
    return matches, players
